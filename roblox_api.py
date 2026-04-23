"""Async Roblox API client.

Handles group lookups, catalog pagination, batched item details, and PNG
template retrieval for classic clothing (shirts, pants, t-shirts).
"""
from __future__ import annotations

import asyncio
import socket
from typing import AsyncIterator, Optional

import aiohttp

from .constants import (
    ASSET_DELIVERY_URL,
    CATALOG_ITEM_DETAILS_URL,
    CATALOG_PAGE_SIZE,
    CATALOG_SEARCH_URL,
    CLOTHING_ASSET_TYPES,
    DEFAULT_HEADERS,
    GROUP_INFO_URL,
    MAX_RETRIES,
    REQUEST_TIMEOUT,
    RETRY_BACKOFF,
)
from .logger import get_logger
from .models import ClothingItem, GroupInfo
from .utils import extract_template_id_from_xml, looks_like_image

log = get_logger()


class RobloxAPIError(Exception):
    """Raised when a Roblox endpoint fails in a way we can't recover from."""


class RobloxAPI:
    """Thin async wrapper around the public Roblox REST endpoints we need."""

    def __init__(self, concurrency: int = 8) -> None:
        # Force IPv4 — many VPS providers have broken or slow IPv6 routing
        # to Roblox, which makes aiohttp hang until the total timeout.
        connector = aiohttp.TCPConnector(
            family=socket.AF_INET,
            limit=concurrency * 2,
        )
        timeout = aiohttp.ClientTimeout(
            total=60,          # whole request budget
            sock_connect=15,   # TCP connect alone
            sock_read=30,      # between chunks of response
        )
        self._session = aiohttp.ClientSession(
            headers=DEFAULT_HEADERS,
            timeout=timeout,
            connector=connector,
        )
        self._sem = asyncio.Semaphore(concurrency)
        self._csrf_token: Optional[str] = None

    async def close(self) -> None:
        await self._session.close()

    async def __aenter__(self) -> "RobloxAPI":
        return self

    async def __aexit__(self, *exc) -> None:
        await self.close()

    # ------------------------------------------------------------------ low level
    async def _request(
        self, method: str, url: str, **kwargs
    ) -> aiohttp.ClientResponse:
        """HTTP request with retry + backoff on transient failures (429, 5xx, network)."""
        last_exc: Optional[Exception] = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                async with self._sem:
                    resp = await self._session.request(method, url, **kwargs)
                if resp.status == 429 or 500 <= resp.status < 600:
                    wait = RETRY_BACKOFF * attempt
                    log.warning(
                        f"[yellow]HTTP {resp.status} from {url}; retry in {wait:.1f}s[/]"
                    )
                    await resp.release()
                    await asyncio.sleep(wait)
                    continue
                return resp
            except aiohttp.ClientError as exc:
                last_exc = exc
                await asyncio.sleep(RETRY_BACKOFF * attempt)
        raise RobloxAPIError(f"Request failed after retries: {url} ({last_exc})")

    async def _post_with_csrf(self, url: str, json: dict) -> aiohttp.ClientResponse:
        """POST that transparently handles Roblox's x-csrf-token challenge."""
        headers = {"x-csrf-token": self._csrf_token} if self._csrf_token else {}
        resp = await self._request("POST", url, json=json, headers=headers)
        if resp.status == 403 and "x-csrf-token" in resp.headers:
            self._csrf_token = resp.headers["x-csrf-token"]
            await resp.release()
            resp = await self._request(
                "POST", url, json=json, headers={"x-csrf-token": self._csrf_token}
            )
        return resp

    # ----------------------------------------------------------------- group info
    async def get_group_info(self, group_id: int) -> GroupInfo:
        url = GROUP_INFO_URL.format(group_id=group_id)
        resp = await self._request("GET", url)
        async with resp:
            if resp.status == 404:
                raise RobloxAPIError(f"Group {group_id} not found")
            if resp.status != 200:
                raise RobloxAPIError(
                    f"Group {group_id} returned HTTP {resp.status}"
                )
            data = await resp.json()
        return GroupInfo(
            id=int(data["id"]),
            name=data.get("name", f"Group {group_id}"),
            member_count=int(data.get("memberCount", 0)),
            description=data.get("description") or "",
        )

    # ---------------------------------------------------------- catalog pagination
    async def iter_group_clothing_ids(self, group_id: int) -> AsyncIterator[int]:
        """Yield every clothing asset ID sold by `group_id`, paginated."""
        cursor = ""
        while True:
            params = {
                "Category": "Clothing",          # covers Shirts / Pants / T-Shirts
                "CreatorType": "Group",
                "CreatorTargetId": group_id,
                "limit": CATALOG_PAGE_SIZE,
                "SortType": 3,                   # RecentlyUpdated
            }
            if cursor:
                params["cursor"] = cursor
            resp = await self._request("GET", CATALOG_SEARCH_URL, params=params)
            async with resp:
                if resp.status != 200:
                    log.error(
                        f"Catalog search failed for group {group_id}: "
                        f"HTTP {resp.status}"
                    )
                    return
                payload = await resp.json()
            for entry in payload.get("data", []):
                if entry.get("itemType") != "Asset":
                    continue
                yield int(entry["id"])
            cursor = payload.get("nextPageCursor") or ""
            if not cursor:
                return

    # ------------------------------------------------------------- item metadata
    async def get_item_details(self, asset_ids: list[int]) -> list[ClothingItem]:
        """Batch-fetch name / assetType / price for up to ~120 IDs per call."""
        if not asset_ids:
            return []
        body = {"items": [{"itemType": "Asset", "id": aid} for aid in asset_ids]}
        resp = await self._post_with_csrf(CATALOG_ITEM_DETAILS_URL, body)
        async with resp:
            if resp.status != 200:
                log.error(f"items/details failed: HTTP {resp.status}")
                return []
            payload = await resp.json()

        items: list[ClothingItem] = []
        for entry in payload.get("data", []):
            asset_type = int(entry.get("assetType") or 0)
            if asset_type not in CLOTHING_ASSET_TYPES:
                continue
            items.append(
                ClothingItem(
                    asset_id=int(entry["id"]),
                    name=entry.get("name") or f"asset_{entry['id']}",
                    asset_type_id=asset_type,
                    price=entry.get("price"),
                )
            )
        return items

    # ------------------------------------------------------------- asset download
    async def fetch_asset_bytes(self, asset_id: int) -> Optional[bytes]:
        """Raw bytes for an asset delivery URL. Returns None on non-200."""
        resp = await self._request(
            "GET", ASSET_DELIVERY_URL, params={"id": asset_id}, allow_redirects=True
        )
        async with resp:
            if resp.status != 200:
                return None
            return await resp.read()

    async def download_template_png(self, item: ClothingItem) -> Optional[bytes]:
        """Return the PNG template bytes for a clothing item.

        T-Shirts store the PNG directly at the asset ID. Shirts and Pants store
        a small Roblox XML file that references the PNG template by a second
        asset ID, which we then fetch.
        """
        raw = await self.fetch_asset_bytes(item.asset_id)
        if raw is None:
            return None
        if looks_like_image(raw):
            return raw
        template_id = extract_template_id_from_xml(raw)
        if template_id is None:
            log.warning(
                f"Could not find template ID inside asset {item.asset_id} "
                f"({item.name!r})"
            )
            return None
        return await self.fetch_asset_bytes(template_id)
