// Simple icon generator
// Run this code in a browser console to generate icons

function generateIcon(size) {
  // Create a canvas element
  const canvas = document.createElement('canvas');
  canvas.width = size;
  canvas.height = size;
  
  // Get the 2D context
  const ctx = canvas.getContext('2d');
  
  // Background
  ctx.fillStyle = '#4285f4'; // Google blue
  ctx.fillRect(0, 0, size, size);
  
  // White key shape
  ctx.fillStyle = '#ffffff';
  
  // Draw a simple key shape
  const keySize = size * 0.6;
  const keyX = size * 0.2;
  const keyY = size * 0.2;
  
  // Key head (circle)
  ctx.beginPath();
  ctx.arc(keyX + keySize * 0.2, keyY + keySize * 0.2, keySize * 0.2, 0, Math.PI * 2);
  ctx.fill();
  
  // Key stem
  ctx.fillRect(keyX + keySize * 0.2, keyY + keySize * 0.3, keySize * 0.15, keySize * 0.5);
  
  // Key teeth
  ctx.fillRect(keyX + keySize * 0.2, keyY + keySize * 0.5, keySize * 0.5, keySize * 0.15);
  ctx.fillRect(keyX + keySize * 0.5, keyY + keySize * 0.5, keySize * 0.15, keySize * 0.3);
  
  // Border
  ctx.strokeStyle = '#3367d6'; // Darker blue
  ctx.lineWidth = size * 0.05;
  ctx.strokeRect(0, 0, size, size);
  
  // Return the data URL
  return canvas.toDataURL('image/png');
}

// Generate icons of different sizes
const sizes = [16, 48, 128];
sizes.forEach(size => {
  const dataUrl = generateIcon(size);
  
  console.log(`Icon ${size}x${size}:`);
  console.log(dataUrl);
  
  // You can also create a download link
  const link = document.createElement('a');
  link.download = `icon${size}.png`;
  link.href = dataUrl;
  link.textContent = `Download icon${size}.png`;
  document.body.appendChild(link);
  document.body.appendChild(document.createElement('br'));
}); 