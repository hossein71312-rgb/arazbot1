import os, io, datetime, zoneinfo
import requests, jdatetime
from hijridate import Gregorian
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display

TOKEN = os.environ.get("RUBIKA_TOKEN", "")
CHAT_ID = os.environ.get("RUBIKA_CHAT_ID", "")
CHANNEL_NAME = os.environ.get("CHANNEL_NAME", "اسم کانال")
CHANNEL_ID = os.environ.get("CHANNEL_ID", "@your_channel")
HIJRI_OFFSET = int(os.environ.get("HIJRI_OFFSET", "0"))  # اگر تاریخ قمری یک روز اختلاف داشت: -1 یا 1
FONT = os.path.join(os.path.dirname(__file__), "Vazirmatn-Bold.ttf")

FA_DAYS = ["دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه", "شنبه", "یکشنبه"]  # Monday=0
FA_MONTHS = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور", "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"]
HJ_MONTHS = ["محرم", "صفر", "ربیع‌الاول", "ربیع‌الثانی", "جمادی‌الاول", "جمادی‌الثانی", "رجب", "شعبان", "رمضان", "شوال", "ذی‌القعده", "ذی‌الحجه"]
EN_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
EN_MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")

def fa(s):
    s = str(s)
    return s[::-1] if False else get_display(arabic_reshaper.reshape(s), base_dir="R")

def font(size):
    return ImageFont.truetype(FONT, size, layout_engine=ImageFont.Layout.BASIC)

def gold_bar(img, box, r=14):
    x0, y0, x1, y1 = box
    grad = Image.new("RGB", (x1 - x0, y1 - y0))
    d = ImageDraw.Draw(grad)
    top, mid, bot = (250, 205, 60), (222, 160, 20), (170, 105, 5)
    h = y1 - y0
    for y in range(h):
        t = y / h
        a, b, u = (top, mid, t * 2) if t < .5 else (mid, bot, (t - .5) * 2)
        d.line([(0, y), (x1 - x0, y)], fill=tuple(int(a[i] + (b[i] - a[i]) * u) for i in range(3)))
    m = Image.new("L", grad.size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, grad.size[0], grad.size[1]], r, fill=255)
    img.paste(grad, (x0, y0), m)

def text_c(d, cx, cy, s, size, fill):
    d.text((cx, cy), s, font=font(size), fill=fill, anchor="mm")

def make_card(now):
    W = H = 1080
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    for y in range(H):
        c = int(232 - 22 * y / H)
        d.line([(0, y), (W, y)], fill=(c - 4, c + 2, c + 8))
    BLACK, GOLD, WHITE = (28, 28, 30), (245, 190, 40), (255, 255, 255)
    L, R = 110, 970
    # سیم‌های آویز
    for x in (230, 850):
        d.line([(x, 0), (x, 170)], fill=(90, 90, 95), width=4)
        d.rounded_rectangle([x - 22, 150, x + 22, 200], 6, fill=(60, 60, 65))
    # بالا
    d.rounded_rectangle([L, 190, R, 420], 36, fill=BLACK)
    gold_bar(img, (590, 225, 940, 295))
    gold_bar(img, (590, 310, 940, 380))
    text_c(d, 765, 260, EN_DAYS[now.weekday()], 44, WHITE)
    text_c(d, 765, 345, fa(FA_DAYS[now.weekday()]), 44, WHITE)
    text_c(d, 340, 260, fa(CHANNEL_NAME), 46, GOLD)
    # میلادی
    y0, y1 = 450, 570
    gold_bar(img, (L, y0, 330, y1)); gold_bar(img, (R - 220, y0, R, y1))
    d.rounded_rectangle([345, y0, R - 235, y1], 22, fill=BLACK)
    text_c(d, 220, 510, str(now.day), 64, WHITE)
    text_c(d, 540, 510, EN_MONTHS[now.month - 1], 58, GOLD)
    text_c(d, R - 110, 510, str(now.year), 60, WHITE)
    # شمسی
    j = jdatetime.date.fromgregorian(date=now.date())
    y0, y1 = 600, 720
    gold_bar(img, (L, y0, 330, y1)); gold_bar(img, (R - 220, y0, R, y1))
    d.rounded_rectangle([345, y0, R - 235, y1], 22, fill=BLACK)
    text_c(d, 220, 660, fa(str(j.year).translate(FA_DIGITS)), 60, WHITE)
    text_c(d, 540, 660, fa(FA_MONTHS[j.month - 1]), 58, GOLD)
    text_c(d, R - 110, 660, fa(str(j.day).translate(FA_DIGITS)), 64, WHITE)
    # پایین: قمری
    d.rounded_rectangle([L, 750, R, 960], 36, fill=BLACK)
    h = Gregorian.fromdate(now.date() + datetime.timedelta(days=HIJRI_OFFSET)).to_hijri()
    hs = f"{h.day} {HJ_MONTHS[h.month - 1]} {h.year}".translate(FA_DIGITS)
    text_c(d, 540, 820, fa(hs), 50, GOLD)
    text_c(d, 540, 900, CHANNEL_ID, 44, WHITE)
    buf = io.BytesIO(); img.save(buf, "PNG")
    return buf.getvalue(), j, hs

def send(png, caption):
    base = f"https://botapi.rubika.ir/v3/{TOKEN}"
    r = requests.post(f"{base}/requestSendFile", json={"type": "Image"}, timeout=30).json()
    up = r["data"]["upload_url"]
    r = requests.post(up, files={"file": ("calendar.png", png, "image/png")}, timeout=60).json()
    file_id = r["data"]["file_id"]
    r = requests.post(f"{base}/sendFile", json={"chat_id": CHAT_ID, "file_id": file_id, "text": caption}, timeout=30)
    print(r.status_code, r.text[:300])
    r.raise_for_status()

if __name__ == "__main__":
    now = datetime.datetime.now(zoneinfo.ZoneInfo("Asia/Tehran"))
    png, j, hs = make_card(now)
    if os.environ.get("TEST_ONLY"):
        open("card.png", "wb").write(png); print("saved card.png"); raise SystemExit
    cap = f"📅 {FA_DAYS[now.weekday()]} {str(j.day).translate(FA_DIGITS)} {FA_MONTHS[j.month - 1]} {str(j.year).translate(FA_DIGITS)}\n🌙 {hs}\n🗓 {now.day} {EN_MONTHS[now.month-1]} {now.year}"
    send(png, cap)
