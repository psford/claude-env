"""Generate 10 minimal WHITE icon variations based on design #4."""
from PIL import Image, ImageDraw
import os

OUTPUT_DIR = "stream_deck_icons/minimal_white"
SIZE = 144  # 144x144 for high-res Stream Deck


def create_minimal_1():
    """Original - white on pure black."""
    img = Image.new('RGB', (SIZE, SIZE), '#000000')
    draw = ImageDraw.Draw(img)
    draw.ellipse([50, 30, 94, 80], outline='white', width=4)
    draw.line([52, 55, 52, 80], fill='white', width=4)
    draw.line([92, 55, 92, 80], fill='white', width=4)
    draw.arc([35, 55, 109, 120], 0, 180, fill='white', width=4)
    draw.line([72, 120, 72, 130], fill='white', width=4)
    draw.line([52, 130, 92, 130], fill='white', width=4)
    return img, "m1_pure_black"


def create_minimal_2():
    """White on charcoal gray."""
    img = Image.new('RGB', (SIZE, SIZE), '#2d2d2d')
    draw = ImageDraw.Draw(img)
    draw.ellipse([50, 30, 94, 80], outline='white', width=4)
    draw.line([52, 55, 52, 80], fill='white', width=4)
    draw.line([92, 55, 92, 80], fill='white', width=4)
    draw.arc([35, 55, 109, 120], 0, 180, fill='white', width=4)
    draw.line([72, 120, 72, 130], fill='white', width=4)
    draw.line([52, 130, 92, 130], fill='white', width=4)
    return img, "m2_charcoal"


def create_minimal_3():
    """White on deep navy."""
    img = Image.new('RGB', (SIZE, SIZE), '#0a1628')
    draw = ImageDraw.Draw(img)
    draw.ellipse([50, 30, 94, 80], outline='white', width=4)
    draw.line([52, 55, 52, 80], fill='white', width=4)
    draw.line([92, 55, 92, 80], fill='white', width=4)
    draw.arc([35, 55, 109, 120], 0, 180, fill='white', width=4)
    draw.line([72, 120, 72, 130], fill='white', width=4)
    draw.line([52, 130, 92, 130], fill='white', width=4)
    return img, "m3_navy"


def create_minimal_4():
    """Thin delicate lines on black."""
    img = Image.new('RGB', (SIZE, SIZE), '#000000')
    draw = ImageDraw.Draw(img)
    draw.ellipse([50, 30, 94, 80], outline='white', width=2)
    draw.line([52, 55, 52, 80], fill='white', width=2)
    draw.line([92, 55, 92, 80], fill='white', width=2)
    draw.arc([35, 55, 109, 120], 0, 180, fill='white', width=2)
    draw.line([72, 120, 72, 130], fill='white', width=2)
    draw.line([52, 130, 92, 130], fill='white', width=2)
    return img, "m4_thin"


def create_minimal_5():
    """Bold thick lines on black."""
    img = Image.new('RGB', (SIZE, SIZE), '#000000')
    draw = ImageDraw.Draw(img)
    draw.ellipse([46, 26, 98, 84], outline='white', width=6)
    draw.line([48, 55, 48, 84], fill='white', width=6)
    draw.line([96, 55, 96, 84], fill='white', width=6)
    draw.arc([30, 52, 114, 124], 0, 180, fill='white', width=6)
    draw.line([72, 124, 72, 136], fill='white', width=6)
    draw.line([46, 136, 98, 136], fill='white', width=6)
    return img, "m5_bold"


def create_minimal_6():
    """White on slate blue."""
    img = Image.new('RGB', (SIZE, SIZE), '#2c3e50')
    draw = ImageDraw.Draw(img)
    draw.ellipse([50, 30, 94, 80], outline='white', width=4)
    draw.line([52, 55, 52, 80], fill='white', width=4)
    draw.line([92, 55, 92, 80], fill='white', width=4)
    draw.arc([35, 55, 109, 120], 0, 180, fill='white', width=4)
    draw.line([72, 120, 72, 130], fill='white', width=4)
    draw.line([52, 130, 92, 130], fill='white', width=4)
    return img, "m6_slate_blue"


def create_minimal_7():
    """White on deep purple."""
    img = Image.new('RGB', (SIZE, SIZE), '#1a0a2e')
    draw = ImageDraw.Draw(img)
    draw.ellipse([50, 30, 94, 80], outline='white', width=4)
    draw.line([52, 55, 52, 80], fill='white', width=4)
    draw.line([92, 55, 92, 80], fill='white', width=4)
    draw.arc([35, 55, 109, 120], 0, 180, fill='white', width=4)
    draw.line([72, 120, 72, 130], fill='white', width=4)
    draw.line([52, 130, 92, 130], fill='white', width=4)
    return img, "m7_purple"


def create_minimal_8():
    """White on dark teal."""
    img = Image.new('RGB', (SIZE, SIZE), '#0d3b3b')
    draw = ImageDraw.Draw(img)
    draw.ellipse([50, 30, 94, 80], outline='white', width=4)
    draw.line([52, 55, 52, 80], fill='white', width=4)
    draw.line([92, 55, 92, 80], fill='white', width=4)
    draw.arc([35, 55, 109, 120], 0, 180, fill='white', width=4)
    draw.line([72, 120, 72, 130], fill='white', width=4)
    draw.line([52, 130, 92, 130], fill='white', width=4)
    return img, "m8_teal"


def create_minimal_9():
    """White on dark olive/forest."""
    img = Image.new('RGB', (SIZE, SIZE), '#1a2618')
    draw = ImageDraw.Draw(img)
    draw.ellipse([50, 30, 94, 80], outline='white', width=4)
    draw.line([52, 55, 52, 80], fill='white', width=4)
    draw.line([92, 55, 92, 80], fill='white', width=4)
    draw.arc([35, 55, 109, 120], 0, 180, fill='white', width=4)
    draw.line([72, 120, 72, 130], fill='white', width=4)
    draw.line([52, 130, 92, 130], fill='white', width=4)
    return img, "m9_forest"


def create_minimal_10():
    """Off-white on soft black - gentler contrast."""
    img = Image.new('RGB', (SIZE, SIZE), '#121212')
    draw = ImageDraw.Draw(img)
    color = '#e8e8e8'
    draw.ellipse([50, 30, 94, 80], outline=color, width=4)
    draw.line([52, 55, 52, 80], fill=color, width=4)
    draw.line([92, 55, 92, 80], fill=color, width=4)
    draw.arc([35, 55, 109, 120], 0, 180, fill=color, width=4)
    draw.line([72, 120, 72, 130], fill=color, width=4)
    draw.line([52, 130, 92, 130], fill=color, width=4)
    return img, "m10_soft_contrast"


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    generators = [
        create_minimal_1,
        create_minimal_2,
        create_minimal_3,
        create_minimal_4,
        create_minimal_5,
        create_minimal_6,
        create_minimal_7,
        create_minimal_8,
        create_minimal_9,
        create_minimal_10,
    ]

    print(f"Generating {len(generators)} minimal white icon variations...")
    for gen in generators:
        img, name = gen()
        path = os.path.join(OUTPUT_DIR, f"{name}.png")
        img.save(path, "PNG")
        print(f"  Created: {path}")

    print(f"\nDone! Icons saved to {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
