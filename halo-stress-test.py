#!/usr/bin/env python3
"""
Halo.rip Bio Update Stress Test
Concurrent load testing for profile endpoint
"""

import asyncio
import aiohttp
import time
import random
from datetime import datetime
from collections import defaultdict

# Configuration
CONFIG = {
    'endpoint': 'https://www.halo.rip/api/profile',
    'total_requests': 100,
    'concurrent_requests': 10,
    'cookie': '',  # Set this or use command line arg
}

# Stats tracking
stats = {
    'total': 0,
    'success': 0,
    'failed': 0,
    'in_progress': 0,
    'response_times': [],
    'errors': defaultdict(int),
}

def generate_bio(index):
    """Generate random bio text for variation"""
    emojis = ['🚀', '💪', '⚡', '🔥', '✨', '🎯', '💻', '🌟', '🎨', '🎮']
    random_emoji = random.choice(emojis)
    random_num = random.randint(1000, 9999)
    timestamp = int(time.time() * 1000)
    
    variations = [
        f"Stress test #{index} {random_emoji} | {timestamp}",
        f"Load testing halo.rip 🧪 req={index} rand={random_num}",
        f"Bio update {index} at {datetime.now().strftime('%H:%M:%S')} {random_emoji}",
        f"Concurrent request #{index} | hash: {random_num}",
        f"Testing capacity {random_emoji} [{index}/{timestamp % 1000}]",
        f"halo.rip stress test | iteration: {index} | id: {random_num}",
        f"{random_emoji} Load test {index} - {datetime.now().strftime('%H:%M:%S')}",
    ]
    
    chosen = random.choice(variations)
    return f"{chosen} | {random_num}"

async def update_bio(session, index):
    """Make a single API request"""
    start_time = time.time()
    stats['in_progress'] += 1
    
    try:
        payload = {
            'bio': generate_bio(index),
        }
        
        headers = {
            'Content-Type': 'application/json',
            'Cookie': CONFIG['cookie'],
        }
        
        async with session.put(
            CONFIG['endpoint'],
            json=payload,
            headers=headers
        ) as response:
            duration = (time.time() - start_time) * 1000  # Convert to ms
            stats['response_times'].append(duration)
            
            if response.status == 200:
                stats['success'] += 1
                return {'success': True, 'index': index, 'duration': duration, 'status': response.status}
            else:
                stats['failed'] += 1
                error_text = await response.text()
                error_key = f"{response.status}: {error_text[:50]}"
                stats['errors'][error_key] += 1
                return {'success': False, 'index': index, 'duration': duration, 'status': response.status, 'error': error_text}
                
    except Exception as e:
        duration = (time.time() - start_time) * 1000
        stats['failed'] += 1
        error_key = str(e)[:50]
        stats['errors'][error_key] += 1
        return {'success': False, 'index': index, 'duration': duration, 'error': str(e)}
    finally:
        stats['in_progress'] -= 1

def show_progress():
    """Display progress bar"""
    completed = stats['success'] + stats['failed']
    percentage = (completed / CONFIG['total_requests']) * 100 if CONFIG['total_requests'] > 0 else 0
    avg_time = sum(stats['response_times']) / len(stats['response_times']) if stats['response_times'] else 0
    
    print(f"\r📊 Progress: {completed}/{CONFIG['total_requests']} ({percentage:.1f}%) | "
          f"✅ {stats['success']} | ❌ {stats['failed']} | "
          f"⚡ {stats['in_progress']} active | "
          f"⏱️  {avg_time:.0f}ms avg", end='', flush=True)

async def run_stress_test():
    """Run the concurrent stress test"""
    print('🚀 Starting Halo.rip Stress Test\n')
    print(f'📋 Configuration:')
    print(f'   - Total Requests: {CONFIG["total_requests"]}')
    print(f'   - Concurrent: {CONFIG["concurrent_requests"]}')
    print(f'   - Endpoint: {CONFIG["endpoint"]}')
    print(f'   - Cookie: {"✓ Set" if CONFIG["cookie"] else "✗ Missing"}\n')
    
    if not CONFIG['cookie']:
        print('❌ Error: No cookie provided!')
        print('\nUsage: python halo-stress-test.py "your-cookie-here"')
        print('   or: Edit CONFIG["cookie"] in the script\n')
        return
    
    start_time = time.time()
    
    # Create semaphore to limit concurrency
    semaphore = asyncio.Semaphore(CONFIG['concurrent_requests'])
    
    async def bounded_update(session, index):
        async with semaphore:
            result = await update_bio(session, index)
            show_progress()
            return result
    
    # Create session and run all requests
    async with aiohttp.ClientSession() as session:
        tasks = [
            bounded_update(session, i + 1)
            for i in range(CONFIG['total_requests'])
        ]
        
        stats['total'] = CONFIG['total_requests']
        results = await asyncio.gather(*tasks)
    
    total_time = time.time() - start_time
    
    # Final results
    print('\n\n✨ Stress Test Complete!\n')
    print('📈 Results:')
    print(f'   - Total Requests: {stats["total"]}')
    print(f'   - Successful: {stats["success"]} ({(stats["success"] / stats["total"] * 100):.1f}%)')
    print(f'   - Failed: {stats["failed"]} ({(stats["failed"] / stats["total"] * 100):.1f}%)')
    print(f'   - Total Time: {total_time:.2f}s')
    print(f'   - Requests/sec: {stats["total"] / total_time:.2f}')
    
    if stats['response_times']:
        sorted_times = sorted(stats['response_times'])
        print('\n⏱️  Response Times:')
        print(f'   - Average: {sum(sorted_times) / len(sorted_times):.0f}ms')
        print(f'   - Median: {sorted_times[len(sorted_times) // 2]:.0f}ms')
        print(f'   - Min: {sorted_times[0]:.0f}ms')
        print(f'   - Max: {sorted_times[-1]:.0f}ms')
        print(f'   - P95: {sorted_times[int(len(sorted_times) * 0.95)]:.0f}ms')
        print(f'   - P99: {sorted_times[int(len(sorted_times) * 0.99)]:.0f}ms')
    
    if stats['errors']:
        print('\n❌ Errors:')
        for error, count in stats['errors'].items():
            print(f'   - {error}: {count}x')
    
    print()

def main():
    """Entry point"""
    import sys
    
    # Allow cookie to be passed as command line argument
    if len(sys.argv) > 1:
        CONFIG['cookie'] = sys.argv[1]
    
    try:
        asyncio.run(run_stress_test())
    except KeyboardInterrupt:
        print('\n\n⚠️  Interrupted! Current stats:')
        show_progress()
        print('\n')

if __name__ == '__main__':
    main()
