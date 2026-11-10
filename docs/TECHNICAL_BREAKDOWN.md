# Technical Breakdown v2

## Modes

| Mode | When | How |
|------|------|-----|
| Polling | `USE_WEBHOOK=false` (default) | `python main.py` |
| Webhook | `USE_WEBHOOK=true` | FastAPI + uvicorn, `POST /webhook`, `GET /health` |

## FSM Storage

- `USE_REDIS=false` → `MemoryStorage` (dev)
- `USE_REDIS=true` → `RedisStorage` (production, survives restarts)

## Step-by-Step Pipeline

1. `understand_idea` → if complex → return `needs_step_by_step=True` + `generation_plan`
2. User confirms each step via inline button
3. `run_step_pipeline(step_index)` generates/merges files
4. Last step → self-review + static safety → finalize

## Admin

- `ADMIN_IDS` env list
- Commands: `/admin`, stats, recent users, block/unblock by telegram_id
- Blocked users cannot generate

## Health

```
GET /health
→ {"status":"ok","mode":"webhook","environment":"production","redis":true}
```

## Security

- Webhook secret token header check
- Static patterns: eval/exec/shell/hardcoded token blocked
- Rate limit per user (MAX_BOTS_PER_DAY)
