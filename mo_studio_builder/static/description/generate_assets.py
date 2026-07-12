"""Generate Odoo Apps Store PNG assets for MO Studio Builder.

Run from the module root with:
    python static/description/generate_assets.py
"""

from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except Exception as exc:  # pragma: no cover - helper script
    raise SystemExit("Pillow is required to generate images: pip install pillow") from exc


BASE = Path(__file__).resolve().parent
INK = "#17212b"
MUTED = "#5d6b7a"
LINE = "#d9e2ea"
PANEL = "#f6f9fb"
BRAND = "#0f8f87"
ACCENT = "#6f4566"


def font(size, bold=False):
    names = [
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ]
    for name in names:
        if Path(name).exists():
            return ImageFont.truetype(name, size)
    return ImageFont.load_default()


def rounded(draw, box, fill, outline=None, width=1, radius=12):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def draw_topbar(draw, width):
    draw.rectangle((0, 0, width, 54), fill="#213843")
    draw.text((28, 16), "MO Studio Builder", fill="white", font=font(18, True))
    draw.text((230, 17), "App Builder", fill="#dbe6ea", font=font(15))
    rounded(draw, (width - 162, 11, width - 34, 43), ACCENT, radius=6)
    draw.text((width - 132, 18), "Studio", fill="white", font=font(15, True))


def save_icon():
    img = Image.new("RGBA", (512, 512), "white")
    d = ImageDraw.Draw(img)
    rounded(d, (40, 40, 472, 472), "#f7fbfb", LINE, 3, 46)
    d.polygon([(256, 86), (392, 164), (256, 242), (120, 164)], outline=BRAND, fill=None)
    d.line([(120, 164), (120, 324), (256, 404), (392, 324), (392, 164)], fill=BRAND, width=12)
    d.line([(256, 242), (256, 404)], fill=BRAND, width=12)
    d.line([(120, 164), (256, 242), (392, 164)], fill=BRAND, width=12)
    d.text((151, 205), "MO", fill=INK, font=font(72, True))
    d.text((149, 286), "Studio", fill=ACCENT, font=font(32, True))
    img.save(BASE / "icon.png")


def save_banner():
    img = Image.new("RGB", (1024, 512), "#ffffff")
    d = ImageDraw.Draw(img)
    for y in range(512):
        shade = int(246 - y * 0.045)
        d.line((0, y, 1024, y), fill=(shade, min(255, shade + 8), min(255, shade + 10)))
    rounded(d, (48, 56, 976, 456), "#ffffff", LINE, 2, 24)
    d.text((88, 104), "MO Studio Builder", fill=INK, font=font(54, True))
    d.text((90, 174), "Visual app builder for Odoo 17", fill=MUTED, font=font(28))
    for i, text in enumerate(["Header Studio button", "Live preview", "Drag and drop", "Update App"]):
        x = 90 + (i % 2) * 300
        y = 252 + (i // 2) * 68
        rounded(d, (x, y, x + 260, y + 42), "#eef7f6", "#b8ded9", 1, 8)
        d.text((x + 18, y + 10), text, fill=BRAND, font=font(17, True))
    rounded(d, (720, 110, 910, 330), PANEL, LINE, 2, 16)
    d.rectangle((744, 142, 887, 164), fill=BRAND)
    d.rectangle((744, 188, 887, 210), fill="#cdd9e2")
    d.rectangle((744, 234, 887, 256), fill="#cdd9e2")
    d.text((746, 356), "Created by", fill=MUTED, font=font(18))
    d.text((746, 384), "abdulrahman sammour", fill=INK, font=font(24, True))
    img.save(BASE / "banner.png")


def screenshot_base(title):
    img = Image.new("RGB", (1200, 675), "#f3f6f8")
    d = ImageDraw.Draw(img)
    draw_topbar(d, 1200)
    d.rectangle((0, 54, 170, 675), fill="#17212b")
    for i, item in enumerate(["Discuss", "Studio Builder", "Sales", "Accounting", "Project", "Settings"]):
        y = 82 + i * 46
        if item == "Studio Builder":
            d.rectangle((0, y - 8, 170, y + 30), fill="#4f91a5")
        d.text((22, y), item, fill="white", font=font(15))
    d.text((198, 82), title, fill=INK, font=font(24, True))
    return img, d


def save_main_screenshot():
    img, d = screenshot_base("Studio Builder - request app")
    d.rectangle((190, 126, 350, 675), fill="#22303a")
    d.text((210, 148), "COMPONENTS", fill="#d8e6ed", font=font(14, True))
    comps = ["Text", "Multiline", "HTML", "Integer", "Decimal", "Selection", "Date", "Many2one", "Image", "File"]
    for i, comp in enumerate(comps):
        x = 210 + (i % 2) * 72
        y = 178 + (i // 2) * 44
        d.rectangle((x, y, x + 62, y + 28), fill="#f5f8fa", outline="#dfe8ee")
        d.text((x + 7, y + 6), comp[:8], fill=INK, font=font(12, True))
    d.rectangle((380, 126, 970, 640), fill="#ffffff", outline=LINE)
    d.text((405, 152), "FORM PREVIEW", fill=MUTED, font=font(14, True))
    fields = ["Customer", "Phone", "Email", "Start Date", "Status", "Notes"]
    for i, field in enumerate(fields):
        y = 200 + i * 64
        d.text((425, y), field, fill=INK, font=font(15, True))
        d.line((425, y + 30, 790, y + 30), fill="#cdd9e2", width=2)
        d.rectangle((425, y + 42, 905, y + 66), outline="#9fc6da")
        d.text((625, y + 47), "Drop after " + field, fill="#8aa6b8", font=font(12))
    d.rectangle((990, 126, 1170, 640), fill="#ffffff", outline=LINE)
    d.text((1012, 152), "PROPERTIES", fill=MUTED, font=font(14, True))
    d.text((1012, 194), "Label", fill=INK, font=font(14))
    d.rectangle((1012, 218, 1150, 250), outline="#c5d2db")
    d.text((1022, 226), "Status", fill=INK, font=font(14))
    d.text((1012, 278), "Selection Options", fill=INK, font=font(14))
    d.rectangle((1012, 304, 1150, 390), outline="#c5d2db")
    d.text((1022, 314), "new:New\napproved:Approved", fill=MUTED, font=font(13))
    rounded(d, (1012, 428, 1150, 464), "#5b94b0", radius=5)
    d.text((1034, 437), "Save Properties", fill="white", font=font(14, True))
    img.save(BASE / "main_screenshot.png")


def save_builder_screenshot():
    img, d = screenshot_base("Create Your App")
    d.rectangle((205, 140, 1120, 610), fill="#ffffff", outline=LINE)
    d.text((240, 178), "Suggested features for your new model", fill=INK, font=font(28, True))
    features = [
        "Contact details", "User assignment", "Date & Calendar", "Pipeline stages",
        "Tags", "Picture", "Notes", "Monetary value", "Company", "Chatter",
    ]
    for i, feat in enumerate(features):
        x = 250 + (i % 2) * 410
        y = 245 + (i // 2) * 58
        d.rectangle((x, y, x + 18, y + 18), fill=BRAND if i not in (3, 7) else "#fff", outline="#b8cbd8")
        d.text((x + 30, y - 2), feat, fill=INK, font=font(17, True))
        d.text((x + 30, y + 23), "Add ready-made fields and views", fill=MUTED, font=font(13))
    rounded(d, (910, 540, 1088, 584), ACCENT, radius=6)
    d.text((942, 552), "Create Your App", fill="white", font=font(17, True))
    img.save(BASE / "screenshot_builder.png")


def save_properties_screenshot():
    img, d = screenshot_base("Field Properties")
    d.rectangle((200, 130, 960, 620), fill="#ffffff", outline=LINE)
    d.text((235, 166), "FORM", fill=MUTED, font=font(14, True))
    d.text((235, 196), "Request Approval", fill=INK, font=font(28, True))
    for i, field in enumerate(["Name", "Responsible", "Date", "Approval Status", "Approval Notes"]):
        y = 255 + i * 66
        fill = "#edf8fb" if field == "Approval Status" else "#ffffff"
        d.rectangle((235, y - 18, 860, y + 42), fill=fill, outline="#9fc6da" if field == "Approval Status" else "#ffffff")
        d.text((260, y), field, fill=INK, font=font(16, True))
        d.line((420, y + 25, 820, y + 25), fill="#cdd9e2", width=2)
    d.rectangle((985, 130, 1165, 620), fill="#ffffff", outline=LINE)
    d.text((1005, 164), "PROPERTIES", fill=MUTED, font=font(14, True))
    for i, label in enumerate(["Label", "Technical Name", "Help", "Options"]):
        y = 205 + i * 78
        d.text((1005, y), label, fill=INK, font=font(14))
        d.rectangle((1005, y + 25, 1145, y + 56), outline="#c5d2db")
    d.text((1016, 230), "Approval Status", fill=INK, font=font(13))
    d.text((1016, 308), "x_approval_status", fill=MUTED, font=font(13))
    d.text((1016, 464), "draft:Draft\napproved:Approved", fill=MUTED, font=font(12))
    rounded(d, (1005, 548, 1145, 584), "#5b94b0", radius=5)
    d.text((1030, 557), "Save Properties", fill="white", font=font(14, True))
    img.save(BASE / "screenshot_properties.png")


if __name__ == "__main__":
    save_icon()
    save_banner()
    save_main_screenshot()
    save_builder_screenshot()
    save_properties_screenshot()
    print("Generated Odoo Apps Store assets in", BASE)
