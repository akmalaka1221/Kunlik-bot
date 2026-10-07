# Kunlik vazifalar boti — o'rnatish (dasturlashsiz)

Sizga **3 ta kalit** kerak. Kodga tegmaysiz.

## 1-qadam. Kalitlarni oling
1. **BOT_TOKEN** — Telegramda @BotFather → `/newbot` → bergan kodni nusxalang.
2. **ANTHROPIC_API_KEY** — console.anthropic.com → API Keys → Create Key. (Matnni tushunish uchun, pullik lekin juda arzon.)
3. **GROQ_API_KEY** — console.groq.com → Google bilan kiring → API Keys → Create API Key. (Ovozni matnga o'girish uchun, bepul.)

## 2-qadam. Fayllarni GitHub'ga yuklang
1. github.com → yuqorida **+** → **New repository** → nom: `kunlik-bot` → **Private** → **Create repository**.
2. Ochilgan sahifada **"uploading an existing file"** havolasini bosing.
3. Arxivdan chiqargan barcha fayllarni (bot.py, Dockerfile, requirements.txt, README.md) sudrab tashlang → **Commit changes**.

## 3-qadam. Railway
1. railway.app → **New Project** → **Deploy from GitHub repo** → `kunlik-bot` ni tanlang.
2. Loyiha ichida servisni bosing → **Variables** → **New Variable**:
   - `BOT_TOKEN` = 1-qadamdagi Telegram kodi
   - `ANTHROPIC_API_KEY` = Claude kaliti
   - `GROQ_API_KEY` = Groq kaliti
   - (Eski `GEMINI_API_KEY` bo'lsa, o'chirib tashlang yoki qoldiring — Claude kaliti bo'lsa, u ishlatilmaydi)
3. **Ma'lumotlar o'chib ketmasligi uchun (majburiy):** servisni o'ng tugma bilan bosing (yoki Ctrl+K → "volume") → **Add Volume** → Mount path: `/app/data` → saqlang.
4. Railway o'zi qayta ishga tushiradi. **Deployments → View logs** da qizil XATO bo'lmasa, tayyor.

## 4-qadam. Botni o'zingizga biriktiring
Telegramda botingizni oching → **/start**. Birinchi /start yozgan odam egasi bo'ladi, boshqalarga bot javob bermaydi. Shuning uchun buni darhol qiling.

## Xatolar
- Logda `XATO: ... BOT_TOKEN kiritilmagan` → Variables'ni tekshiring.
- Bot "Xatolik" deb pastida kulrang matn ko'rsatsa — o'sha matnni skrinshot qilib yuboring.

## Foydalanish (hammasi tugmalar bilan)
- Vazifa qo'shish: shunchaki yozing yoki 🎤 ovozli yuboring → **✅ Saqlash**
- Pastdagi tugmalar: 📋 Bugun · 📅 Ertaga · 🗓 Hafta · 📊 Hisobot · ⚙️ Sozlamalar · ❓ Yordam
- Ro'yxatda raqamni bosing → ✅ Bajarildi · ✏️ O'zgartirish · ➡️ Ertaga · 🗑 O'chirish
- ⚙️ Sozlamalar → ertalabki/kechki xabar vaqti va eslatma vaqtini tugma bilan tanlaysiz
