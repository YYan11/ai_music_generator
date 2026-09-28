from PIL import Image, ImageDraw, ImageFont


W, H = 900, 1100
OUT = "report_assets/text_muse_system_architecture.png"


def font(size, bold=False):
    names = [
        "arialbd.ttf" if bold else "arial.ttf",
        "timesbd.ttf" if bold else "times.ttf",
        "calibrib.ttf" if bold else "calibri.ttf",
    ]
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


F_SMALL = font(16)
F_MED = font(18)
F_LABEL = font(15)
F_CAPTION = font(20)
F_CAPTION_BOLD = font(20, True)


img = Image.new("RGB", (W, H), "white")
d = ImageDraw.Draw(img)


def center_text(x, y, text, f=F_SMALL):
    box = d.textbbox((0, 0), text, font=f)
    d.text((x - (box[2] - box[0]) / 2, y), text, fill="black", font=f)


def rect(x1, y1, x2, y2, radius=10):
    d.rounded_rectangle((x1, y1, x2, y2), radius=radius, outline="black", width=2, fill="white")


def outer(x1, y1, x2, y2):
    d.rectangle((x1, y1, x2, y2), outline="black", width=2, fill="white")


def arrow_line(p1, p2, both=False, dashed=False):
    x1, y1 = p1
    x2, y2 = p2
    if dashed:
        dash = 8
        gap = 6
        length = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
        if length == 0:
            return
        ux, uy = (x2 - x1) / length, (y2 - y1) / length
        t = 0
        while t < length:
            t2 = min(t + dash, length)
            d.line((x1 + ux * t, y1 + uy * t, x1 + ux * t2, y1 + uy * t2), fill="black", width=2)
            t += dash + gap
    else:
        d.line((x1, y1, x2, y2), fill="black", width=2)
    draw_arrow_head(x1, y1, x2, y2)
    if both:
        draw_arrow_head(x2, y2, x1, y1)


def draw_arrow_head(x1, y1, x2, y2):
    import math

    angle = math.atan2(y2 - y1, x2 - x1)
    size = 12
    left = angle + math.pi * 0.82
    right = angle - math.pi * 0.82
    p1 = (x2, y2)
    p2 = (x2 + size * math.cos(left), y2 + size * math.sin(left))
    p3 = (x2 + size * math.cos(right), y2 + size * math.sin(right))
    d.polygon([p1, p2, p3], fill="black")


def user_icon(cx, top, label):
    d.ellipse((cx - 17, top, cx + 17, top + 34), outline="black", width=2, fill="white")
    d.line((cx - 30, top + 85, cx - 30, top + 62), fill="black", width=2)
    d.arc((cx - 30, top + 40, cx + 30, top + 84), 180, 360, fill="black", width=2)
    d.line((cx + 30, top + 62, cx + 30, top + 85), fill="black", width=2)
    d.line((cx - 30, top + 85, cx + 30, top + 85), fill="black", width=2)
    center_text(cx, top + 102, label, F_LABEL)


user_icon(215, 28, "User")
user_icon(445, 28, "Student User")
user_icon(675, 28, "Admin / Tester")

arrow_line((215, 155), (215, 230), both=True)
arrow_line((445, 155), (445, 230), both=True)
arrow_line((675, 155), (675, 230), both=True)

outer(70, 215, 830, 425)
rect(105, 245, 795, 303)
center_text(450, 268, "Text Muse Web Interface", F_MED)

rect(105, 335, 285, 397)
center_text(195, 354, "Login / Register")
center_text(195, 375, "Password Reset")
rect(360, 335, 540, 397)
center_text(450, 354, "Chat Prompt")
center_text(450, 375, "Music Request")
rect(615, 335, 795, 397)
center_text(705, 354, "Playback / Download")
center_text(705, 375, "History Page")

arrow_line((195, 305), (195, 330), both=True)
arrow_line((450, 305), (450, 330), both=True)
arrow_line((705, 305), (705, 330), both=True)

outer(70, 485, 830, 725)
rect(105, 535, 285, 610)
center_text(195, 558, "Authentication")
center_text(195, 579, "Service")
rect(360, 535, 540, 610)
center_text(450, 558, "Flask Backend")
center_text(450, 579, "API Controller")
rect(615, 535, 795, 610)
center_text(705, 558, "History")
center_text(705, 579, "Service")
rect(232, 640, 412, 695)
center_text(322, 658, "Emotion Detection")
center_text(322, 679, "Module")
rect(488, 640, 668, 695)
center_text(578, 658, "Music Mapping")
center_text(578, 679, "Module")

arrow_line((450, 425), (450, 530), both=True)
arrow_line((285, 572), (355, 572), both=True)
arrow_line((540, 572), (610, 572), both=True)
arrow_line((450, 610), (350, 638))
arrow_line((412, 668), (486, 668))

outer(70, 785, 830, 990)
d.ellipse((65, 823, 345, 907), outline="black", width=2, fill="white")
d.line((65, 865, 65, 922), fill="black", width=2)
d.line((345, 865, 345, 922), fill="black", width=2)
d.arc((65, 880, 345, 964), 0, 180, fill="black", width=2)
center_text(205, 848, "Firebase Firestore")
center_text(205, 870, "User Generation History")
center_text(205, 892, "Prompt / Emotion / Files")

rect(390, 825, 570, 905)
center_text(480, 848, "Music Generation")
center_text(480, 870, "Baseline MIDI")
center_text(480, 892, "Optional MIDI-GPT")
rect(620, 825, 800, 905)
center_text(710, 848, "Generated Output")
center_text(710, 870, "MIDI File")
center_text(710, 892, "WAV Preview")

arrow_line((578, 695), (480, 820), both=True)
arrow_line((570, 865), (615, 865))
arrow_line((705, 610), (705, 820), dashed=True)
arrow_line((345, 885), (386, 885), both=True)
arrow_line((195, 610), (195, 820), dashed=True)

d.text((275, 805), "generation record", fill="black", font=F_LABEL)
d.text((610, 765), "music files", fill="black", font=F_LABEL)
d.text((500, 930), "emotion parameters", fill="black", font=F_LABEL)

d.text((310, 1050), "Figure 4.1", fill="black", font=F_CAPTION_BOLD)
d.text((412, 1050), "System Architecture Diagram.", fill="black", font=F_CAPTION)

img.save(OUT, "PNG")
print(OUT)
