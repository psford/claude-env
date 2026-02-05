"""Generate 10 Stream Deck icon prototypes for voice dictation."""
from PIL import Image, ImageDraw
import os

OUTPUT_DIR = "stream_deck_icons"
SIZE = 144  # 144x144 for high-res Stream Deck

def create_icon_1():
    """Classic microphone - blue gradient."""
    img = Image.new('RGB', (SIZE, SIZE), '#1565C0')
    draw = ImageDraw.Draw(img)
    # Gradient-like effect with circles
    draw.ellipse([10, 10, SIZE-10, SIZE-10], fill='#2196F3')
    draw.ellipse([20, 20, SIZE-20, SIZE-20], fill='#42A5F5')
    # White mic
    draw.ellipse([50, 25, 94, 75], fill='white')
    draw.rectangle([62, 75, 82, 95], fill='white')
    draw.arc([40, 55, 104, 115], 0, 180, fill='white', width=6)
    draw.line([72, 115, 72, 125], fill='white', width=6)
    draw.line([52, 125, 92, 125], fill='white', width=6)
    return img, "1_classic_blue"

def create_icon_2():
    """Neon pink mic on dark."""
    img = Image.new('RGB', (SIZE, SIZE), '#1a1a2e')
    draw = ImageDraw.Draw(img)
    # Glow effect
    for i in range(3):
        offset = (3-i) * 4
        alpha = 100 + i * 50
        draw.ellipse([45-offset, 20-offset, 99+offset, 80+offset], outline='#ff71ce', width=2)
    # Mic
    draw.ellipse([50, 25, 94, 75], fill='#ff71ce')
    draw.rectangle([62, 75, 82, 95], fill='#ff71ce')
    draw.arc([40, 55, 104, 115], 0, 180, fill='#ff71ce', width=5)
    draw.line([72, 115, 72, 125], fill='#ff71ce', width=5)
    draw.line([52, 125, 92, 125], fill='#ff71ce', width=5)
    return img, "2_neon_pink"

def create_icon_3():
    """Sound wave bars."""
    img = Image.new('RGB', (SIZE, SIZE), '#2d3436')
    draw = ImageDraw.Draw(img)
    # Sound bars
    colors = ['#00cec9', '#00b894', '#55efc4', '#00b894', '#00cec9']
    heights = [40, 70, 100, 70, 40]
    bar_width = 18
    gap = 8
    start_x = 20
    for i, (h, c) in enumerate(zip(heights, colors)):
        x = start_x + i * (bar_width + gap)
        y_top = (SIZE - h) // 2
        draw.rounded_rectangle([x, y_top, x + bar_width, y_top + h], radius=9, fill=c)
    return img, "3_sound_waves"

def create_icon_4():
    """Minimal white mic on black."""
    img = Image.new('RGB', (SIZE, SIZE), '#000000')
    draw = ImageDraw.Draw(img)
    # Simple white mic outline
    draw.ellipse([50, 30, 94, 80], outline='white', width=4)
    draw.line([52, 55, 52, 80], fill='white', width=4)
    draw.line([92, 55, 92, 80], fill='white', width=4)
    draw.arc([35, 55, 109, 120], 0, 180, fill='white', width=4)
    draw.line([72, 120, 72, 130], fill='white', width=4)
    draw.line([52, 130, 92, 130], fill='white', width=4)
    return img, "4_minimal_white"

def create_icon_5():
    """Speech bubble with mic."""
    img = Image.new('RGB', (SIZE, SIZE), '#6c5ce7')
    draw = ImageDraw.Draw(img)
    # Speech bubble
    draw.rounded_rectangle([15, 15, SIZE-15, SIZE-35], radius=20, fill='white')
    draw.polygon([(50, SIZE-35), (70, SIZE-35), (40, SIZE-10)], fill='white')
    # Small mic inside
    draw.ellipse([55, 35, 89, 75], fill='#6c5ce7')
    draw.rectangle([65, 75, 79, 88], fill='#6c5ce7')
    draw.arc([50, 60, 94, 100], 0, 180, fill='#6c5ce7', width=4)
    return img, "5_speech_bubble"

def create_icon_6():
    """Orange/red recording style."""
    img = Image.new('RGB', (SIZE, SIZE), '#2d3436')
    draw = ImageDraw.Draw(img)
    # Red circle (recording indicator)
    draw.ellipse([20, 20, SIZE-20, SIZE-20], fill='#d63031')
    # White mic
    draw.ellipse([52, 35, 92, 80], fill='white')
    draw.rectangle([63, 80, 81, 95], fill='white')
    draw.arc([45, 65, 99, 115], 0, 180, fill='white', width=5)
    draw.line([72, 115, 72, 122], fill='white', width=5)
    draw.line([55, 122, 89, 122], fill='white', width=5)
    return img, "6_recording_red"

def create_icon_7():
    """Waveform with mic silhouette."""
    img = Image.new('RGB', (SIZE, SIZE), '#0984e3')
    draw = ImageDraw.Draw(img)
    # Waveform lines
    import math
    for i in range(0, SIZE, 6):
        h = int(30 + 25 * math.sin(i * 0.1) + 15 * math.sin(i * 0.2))
        y1 = SIZE//2 - h//2
        y2 = SIZE//2 + h//2
        draw.line([i, y1, i, y2], fill='#74b9ff', width=3)
    # Mic silhouette overlay
    draw.ellipse([50, 30, 94, 80], fill='white')
    draw.rectangle([62, 80, 82, 95], fill='white')
    draw.arc([42, 65, 102, 115], 0, 180, fill='white', width=5)
    draw.line([72, 115, 72, 125], fill='white', width=5)
    return img, "7_waveform"

def create_icon_8():
    """Gradient purple to blue."""
    img = Image.new('RGB', (SIZE, SIZE), '#667eea')
    draw = ImageDraw.Draw(img)
    # Fake gradient with rectangles
    for i in range(SIZE):
        r = int(102 + (118-102) * i / SIZE)
        g = int(126 + (75-126) * i / SIZE)
        b = int(234 + (109-234) * i / SIZE)
        draw.line([0, i, SIZE, i], fill=(r, g, b))
    # White mic
    draw.ellipse([50, 28, 94, 78], fill='white')
    draw.rectangle([62, 78, 82, 95], fill='white')
    draw.arc([40, 60, 104, 118], 0, 180, fill='white', width=5)
    draw.line([72, 118, 72, 128], fill='white', width=5)
    draw.line([52, 128, 92, 128], fill='white', width=5)
    return img, "8_gradient_purple"

def create_icon_9():
    """Podcast style - dual tone."""
    img = Image.new('RGB', (SIZE, SIZE), '#fdcb6e')
    draw = ImageDraw.Draw(img)
    # Dark mic shape
    draw.ellipse([45, 20, 99, 85], fill='#2d3436')
    draw.rounded_rectangle([55, 85, 89, 105], radius=5, fill='#2d3436')
    # Stand
    draw.ellipse([30, 100, 114, 140], outline='#2d3436', width=6)
    draw.rectangle([68, 105, 76, 140], fill='#2d3436')
    # Highlight
    draw.ellipse([55, 30, 70, 50], fill='#636e72')
    return img, "9_podcast_gold"

def create_icon_10():
    """Cyberpunk style."""
    img = Image.new('RGB', (SIZE, SIZE), '#0a0a0f')
    draw = ImageDraw.Draw(img)
    # Cyan border
    draw.rectangle([5, 5, SIZE-5, SIZE-5], outline='#01cdfe', width=3)
    # Corner accents
    draw.line([5, 5, 25, 5], fill='#ff71ce', width=3)
    draw.line([5, 5, 5, 25], fill='#ff71ce', width=3)
    draw.line([SIZE-5, SIZE-5, SIZE-25, SIZE-5], fill='#ff71ce', width=3)
    draw.line([SIZE-5, SIZE-5, SIZE-5, SIZE-25], fill='#ff71ce', width=3)
    # Cyan mic
    draw.ellipse([50, 30, 94, 80], outline='#01cdfe', width=3)
    draw.ellipse([50, 30, 94, 80], fill='#01cdfe')
    draw.rectangle([62, 80, 82, 95], fill='#01cdfe')
    draw.arc([42, 65, 102, 115], 0, 180, fill='#01cdfe', width=4)
    draw.line([72, 115, 72, 125], fill='#01cdfe', width=4)
    draw.line([55, 125, 89, 125], fill='#01cdfe', width=4)
    return img, "10_cyberpunk"


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    generators = [
        create_icon_1,
        create_icon_2,
        create_icon_3,
        create_icon_4,
        create_icon_5,
        create_icon_6,
        create_icon_7,
        create_icon_8,
        create_icon_9,
        create_icon_10,
    ]

    print(f"Generating {len(generators)} Stream Deck icons...")
    for gen in generators:
        img, name = gen()
        path = os.path.join(OUTPUT_DIR, f"{name}.png")
        img.save(path, "PNG")
        print(f"  Created: {path}")

    print(f"\nDone! Icons saved to {OUTPUT_DIR}/")
    print("Open the folder to preview them.")


if __name__ == "__main__":
    main()
