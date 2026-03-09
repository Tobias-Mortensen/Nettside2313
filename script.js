const sharpLayer = document.getElementById('sharpLayer');
let currentUserPermission = 1; // Default

// --- Spotlight Logic ---
function handleMove(e) {
    const x = e.touches ? e.touches[0].clientX : e.clientX;
    const y = e.touches ? e.touches[0].clientY : e.clientY;
    const radius = window.innerWidth < 768 ? '150px' : '250px';
    const maskValue = `radial-gradient(circle ${radius} at ${x}px ${y}px, black 0%, transparent 80%)`;
    if (sharpLayer) {
        sharpLayer.style.webkitMaskImage = maskValue;
        sharpLayer.style.maskImage = maskValue;
    }
}
document.addEventListener('mousemove', handleMove);
document.addEventListener('touchmove', handleMove, { passive: true });
document.addEventListener('touchstart', handleMove, { passive: true });

// --- Chat Logic ---

// Toggle Window
document.getElementById('chat-toggle')?.addEventListener('click', () => {
    document.getElementById('chat-window').classList.toggle('hidden');
    scrollToBottom(true); // Snap to bottom when opened
});

// Check permission on load
async function checkUserStatus() {
    try {
        const res = await fetch('/api/user-status');
        const data = await res.json();
        if (data.loggedIn) {
            currentUserPermission = data.permission;
        }
    } catch (e) { console.error("Error checking status"); }
}

// Utility function for smooth scrolling
function scrollToBottom(force = false) {
    const container = document.getElementById('chat-messages');
    if (!container) return;

    const threshold = 150;
    const isNearBottom = container.scrollHeight - container.scrollTop <= container.clientHeight + threshold;

    if (force || isNearBottom) {
        container.scrollTo({
            top: container.scrollHeight,
            behavior: force ? 'auto' : 'smooth' // Snap if forced, smooth if automatic
        });
    }
}

async function loadMessages() {
    const res = await fetch('/api/chats');
    const data = await res.json();
    const container = document.getElementById('chat-messages');
    
    if (container) {
        container.innerHTML = data.map(m => {
            const deleteBtn = currentUserPermission >= 2 
                ? `<button class="del-btn" onclick="deleteMessage(${m.time})">×</button>` 
                : '';

            return `
                <div class="msg">
                    <b>${m.username}</b>
                    <span>${m.text}</span>
                    ${deleteBtn}
                </div>
            `;
        }).join('');
        
        scrollToBottom(); 
    }
}

// Function to handle sending
async function sendMessage() {
    const input = document.getElementById('chat-input');
    const charCounter = document.getElementById('char-count');
    const messageText = input.value.trim();
    if (!messageText) return;

    const res = await fetch('/send-chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: messageText }) 
    });

    if (res.ok) {
        input.value = '';
        if (charCounter) charCounter.textContent = '0/128'; // Reset counter UI
        await loadMessages();
        scrollToBottom(true); // Force scroll for user's own message
    } else if (res.status === 429) {
        alert("Slow down! 1 message per second.");
    }
}

// Click listener
document.getElementById('send-btn')?.addEventListener('click', sendMessage);

// Enter key listener
document.getElementById('chat-input')?.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        sendMessage();
    }
});

// Character Counter Listener
document.getElementById('chat-input')?.addEventListener('input', (e) => {
    const charCounter = document.getElementById('char-count');
    if (charCounter) {
        const len = e.target.value.length;
        charCounter.textContent = `${len}/128`;
        
        // Visual warning if near limit
        if (len >= 110) {
            charCounter.classList.add('warning');
        } else {
            charCounter.classList.remove('warning');
        }
    }
});

async function deleteMessage(timestamp) {
    if (!confirm("Confirm deletion?")) return;
    const res = await fetch(`/api/chats/${timestamp}`, { method: 'DELETE' });
    if (res.ok) {
        loadMessages();
    } else {
        alert("Permission denied.");
    }
}

// Initialization sequence
async function init() {
    await checkUserStatus();
    loadMessages();
    setInterval(loadMessages, 3000);
}

init();