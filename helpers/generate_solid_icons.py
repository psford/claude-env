"""Generate 10 solid white mic icons - Xbox/Steam style."""
from PIL import Image, ImageDraw
import os

OUTPUT_DIR = "stream_deck_icons/solid_white"
SIZE = 144


def create_icon_1():
    """Classic condenser mic - solid."""
    img = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 255))
    draw = ImageDraw.Draw(img)
    # Mic head
    draw.ellipse([44, 18, 100, 80], fill='white')
    # Mic body
    draw.rectangle([56, 80, 88, 100], fill='white')
    # Stand arc
    draw.arc([30, 60, 114, 130], 0, 180, fill='white', width=8)
    # Stand pole
    draw.rectangle([68, 125, 76, 138], fill='white')
    # Stand base
    draw.rectangle([48, 134, 96, 142], fill='white')
    return img, "s1_condenser"


def create_icon_2():
    """Rounded podcast mic."""
    img = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 255))
    draw = ImageDraw.Draw(img)
    # Rounded mic head
    draw.rounded_rectangle([40, 15, 104, 90], radius=32, fill='white')
    # Neck
    draw.rectangle([62, 90, 82, 108], fill='white')
    # Base circle
    draw.ellipse([50, 108, 94, 140], fill='white')
    return img, "s2_podcast"


def create_icon_3():
    """Simple pill mic."""
    img = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 255))
    draw = ImageDraw.Draw(img)
    # Pill shape mic
    draw.rounded_rectangle([48, 20, 96, 95], radius=24, fill='white')
    # Stand
    draw.arc([35, 65, 109, 125], 0, 180, fill='white', width=7)
    draw.rectangle([69, 120, 75, 135], fill='white')
    draw.rounded_rectangle([50, 132, 94, 140], radius=4, fill='white')
    return img, "s3_pill"


def create_icon_4():
    """Broadcast mic - rectangular."""
    img = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 255))
    draw = ImageDraw.Draw(img)
    # Rectangular mic with rounded top
    draw.rounded_rectangle([42, 18, 102, 95], radius=15, fill='white')
    # Neck
    draw.rectangle([64, 95, 80, 110], fill='white')
    # Tripod-style base
    draw.polygon([(72, 110), (45, 140), (55, 140), (72, 118)], fill='white')
    draw.polygon([(72, 110), (99, 140), (89, 140), (72, 118)], fill='white')
    return img, "s4_broadcast"


def create_icon_5():
    """Handheld mic - karaoke style."""
    img = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 255))
    draw = ImageDraw.Draw(img)
    # Mic ball head
    draw.ellipse([45, 12, 99, 66], fill='white')
    # Handle (tapered)
    draw.polygon([(52, 60), (92, 60), (85, 138), (59, 138)], fill='white')
    return img, "s5_handheld"


def create_icon_6():
    """Retro radio mic."""
    img = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 255))
    draw = ImageDraw.Draw(img)
    # Diamond/rounded square head
    draw.rounded_rectangle([38, 15, 106, 83], radius=20, fill='white')
    # Thick neck
    draw.rectangle([58, 83, 86, 105], fill='white')
    # Wide base
    draw.rounded_rectangle([42, 105, 102, 140], radius=10, fill='white')
    return img, "s6_retro"


def create_icon_7():
    """Sleek modern mic."""
    img = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 255))
    draw = ImageDraw.Draw(img)
    # Tall narrow mic
    draw.rounded_rectangle([52, 15, 92, 100], radius=20, fill='white')
    # Thin stand
    draw.arc([40, 70, 104, 125], 0, 180, fill='white', width=6)
    draw.rectangle([70, 122, 74, 138], fill='white')
    draw.ellipse([55, 132, 89, 144], fill='white')
    return img, "s7_modern"


def create_icon_8():
    """USB mic style."""
    img = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 255))
    draw = ImageDraw.Draw(img)
    # Cylindrical head
    draw.rounded_rectangle([44, 18, 100, 88], radius=28, fill='white')
    # Thick stem
    draw.rectangle([60, 88, 84, 108], fill='white')
    # Circular base
    draw.ellipse([38, 108, 106, 144], fill='white')
    return img, "s8_usb"


def create_icon_9():
    """Minimal abstract mic."""
    img = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 255))
    draw = ImageDraw.Draw(img)
    # Simple circle head
    draw.ellipse([42, 18, 102, 78], fill='white')
    # Simple rectangle body
    draw.rectangle([60, 78, 84, 140], fill='white')
    return img, "s9_abstract"


def create_icon_10():
    """Studio mic with mount."""
    img = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 255))
    draw = ImageDraw.Draw(img)
    # Large oval head
    draw.ellipse([38, 22, 106, 95], fill='white')
    # Mount ring (draw as filled shape around mic)
    # Left bracket
    draw.rectangle([28, 45, 38, 72], fill='white')
    # Right bracket
    draw.rectangle([106, 45, 116, 72], fill='white')
    # Bottom connector
    draw.rectangle([64, 95, 80, 115], fill='white')
    # Arm hint
    draw.polygon([(72, 115), (30, 140), (42, 140), (72, 122)], fill='white')
    return img, "s10_studio"


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

    print(f"Generating {len(generators)} solid white icons...")
    for gen in generators:
        img, name = gen()
        path = os.path.join(OUTPUT_DIR, f"{name}.png")
        img.save(path, "PNG")
        print(f"  Created: {path}")

    print(f"\nDone! Icons saved to {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
