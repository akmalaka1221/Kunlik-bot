# Kunlik vazifalar boti — o'rnatish (dasturlashsiz)

Sizga faqat **2 ta kalit** kerak. Kodga tegmaysiz.

## 1-qadam. Kalitlarni oling
1. **BOT_TOKEN** — Telegramda @BotFather → `/newbot` → nom bering → bergan uzun kodni nusxalang.
2. **GEMINI_API_KEY** — aistudio.google.com → Google akkaunt bilan kiring → "Get API key" → "Create API key" → nusxalang.

## 2-qadam. Fayllarni GitHub'ga yuklang
1. github.com → yuqorida **+** → **New repository** → nom: `kunlik-bot` → **Private** → **Create repository**.
2. Ochilgan sahifada **"uploading an existing file"** havolasini bosing.
3. Arxivdan chiqargan barcha fayllarni (bot.py, Dockerfile, requirements.txt, README.md) sudrab tashlang → **Commit changes**.

## 3-qadam. Railway
1. railway.app → **New Project** → **Deploy from GitHub repo** → `kunlik-bot` ni tanlang.
2. Loyiha ichida servisni bosing → **Variables** → **New Variable**:
   - `BOT_TOKEN` = 1-qadamdagi Telegram kodi
   - `GEMINI_API_KEY` = 1-qadamdagi Gemini kaliti
3. **Ma'lumotlar o'chib ketmasligi uchun (majburiy):** servisni o'ng tugma bilan bosing (yoki Ctrl+K → "volume") → **Add Volume** → Mount path: `/app/data` → saqlang.
4. Railway o'zi qayta ishga tushiradi. **Deployments → View logs** da qizil XATO bo'lmasa, tayyor.

## 4-qadam. Botni o'zingizga biriktiring
Telegramda botingizni oching → **/start**. Birinchi /start yozgan odam egasi bo'ladi, boshqalarga bot javob bermaydi. Shuning uchun buni darhol qiling.

## Xatolar
- Logda `XATO: ... BOT_TOKEN kiritilmagan` → Variables'ni tekshiring.
- Bot "AI xatosi" deyapti → Gemini kaliti noto'g'ri yoki limit tugagan.

## Foydalanish
- Matn yoki ovoz: «Ertaga 10 da mijoz bilan uchrashuv, 30 daqiqa oldin eslat. Har kuni 9 da reels joylash» → ✅ Saqlash
- /bugun /ertaga /hafta → raqamni bosing → ✅ ✏️ ➡️ 🗑
- ✏️ bosib «vaqtini 15:00 ga o'zgartir» deb yozing yoki ayting
- Sozlamalar: /ertalab 08:00 · /kechqurun 21:00 · /oldin 15
- Haftalik hisobot: yakshanba kechqurun avtomatik yoki /hisobot
