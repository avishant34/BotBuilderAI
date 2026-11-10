# 🤖 BotBuilderAI

**Kisi bhi idea se production-ready Telegram bot banane wala AI-powered generator.**

Pure Telegram bot. **Admin Panel**, **Step-by-step complex generation**, **Redis FSM (optional)**, aur **12+ templates** ke saath.

---

## Production-grade v3

- Pydantic schema validation for LLM outputs
- AST syntax check + dangerous-pattern scanner on every generated package
- Auto-repair pass when validation fails
- JSON repair retry on malformed LLM responses
- Global error middleware (bot never dies on handler crash)
- Startup config validation (fail-fast)
- In-process metrics (admin panel → Metrics)
- Unit tests under `tests/`

## ✨ Features (Updated)

| Feature | Description |
|---------|-------------|
| **Any Idea → Bot** | Text adventure, Quiz, RPG, Weather, Habit, Shop, Study helper... |
| **Self-Correction** | Structured gen → LLM Self-Review → Static safety |
| **Step-by-Step** | Complex games automatically multi-step generation + confirm |
| **Clarifying Questions** | Vague ideas pe smart questions |
| **Iterative Improve** | User feedback se fix |
| **ZIP + GitHub + Deploy** | One-click download / push / instructions |
| **Optional Webhook** | Production webhook (aiohttp, no web UI) |
| **Redis FSM** | Production scale state storage |
| **Admin Panel** | Stats, recent users, block/unblock |
| **12 Templates** | Adventure, Quiz, RPG, Shop, Study, RPS, Reminder... |

---

## 🚀 Quick Start (Polling – Local)

```bash
cd BotBuilderAI
cp .env.example .env
# Edit BOT_TOKEN + LLM_API_KEY

python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

---

## 🐳 Docker (recommended)

```bash
cp .env.example .env
# BOT_TOKEN + LLM_API_KEY set karo
docker compose up --build -d
```

Optional Redis FSM:
```bash
# .env → USE_REDIS=true + REDIS_URL=redis://redis:6379/0
docker compose --profile redis up --build -d
```

Optional Webhook (production, still pure bot – no web UI):
```env
USE_WEBHOOK=true
WEBHOOK_HOST=https://your-domain.com
WEBHOOK_PATH=/webhook
WEBHOOK_SECRET=long-random-secret
```

---

## 🛡 Admin Panel

`ADMIN_IDS` mein apna Telegram ID daalo. Phir:
- `/admin` ya menu se **Admin Panel**
- Stats, recent users, block / unblock

Blocked users generate nahi kar sakte.

---

## 🧩 Step-by-Step Generation

Complex games (RPG, long adventure, multi-state) detect hone pe:

1. Bot plan dikhata hai (5–6 steps)
2. Har step pe "Next Step" confirm
3. Last step pe self-review + safety
4. Final ZIP ready

Quality aur accuracy bahut better rehti hai.

---

## 📚 Templates

- 🎮 Text Adventure
- ❓ Quiz / Trivia
- 💬 AI Chatbot
- 🌤️ Weather
- ✅ Habit Tracker
- 🛡️ Group Moderation
- 🧮 Calculator / Converter
- 📅 Reminder
- 🎲 Rock-Paper-Scissors
- 📚 Study Helper
- 🛒 Simple Shop / Leads
- 🎯 RPG Mini

---

## 📂 Structure

```
main.py                 # Polling / Webhook switch
bot/handlers/
  start.py
  generation.py         # Idea + step-by-step + templates
  admin.py              # Stats + block
core/
  code_generator.py     # Multi-pass + step pipeline
  llm.py
  packager.py
database/
docker-compose.yml      # bot + redis
```

---

## Environment Variables

| Var | Default | Notes |
|-----|---------|-------|
| `BOT_TOKEN` | required | |
| `LLM_API_KEY` | required | |
| `USE_WEBHOOK` | false | true for production |
| `USE_REDIS` | false | true for production FSM |
| `REDIS_URL` | redis://localhost:6379/0 | |
| `ADMIN_IDS` | | comma-separated Telegram IDs |
| `MAX_BOTS_PER_DAY` | 10 | per user |

---

## License

MIT
# BotBuilderAI
