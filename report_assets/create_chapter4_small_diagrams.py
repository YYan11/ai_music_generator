from PIL import Image, ImageDraw, ImageFont


def get_font(size, bold=False):
    candidates = [
        "arialbd.ttf" if bold else "arial.ttf",
        "calibrib.ttf" if bold else "calibri.ttf",
        "timesbd.ttf" if bold else "times.ttf",
    ]
    for name in candidates:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


FONT = get_font(18)
SMALL = get_font(15)
CAPTION = get_font(18)
CAPTION_BOLD = get_font(18, True)


def center(draw, x, y, text, font=FONT):
    lines = text.split("\n")
    sizes = [draw.textbbox((0, 0), line, font=font) for line in lines]
    widths = [box[2] - box[0] for box in sizes]
    heights = [box[3] - box[1] for box in sizes]
    total = sum(heights) + (len(lines) - 1) * 4
    current = y - total / 2
    for idx, line in enumerate(lines):
        draw.text((x - widths[idx] / 2, current), line, font=font, fill="black")
        current += heights[idx] + 4


def box(draw, x, y, w, h, text):
    draw.rectangle((x, y, x + w, y + h), outline="black", width=2, fill="white")
    center(draw, x + w / 2, y + h / 2, text)


def cylinder(draw, x, y, w, h, text):
    draw.ellipse((x, y, x + w, y + 35), outline="black", width=2, fill="white")
    draw.line((x, y + 18, x, y + h - 18), fill="black", width=2)
    draw.line((x + w, y + 18, x + w, y + h - 18), fill="black", width=2)
    draw.arc((x, y + h - 35, x + w, y + h), 0, 180, fill="black", width=2)
    center(draw, x + w / 2, y + h / 2 + 4, text, SMALL)


def user(draw, x, y):
    draw.ellipse((x - 12, y, x + 12, y + 24), outline="black", width=2)
    draw.line((x, y + 24, x, y + 72), fill="black", width=2)
    draw.line((x - 34, y + 42, x + 34, y + 42), fill="black", width=2)
    draw.line((x, y + 72, x - 28, y + 108), fill="black", width=2)
    draw.line((x, y + 72, x + 28, y + 108), fill="black", width=2)
    center(draw, x, y + 130, "User", SMALL)


def browser(draw, x, y, w, h, text):
    draw.rounded_rectangle((x, y, x + w, y + h), radius=10, outline="black", width=2, fill="white")
    draw.line((x, y + 22, x + w, y + 22), fill="black", width=1)
    draw.ellipse((x + 8, y + 8, x + 14, y + 14), outline="black", width=1)
    draw.ellipse((x + 20, y + 8, x + 26, y + 14), outline="black", width=1)
    center(draw, x + w / 2, y + h / 2 + 8, text, SMALL)


def arrow(draw, start, end):
    import math

    x1, y1 = start
    x2, y2 = end
    draw.line((x1, y1, x2, y2), fill="black", width=2)
    angle = math.atan2(y2 - y1, x2 - x1)
    size = 10
    left = angle + math.pi * 0.82
    right = angle - math.pi * 0.82
    p1 = (x2, y2)
    p2 = (x2 + size * math.cos(left), y2 + size * math.sin(left))
    p3 = (x2 + size * math.cos(right), y2 + size * math.sin(right))
    draw.polygon([p1, p2, p3], fill="black")


def label(draw, x, y, text):
    bbox = draw.textbbox((x, y), text, font=SMALL)
    draw.rectangle((bbox[0] - 2, bbox[1] - 1, bbox[2] + 2, bbox[3] + 1), fill="white")
    draw.text((x, y), text, font=SMALL, fill="black")


def caption(draw, number, text, width, y):
    prefix = f"Figure {number}"
    left = 235
    draw.text((left, y), prefix, font=CAPTION_BOLD, fill="black")
    draw.text((left + 90, y), text, font=CAPTION, fill="black")


def create_history_diagram():
    img = Image.new("RGB", (900, 390), "white")
    d = ImageDraw.Draw(img)

    user(d, 90, 85)
    browser(d, 185, 95, 120, 85, "Web\nApplication")
    box(d, 380, 125, 140, 75, "Flask API\nsave history")
    cylinder(d, 640, 45, 115, 82, "Cloud\nFirestore")
    cylinder(d, 640, 220, 115, 82, "Firebase\nStorage")

    arrow(d, (125, 125), (185, 125))
    label(d, 135, 100, "generate")
    arrow(d, (305, 145), (380, 160))
    label(d, 322, 126, "call")
    arrow(d, (520, 145), (640, 85))
    label(d, 560, 75, "metadata")
    arrow(d, (520, 190), (640, 258))
    label(d, 535, 222, "MIDI / WAV files")
    arrow(d, (755, 85), (810, 85))
    arrow(d, (810, 85), (810, 260))
    arrow(d, (810, 260), (755, 260))
    label(d, 770, 165, "file reference")

    caption(d, "4.3", "System architecture diagram for saving generated music history.", 900, 330)
    img.save("report_assets/system_architecture_save_history.png")


def create_generation_diagram():
    img = Image.new("RGB", (900, 390), "white")
    d = ImageDraw.Draw(img)

    user(d, 90, 85)
    browser(d, 185, 95, 120, 85, "Web\nApplication")
    box(d, 380, 92, 140, 75, "Flask\nREST API")
    box(d, 585, 92, 150, 75, "Emotion and\nMapping")
    box(d, 775, 92, 115, 75, "Music\nGenerator")
    cylinder(d, 715, 232, 145, 80, "Output\nMIDI / WAV")

    arrow(d, (125, 125), (185, 125))
    label(d, 132, 92, "text prompt")
    arrow(d, (305, 125), (380, 125))
    label(d, 306, 88, "POST /api/generate")
    arrow(d, (520, 125), (585, 125))
    label(d, 535, 92, "process")
    arrow(d, (735, 125), (775, 125))
    label(d, 735, 92, "conditions")
    arrow(d, (835, 167), (792, 232))
    label(d, 840, 188, "store")
    arrow(d, (715, 270), (305, 165))
    label(d, 405, 248, "return MIDI / WAV result")

    caption(d, "4.4", "System architecture diagram for music generation request.", 900, 330)
    img.save("report_assets/system_architecture_music_generation.png")


create_history_diagram()
create_generation_diagram()
print("report_assets/system_architecture_save_history.png")
print("report_assets/system_architecture_music_generation.png")
