import asyncio, json, logging, os, sqlite3, uuid
from html import escape as esc
from datetime import datetime, date, time, timedelta
from zoneinfo import ZoneInfo
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, CallbackQuery, BotCommand, InlineKeyboardMarkup, InlineKeyboardButton as B
from google import genai
from google.genai import types

for _k in ("BOT_TOKEN", "GEMINI_API_KEY"):
    if not os.getenv(_k, "").strip():
        raise SystemExit(f"XATO: Railway > Variables bo'limida {_k} kiritilmagan!")
TOKEN = os.environ["BOT_TOKEN"].strip()
TZ = ZoneInfo(os.getenv("TZ_NAME", "Asia/Tashkent"))
MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
DB = os.getenv("DB_PATH", "/app/data/tasks.db" if os.path.isdir("/app") else "data/tasks.db")

bot = Bot(TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()
ai = genai.Client(api_key=os.environ["GEMINI_API_KEY"].strip())

# ---------- DB ----------
os.makedirs(os.path.dirname(DB) or ".", exist_ok=True)
db = sqlite3.connect(DB, check_same_thread=False)
db.row_factory = sqlite3.Row
db.executescript("""
CREATE TABLE IF NOT EXISTS tasks(id INTEGER PRIMARY KEY, title TEXT, d TEXT, t TEXT, remind TEXT,
  repeat TEXT DEFAULT 'none', status TEXT DEFAULT 'pending', snooze TEXT, moved INTEGER DEFAULT 0, created TEXT);
CREATE TABLE IF NOT EXISTS sent(task_id INTEGER, off INTEGER, PRIMARY KEY(task_id, off));
CREATE TABLE IF NOT EXISTS kv(k TEXT PRIMARY KEY, v TEXT);
""")

def kv(k, default=None):
    r = db.execute("SELECT v FROM kv WHERE k=?", (k,)).fetchone()
    return r[0] if r else default

def setkv(k, v):
    db.execute("REPLACE INTO kv VALUES(?,?)", (k, str(v))); db.commit()

def owner(): return int(os.getenv("OWNER_ID") or kv("owner") or 0)

def now(): return datetime.now(TZ)
def today(): return now().date()
def row(tid): return db.execute("SELECT * FROM tasks WHERE id=?", (tid,)).fetchone()

def add_task(t):
    db.execute("INSERT INTO tasks(title,d,t,remind,repeat,created) VALUES(?,?,?,?,?,?)",
               (t["title"], t["date"], t["time"], json.dumps(t["remind"]) if t["remind"] else None,
                t["repeat"], now().isoformat()))
    db.commit()

def update_task(tid, t):
    db.execute("UPDATE tasks SET title=?,d=?,t=?,remind=?,repeat=?,snooze=NULL WHERE id=?",
               (t["title"], t["date"], t["time"], json.dumps(t["remind"]) if t["remind"] else None, t["repeat"], tid))
    db.execute("DELETE FROM sent WHERE task_id=?", (tid,)); db.commit()

def set_date(tid, d):
    db.execute("UPDATE tasks SET d=?, moved=moved+1, snooze=NULL WHERE id=?", (d, tid))
    db.execute("DELETE FROM sent WHERE task_id=?", (tid,)); db.commit()

def tdict(r):
    return {"title": r["title"], "date": r["d"], "time": r["t"],
            "remind": json.loads(r["remind"]) if r["remind"] else None, "repeat": r["repeat"]}

def tasks_on(d):
    return db.execute("SELECT * FROM tasks WHERE d=? AND status IN ('pending','done') ORDER BY t IS NULL, t",
                      (d,)).fetchall()

# ---------- Takrorlanish ----------
def next_date(d, rp):
    d = date.fromisoformat(d) + timedelta(days=7 if rp == "weekly" else 1)
    if rp == "weekdays":
        while d.weekday() > 4: d += timedelta(days=1)
    return d.isoformat()

def spawn(r):
    if r["repeat"] == "none": return
    nd = next_date(r["d"], r["repeat"])
    while nd < today().isoformat(): nd = next_date(nd, r["repeat"])
    db.execute("INSERT INTO tasks(title,d,t,remind,repeat,created) VALUES(?,?,?,?,?,?)",
               (r["title"], nd, r["t"], r["remind"], r["repeat"], now().isoformat()))
    db.commit()

def rollover():
    for r in db.execute("SELECT * FROM tasks WHERE status='pending' AND repeat!='none' AND d<?",
                        (today().isoformat(),)).fetchall():
        db.execute("UPDATE tasks SET status='missed' WHERE id=?", (r["id"],)); spawn(r)
    db.commit()

# ---------- Formatlash ----------
WD = ["Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba", "Yakshanba"]
WDS = ["Du", "Se", "Ch", "Pa", "Ju", "Sh", "Ya"]
REP = {"none": "", "daily": " 🔁har kuni", "weekdays": " 🔁ish kunlari", "weekly": " 🔁har hafta"}

def ddmm(d):
    d = date.fromisoformat(d); return f"{d:%d.%m} {WDS[d.weekday()]}"

def dur(m): return f"{m} daqiqa" if m < 60 else f"{m // 60} soat" + (f" {m % 60} daqiqa" if m % 60 else "")

def fmt(t):
    rm = f" 🔔{','.join(map(str, t['remind']))}d" if t.get("remind") else ""
    return f"{t.get('time') or '—'} {esc(t['title'])}{rm}{REP.get(t.get('repeat') or 'none', '')}"

def card(t): return f"📅 {ddmm(t['date'])} · {fmt(t)}"

def listing(rows, show_date=False):
    out, last = [], None
    for i, r in enumerate(rows, 1):
        if show_date and r["d"] != last:
            last = r["d"]; out.append(f"\n<b>{ddmm(r['d'])}</b>")
        mark = "✅ " if r["status"] == "done" else ""
        out.append(f"{i}. {mark}{fmt(tdict(r))}")
    return "\n".join(out)

def kb(*rows): return InlineKeyboardMarkup(inline_keyboard=[[B(text=a, callback_data=b) for a, b in r] for r in rows])

def list_kb(rows):
    btn = [(str(i), f"op:{r['id']}") for i, r in enumerate(rows, 1)]
    return kb(*[btn[i:i + 6] for i in range(0, len(btn), 6)]) if btn else None

def task_kb(tid):
    return kb([("✅ Bajarildi", f"dn:{tid}"), ("✏️ O'zgartirish", f"ed:{tid}")],
              [("➡️ Ertaga", f"mv:{tid}"), ("🗑 O'chirish", f"dl:{tid}")])

def rem_kb(tid):
    return kb([("✅ Bajarildi", f"dn:{tid}"), ("⏰ 15 daq", f"sz:{tid}:15"), ("⏰ 1 soat", f"sz:{tid}:60")],
              [("➡️ Ertaga", f"mv:{tid}"), ("✏️ O'zgartirish", f"ed:{tid}")])

# ---------- AI (Gemini) ----------
SCHEMA = ('{"transcript":"ovozli bo\'lsa matni","tasks":[{"title":"qisqa aniq nom","date":"YYYY-MM-DD",'
          '"time":"HH:MM yoki null","remind":[daqiqalar] yoki null,"repeat":"none|daily|weekdays|weekly"}]}')

def ctx():
    n = now(); return f"Hozir: {n:%Y-%m-%d %H:%M}, {WD[n.weekday()]} (Toshkent vaqti)."

def create_prompt(text):
    src = "Ovozli xabarni o'zbekcha matnga o'gir va undan" if text is None else f'Foydalanuvchi matni: """{text}"""\nShu matndan'
    return f"""{ctx()}
{src} vazifalarni ajrat. Qoidalar:
- Bir xabarda bir nechta vazifa bo'lishi mumkin.
- Sana aytilmasa: hozir 18:00 dan keyin bo'lsa ertangi sana, aks holda bugungi sana.
- "ertaga", "indinga", "dushanba" kabilarni aniq sanaga aylantir.
- Vaqt: aniq aytilsa yoz; "ertalab"=09:00, "tushlikda"=13:00, "kechqurun"=19:00; umuman aytilmasa null.
- "30 daqiqa oldin eslat" -> remind=[30]; "1 soat va 10 daqiqa oldin" -> [60,10]; aytilmasa null.
- "har kuni"->daily, "ish kunlari"->weekdays, "har hafta"/"har dushanba"->weekly (date = eng yaqin shu kun).
- Vazifa bo'lmasa tasks=[].
Faqat JSON qaytar: {SCHEMA}"""

def edit_prompt(task, text):
    src = "Ovozli xabarda" if text is None else f'Foydalanuvchi: """{text}"""\nShu matnda'
    return f"""{ctx()}
Mavjud vazifa: {json.dumps(task, ensure_ascii=False)}
{src} shu vazifaga o'zgartirish so'ralgan. Faqat so'ralgan maydonlarni o'zgartir, qolganini aynan saqla.
Faqat JSON qaytar: {{"title":"","date":"YYYY-MM-DD","time":"HH:MM yoki null","remind":[...] yoki null,"repeat":"none|daily|weekdays|weekly"}}"""

async def ask(prompt, audio=None, mime="audio/ogg"):
    parts = [types.Part.from_bytes(data=audio, mime_type=mime)] if audio else []
    r = await ai.aio.models.generate_content(
        model=MODEL, contents=parts + [prompt],
        config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0))
    return json.loads(r.text)

def parse_hm(s):
    h, m = s.strip().split(":"); return time(int(h), int(m)).strftime("%H:%M")

def clean(t):
    rm = t.get("remind")
    rm = sorted({int(x) for x in rm if 0 <= int(x) <= 1440}, reverse=True) if rm else None
    rp = t.get("repeat") or "none"
    return {"title": str(t["title"]).strip()[:200], "date": date.fromisoformat(t["date"]).isoformat(),
            "time": parse_hm(t["time"]) if t.get("time") else None, "remind": rm or None,
            "repeat": rp if rp in REP else "none"}

# ---------- Kiruvchi xabarlar ----------
state = {"edit": None}
DRAFT = {}

# Botga birinchi /start yozgan odam egasi bo'ladi, boshqalar e'tiborga olinmaydi
dp.message.filter(lambda m: m.from_user.id == owner() or (not owner() and (m.text or "").startswith("/start")))
dp.callback_query.filter(lambda c: c.from_user.id == owner())

HELP = """👋 Vazifalarni <b>matn yoki ovoz</b> bilan yuboring, masalan:
<i>«Ertaga 10 da mijoz bilan uchrashuv, 30 daqiqa oldin eslat. Har kuni 9 da reels joylash»</i>

/bugun · /ertaga · /hafta — ro'yxatlar
/hisobot — haftalik natija
/sozlamalar — eslatma vaqtlari
/bekor — tahrirlashni bekor qilish"""

@dp.message(Command("start", "help"))
async def start(m: Message):
    if not owner():
        setkv("owner", m.from_user.id)
        await m.answer("🔐 Bot sizga biriktirildi. Endi boshqalar undan foydalana olmaydi.")
    await m.answer(HELP)

@dp.message(Command("bekor"))
async def cancel(m: Message):
    state["edit"] = None; await m.answer("Bekor qilindi.")

@dp.message(Command("bugun", "ertaga"))
async def day_list(m: Message, command: CommandObject):
    d = today() + timedelta(days=command.command == "ertaga")
    rows = tasks_on(d.isoformat())
    await m.answer(f"📋 <b>{ddmm(d.isoformat())}</b>\n" + (listing(rows) or "Vazifa yo'q."), reply_markup=list_kb(rows))

@dp.message(Command("hafta"))
async def week_list(m: Message):
    rows = db.execute("SELECT * FROM tasks WHERE status='pending' AND d BETWEEN ? AND ? ORDER BY d, t IS NULL, t",
                      (today().isoformat(), (today() + timedelta(days=6)).isoformat())).fetchall()
    await m.answer("📋 <b>7 kunlik reja</b>" + (listing(rows, True) or "\nVazifa yo'q."), reply_markup=list_kb(rows))

@dp.message(Command("hisobot"))
async def rep_cmd(m: Message): await m.answer(report())

@dp.message(Command("sozlamalar"))
async def settings(m: Message):
    await m.answer(f"⚙️ Ertalabki xulosa: <b>{kv('morning', '08:00')}</b>\n"
                   f"Kechki reja eslatmasi: <b>{kv('evening', '21:00')}</b>\n"
                   f"Standart eslatma: <b>{kv('lead', '15')} daqiqa</b> oldin\n\n"
                   "O'zgartirish: /ertalab 07:30 · /kechqurun 21:30 · /oldin 20")

@dp.message(Command("ertalab", "kechqurun", "oldin"))
async def set_cmd(m: Message, command: CommandObject):
    try:
        a = command.args or ""
        if command.command == "oldin":
            v = int(a); assert 0 <= v <= 1440; setkv("lead", v)
        else:
            setkv("morning" if command.command == "ertalab" else "evening", parse_hm(a))
        await m.answer("✅ Saqlandi")
    except Exception:
        await m.answer("Format: /ertalab 07:30 · /kechqurun 21:00 · /oldin 15")

@dp.message(F.voice | F.audio)
async def on_voice(m: Message):
    v = m.voice or m.audio
    buf = await bot.download(v.file_id)
    await process(m, audio=buf.read(), mime=v.mime_type or "audio/ogg")

@dp.message(F.text & ~F.text.startswith("/"))
async def on_text(m: Message): await process(m, text=m.text)

async def process(m: Message, text=None, audio=None, mime="audio/ogg"):
    w = await m.answer("⏳ Tahlil qilinmoqda...")
    tid, state["edit"] = state["edit"], None
    try:
        if tid and (r := row(tid)):
            new = clean(await ask(edit_prompt(tdict(r), text), audio, mime))
            update_task(tid, new)
            return await w.edit_text("✏️ Yangilandi:\n" + card(new), reply_markup=task_kb(tid))
        res = await ask(create_prompt(text), audio, mime)
        tasks = [clean(t) for t in res.get("tasks", [])]
    except Exception:
        logging.exception("AI")
        state["edit"] = tid
        return await w.edit_text("❗ Tushunmadim yoki AI xatosi. Qaytadan yuboring.")
    heard = f"🎙 <i>{esc(res.get('transcript') or '')}</i>\n\n" if audio and res.get("transcript") else ""
    if not tasks:
        return await w.edit_text(heard + "🤔 Vazifa topilmadi.")
    k = uuid.uuid4().hex[:8]; DRAFT[k] = tasks
    await w.edit_text(heard + "Saqlaymanmi?\n\n" + "\n".join(f"{i}. {card(t)}" for i, t in enumerate(tasks, 1)),
                      reply_markup=kb([("✅ Saqlash", f"sv:{k}"), ("❌ Bekor", f"cx:{k}")]))

# ---------- Tugmalar ----------
@dp.callback_query()
async def cb(c: CallbackQuery):
    act, _, arg = c.data.partition(":")

    async def mark(s):
        await c.message.edit_text(c.message.html_text + "\n\n" + s)

    if act == "sv":
        ts = DRAFT.pop(arg, None)
        if not ts: return await c.answer("Eskirgan, qayta yuboring")
        for t in ts: add_task(t)
        await mark(f"✅ Saqlandi ({len(ts)} ta)")
    elif act == "cx":
        DRAFT.pop(arg, None); await c.message.edit_text("❌ Bekor qilindi")
    else:
        tid = int(arg.split(":")[0]); r = row(tid)
        if not r: return await c.answer("Topilmadi")
        if act == "op":
            await c.message.answer(card(tdict(r)), reply_markup=task_kb(tid))
        elif r["status"] != "pending":
            return await c.answer("Bu vazifa allaqachon yopilgan")
        elif act == "dn":
            db.execute("UPDATE tasks SET status='done' WHERE id=?", (tid,)); db.commit(); spawn(r)
            await mark("✅ Bajarildi")
        elif act == "sz":
            mins = int(arg.split(":")[1])
            db.execute("UPDATE tasks SET snooze=? WHERE id=?", ((now() + timedelta(minutes=mins)).isoformat(), tid)); db.commit()
            await mark(f"⏰ {dur(mins)}dan keyin yana eslataman")
        elif act == "mv":
            nd = (max(date.fromisoformat(r["d"]), today()) + timedelta(days=1)).isoformat()
            set_date(tid, nd); await mark(f"➡️ {ddmm(nd)} ga ko'chirildi")
        elif act == "td":
            set_date(tid, today().isoformat()); await mark("➡️ Bugunga ko'chirildi")
        elif act == "dl":
            db.execute("UPDATE tasks SET status='cancelled' WHERE id=?", (tid,)); db.commit()
            await mark("🗑 O'chirildi" + (" (takrorlanish to'xtadi)" if r["repeat"] != "none" else ""))
        elif act == "ed":
            state["edit"] = tid
            await c.message.answer(f"✏️ <b>{esc(r['title'])}</b>\nNimani o'zgartiramiz? Matn yoki ovoz yuboring.\n"
                                   "<i>Masalan: «vaqtini 15:00 ga, 1 soat oldin eslat»</i>\nBekor: /bekor")
    await c.answer()

# ---------- Rejalashtiruvchi ----------
def report():
    s = (today() - timedelta(days=6)).isoformat()
    c = dict(db.execute("SELECT status, COUNT(*) FROM tasks WHERE d BETWEEN ? AND ? AND status!='cancelled' GROUP BY status",
                        (s, today().isoformat())).fetchall())
    tot, dn = sum(c.values()), c.get("done", 0)
    if not tot: return "📊 Oxirgi 7 kunda vazifa bo'lmadi."
    top = db.execute("SELECT title, moved FROM tasks WHERE moved>0 AND d>=? ORDER BY moved DESC LIMIT 3", (s,)).fetchall()
    txt = f"📊 <b>Haftalik hisobot</b>\nJami: {tot} · Bajarildi: {dn} · Natija: <b>{dn * 100 // tot}%</b>"
    if top: txt += "\n\nEng ko'p ko'chirilganlar:\n" + "\n".join(f"• {esc(r['title'])} ({r['moved']} marta)" for r in top)
    return txt

async def morning():
    rows = tasks_on(today().isoformat())
    await bot.send_message(owner(), "☀️ Xayrli tong! " + ("Bugungi reja:\n" + listing(rows) if rows else "Bugunga vazifa yo'q."),
                           reply_markup=list_kb(rows))
    for r in db.execute("SELECT * FROM tasks WHERE status='pending' AND d<? ORDER BY d", (today().isoformat(),)).fetchall():
        await bot.send_message(owner(), f"⚠️ Bajarilmagan ({ddmm(r['d'])}): <b>{esc(r['title'])}</b>",
                               reply_markup=kb([("➡️ Bugunga", f"td:{r['id']}"), ("✅ Bajarildi", f"dn:{r['id']}"),
                                                ("🗑", f"dl:{r['id']}")]))

async def evening():
    rows = tasks_on((today() + timedelta(days=1)).isoformat())
    txt = "🌙 Ertangi rejangizni yozing yoki ovozli yuboring." + ("\n\nHozircha:\n" + listing(rows) if rows else "")
    if today().weekday() == 6: txt += "\n\n" + report()
    await bot.send_message(owner(), txt, reply_markup=list_kb(rows))

async def send_rem(r, off):
    head = "⏰ <b>Vaqti keldi!</b>" if off == 0 else f"🔔 {dur(off)}dan keyin:"
    await bot.send_message(owner(), f"{head}\n<b>{esc(r['title'])}</b> — {r['t'] or ''}", reply_markup=rem_kb(r["id"]))

async def tick():
    if not owner(): return
    n = now(); td = n.date().isoformat(); hm = n.strftime("%H:%M")
    if kv("roll") != td: rollover(); setkv("roll", td)
    if hm >= kv("morning", "08:00") and kv("m_sent") != td: setkv("m_sent", td); await morning()
    if hm >= kv("evening", "21:00") and kv("e_sent") != td: setkv("e_sent", td); await evening()
    lead = int(kv("lead", "15"))
    rows = db.execute("SELECT * FROM tasks WHERE status='pending' AND t IS NOT NULL AND d BETWEEN ? AND ?",
                      (td, (n.date() + timedelta(days=1)).isoformat())).fetchall()
    for r in rows:
        due = datetime.fromisoformat(f"{r['d']}T{r['t']}").replace(tzinfo=TZ)
        for off in sorted(set(json.loads(r["remind"]) if r["remind"] else [lead]) | {0}, reverse=True):
            at = due - timedelta(minutes=off)
            if at <= n < at + timedelta(minutes=30) and not db.execute(
                    "SELECT 1 FROM sent WHERE task_id=? AND off=?", (r["id"], off)).fetchone():
                db.execute("INSERT INTO sent VALUES(?,?)", (r["id"], off)); db.commit()
                await send_rem(r, off)
    for r in db.execute("SELECT * FROM tasks WHERE status='pending' AND snooze IS NOT NULL AND snooze<=?",
                        (n.isoformat(),)).fetchall():
        db.execute("UPDATE tasks SET snooze=NULL WHERE id=?", (r["id"],)); db.commit()
        await send_rem(r, 0)

async def ticker():
    while True:
        try: await tick()
        except Exception: logging.exception("tick")
        await asyncio.sleep(30)

async def main():
    logging.basicConfig(level=logging.INFO)
    await bot.set_my_commands([BotCommand(command=c, description=d) for c, d in [
        ("bugun", "Bugungi vazifalar"), ("ertaga", "Ertangi vazifalar"), ("hafta", "7 kunlik reja"),
        ("hisobot", "Haftalik hisobot"), ("sozlamalar", "Sozlamalar"), ("bekor", "Tahrirni bekor qilish")]])
    bg = asyncio.create_task(ticker())  # noqa
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
