const sharpLayer = document.getElementById('sharpLayer');

function moveSpotlight(e) {
    // Check if it's a touch event or a mouse event
    const x = e.touches ? e.touches[0].clientX : e.clientX;
    const y = e.touches ? e.touches[0].clientY : e.clientY;
    
    // Smaller circle for mobile (150px) vs Desktop (250px)
    const radius = window.innerWidth < 768 ? '150px' : '250px';
    
    const maskValue = `radial-gradient(circle ${radius} at ${x}px ${y}px, black 0%, transparent 80%)`;
    
    sharpLayer.style.webkitMaskImage = maskValue;
    sharpLayer.style.maskImage = maskValue;
}

// Mouse movement for Desktop
document.addEventListener('mousemove', moveSpotlight);

// Touch movement for Mobile
document.addEventListener('touchmove', (e) => {
    moveSpotlight(e);
}, { passive: true });

document.addEventListener('touchstart', (e) => {
    moveSpotlight(e);
}, { passive: true });