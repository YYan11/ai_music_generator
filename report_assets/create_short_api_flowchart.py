from PIL import Image, ImageDraw, ImageFont


def font(size):
    for name in ("arial.ttf", "calibri.ttf", "times.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


F = font(22)
W = 1050
H = 1500
img = Image.new("RGB", (W, H), "white")
d = ImageDraw.Draw(img)


def center(text, x, y):
    lines = text.split("\n")
    heights = [d.textbbox((0, 0), line, font=F)[3] for line in lines]
    total = sum(heights) + 8 * (len(lines) - 1)
    top = y - total / 2
    for line in lines:
        box = d.textbbox((0, 0), line, font=F)
        d.text((x - (box[2] - box[0]) / 2, top), line, fill="black", font=F)
        top += box[3] + 8


def box(y, text, rounded=False):
    x, w, h = 175, 700, 100
    if rounded:
        d.rounded_rectangle((x, y, x + w, y + h), radius=45, outline="black", width=3, fill="white")
    else:
        d.rectangle((x, y, x + w, y + h), outline="black", width=3, fill="white")
    center(text, x + w / 2, y + h / 2)


def arrow(y1, y2):
    x = W / 2
    d.line((x, y1, x, y2 - 14), fill="black", width=3)
    d.polygon([(x, y2), (x - 10, y2 - 18), (x + 10, y2 - 18)], fill="black")


box(50, "Start", rounded=True)
box(210, "Enter Prompt")
box(370, "Frontend")
box(530, "POST /api/generate")
box(690, "Detect Emotion")
box(850, "Map Conditions")
box(1010, "Generate MIDI")
box(1170, "Return Result")
box(1330, "Play / Download", rounded=True)

for y1, y2 in zip((150, 310, 470, 630, 790, 950, 1110, 1270), (210, 370, 530, 690, 850, 1010, 1170, 1330)):
    arrow(y1, y2)

img.save("report_assets/music_generation_api_flowchart.png")
print("report_assets/music_generation_api_flowchart.png")
