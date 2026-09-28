from PIL import Image, ImageDraw, ImageFont


OUT = "report_assets/text_to_music_prompt_processing_flow.png"
W, H = 1600, 600


def get_font(size, bold=False):
    candidates = [
        "arialbd.ttf" if bold else "arial.ttf",
        "calibrib.ttf" if bold else "calibri.ttf",
        "timesbd.ttf" if bold else "times.ttf",
    ]
    for item in candidates:
        try:
            return ImageFont.truetype(item, size)
        except OSError:
            continue
    return ImageFont.load_default()


FONT = get_font(20)
FONT_SMALL = get_font(18)
FONT_BOLD = get_font(20, True)
CAPTION = get_font(22)
CAPTION_BOLD = get_font(22, True)


img = Image.new("RGB", (W, H), "white")
d = ImageDraw.Draw(img)


def text_center(x, y, text, font=FONT, line_gap=5):
    lines = text.split("\n")
    heights = []
    widths = []
    for line in lines:
        box = d.textbbox((0, 0), line, font=font)
        widths.append(box[2] - box[0])
        heights.append(box[3] - box[1])
    total_h = sum(heights) + line_gap * (len(lines) - 1)
    cy = y - total_h / 2
    for i, line in enumerate(lines):
        d.text((x - widths[i] / 2, cy), line, fill="black", font=font)
        cy += heights[i] + line_gap


def box(x, y, w, h, text, font=FONT):
    d.rectangle((x, y, x + w, y + h), outline="black", width=2, fill="white")
    text_center(x + w / 2, y + h / 2, text, font)
    return (x, y, x + w, y + h)


def diamond(cx, cy, w, h, text):
    pts = [(cx, cy - h / 2), (cx + w / 2, cy), (cx, cy + h / 2), (cx - w / 2, cy)]
    d.polygon(pts, outline="black", fill="white")
    d.line([pts[0], pts[1], pts[2], pts[3], pts[0]], fill="black", width=2)
    text_center(cx, cy, text, FONT_SMALL)
    return pts


def arrow(start, end):
    import math

    x1, y1 = start
    x2, y2 = end
    d.line((x1, y1, x2, y2), fill="black", width=2)
    angle = math.atan2(y2 - y1, x2 - x1)
    size = 12
    left = angle + math.pi * 0.82
    right = angle - math.pi * 0.82
    p1 = (x2, y2)
    p2 = (x2 + size * math.cos(left), y2 + size * math.sin(left))
    p3 = (x2 + size * math.cos(right), y2 + size * math.sin(right))
    d.polygon([p1, p2, p3], fill="black")


def label(x, y, value):
    d.text((x, y), value, fill="black", font=FONT_SMALL)


y = 150
h = 70
b1 = box(30, y, 190, h, "User Text\nInput")
b2 = box(285, y, 190, h, "Chatbot\nInterface")
b3 = box(540, y, 190, h, "Prompt\nAnalysis")
diamond(900, y + h / 2, 270, 130, "Emotion / Style /\nInstrument Found?")
b_yes = box(1075, 35, 245, h, "Structured\nMusic Request")
b_no = box(1075, 305, 245, h, "Neutral Default\nSetting")
b_map = box(1340, y, 230, h, "Music Parameter\nMapping")

arrow((220, y + h / 2), (285, y + h / 2))
arrow((475, y + h / 2), (540, y + h / 2))
arrow((730, y + h / 2), (765, y + h / 2))

arrow((900, y - 30), (1075, 70))
label(990, 94, "Yes")
arrow((900, 215), (1075, 340))
label(990, 250, "No")

arrow((1320, 70), (1340, 160))
arrow((1320, 340), (1340, 210))

# Right-side continuation column.
box(70, 450, 220, 70, "Send to Flask\nBackend")
box(385, 450, 230, 70, "Music Generation\nModule")
box(710, 450, 220, 70, "MIDI File +\nWAV Preview")
box(1025, 450, 210, 70, "Playback /\nDownload")
box(1320, 450, 220, 70, "Save to\nFirebase History")

arrow((1455, 220), (1455, 270))
arrow((1455, 270), (180, 270))
arrow((180, 270), (180, 450))
arrow((290, 485), (385, 485))
arrow((615, 485), (710, 485))
arrow((930, 485), (1025, 485))
arrow((1235, 485), (1320, 485))

d.text((645, 560), "Figure 4.2", fill="black", font=CAPTION_BOLD)
d.text((760, 560), "Text-to-Music Prompt Processing Flow.", fill="black", font=CAPTION)

img.save(OUT, "PNG")
print(OUT)
