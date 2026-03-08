const sharpLayer = document.getElementById('sharpLayer');

/**
 * Handles the spotlight movement for both Mouse and Touch
 * @param {Event} e - The mouse or touch event
 */
function handleMove(e) {
    // Get coordinates for either Mouse or Touch
    const x = e.touches ? e.touches[0].clientX : e.clientX;
    const y = e.touches ? e.touches[0].clientY : e.clientY;

    // Set radius: 150px for mobile, 250px for desktop
    const radius = window.innerWidth < 768 ? '350px' : '450px';

    // Apply the radial gradient mask
    // 'black 0%' is the clear part, 'transparent 80%' is the blur/fade
    const maskValue = `radial-gradient(circle ${radius} at ${x}px ${y}px, black 0%, transparent 80%)`;

    if (sharpLayer) {
        sharpLayer.style.webkitMaskImage = maskValue;
        sharpLayer.style.maskImage = maskValue;
    }
}

// Listen for Desktop mouse movement
document.addEventListener('mousemove', handleMove);

// Listen for Mobile touch movement (passive: true improves scroll performance)
document.addEventListener('touchmove', handleMove, { passive: true });
document.addEventListener('touchstart', handleMove, { passive: true });

// Optional: Initialize the spotlight in the center on page load
window.addEventListener('load', () => {
    const initialEvent = {
        clientX: window.innerWidth / 2,
        clientY: window.innerHeight / 2
    };
    handleMove(initialEvent);
});