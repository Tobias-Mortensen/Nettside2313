const sharpLayer = document.getElementById('sharpLayer');

document.addEventListener('mousemove', (e) => {
    const x = e.clientX;
    const y = e.clientY;
    
    // Increased circle to 250px
    const mask = `radial-gradient(circle 350px at ${x}px ${y}px, black 0%, transparent 80%)`;
    
    sharpLayer.style.webkitMaskImage = mask;
    sharpLayer.style.maskImage = mask;
});