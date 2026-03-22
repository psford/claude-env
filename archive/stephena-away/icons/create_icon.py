"""
Create StephenA Away icon with prohibition sign overlay.
Crops face to circle, embeds in SVG with red "NO" sign.
"""

from PIL import Image, ImageDraw
import base64
import io

def create_circular_crop(img, size):
    """Crop image to a circle and resize."""
    # Make square crop centered on face (upper portion of image)
    width, height = img.size

    # Focus on face area - crop from top, centered horizontally
    crop_size = min(width, height)
    left = (width - crop_size) // 2
    top = 0  # Start from top to get the face
    right = left + crop_size
    bottom = crop_size

    img_cropped = img.crop((left, top, right, bottom))
    img_resized = img_cropped.resize((size, size), Image.LANCZOS)

    # Create circular mask
    mask = Image.new('L', (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size, size), fill=255)

    # Apply mask
    output = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    output.paste(img_resized, (0, 0))
    output.putalpha(mask)

    return output

def image_to_base64(img):
    """Convert PIL Image to base64 string."""
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    return base64.b64encode(buffer.getvalue()).decode('utf-8')

def create_svg_icon(img_base64, size):
    """Create SVG with embedded image and prohibition sign."""
    # Calculate dimensions
    center = size // 2
    radius = (size // 2) - 2
    stroke_width = size // 10

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg"
     xmlns:xlink="http://www.w3.org/1999/xlink"
     width="{size}" height="{size}" viewBox="0 0 {size} {size}">

  <!-- Circular clipping path -->
  <defs>
    <clipPath id="circleClip">
      <circle cx="{center}" cy="{center}" r="{radius}"/>
    </clipPath>
  </defs>

  <!-- Stephen A face (clipped to circle) -->
  <image
    xlink:href="data:image/png;base64,{img_base64}"
    x="0" y="0"
    width="{size}" height="{size}"
    clip-path="url(#circleClip)"
    preserveAspectRatio="xMidYMid slice"/>

  <!-- Red prohibition circle -->
  <circle
    cx="{center}" cy="{center}" r="{radius}"
    fill="none"
    stroke="#d32f2f"
    stroke-width="{stroke_width}"/>

  <!-- Diagonal slash -->
  <line
    x1="{center - radius * 0.7}" y1="{center - radius * 0.7}"
    x2="{center + radius * 0.7}" y2="{center + radius * 0.7}"
    stroke="#d32f2f"
    stroke-width="{stroke_width}"
    stroke-linecap="round"/>
</svg>'''

    return svg

def main():
    # Load the source image
    img = Image.open('stephen_a.jpg').convert('RGBA')

    # Create icons at different sizes
    for size in [48, 96]:
        # Create circular crop
        circular = create_circular_crop(img, size)

        # Convert to base64
        img_base64 = image_to_base64(circular)

        # Create SVG
        svg = create_svg_icon(img_base64, size)

        # Save
        output_path = f'icon-{size}.svg'
        with open(output_path, 'w') as f:
            f.write(svg)
        print(f'Created {output_path}')

if __name__ == '__main__':
    main()
