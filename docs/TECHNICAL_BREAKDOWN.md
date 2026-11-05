# Technical Breakdown – BotBuilderAI

## Modes

| Mode | When | How |
|------|------|-----|
| Polling | `USE_WEBHOOK=false` (default) | `python main.py` |
| Webhook | `USE_WEBHOOK=true` | aiohttp minimal server, `POST /webhook`, `GET /health` |

## FSM Storage

- `USE_REDIS=false` → `MemoryStorage` (dev)
- `USE_REDIS=true` → `RedisStorage` (production)

## Step-by-Step Pipeline

1. `understand_idea` → if complex → `needs_step_by_step=True` + plan
2. User confirms each step
3. `run_step_pipeline` merges files
4. Last step → self-review + AST/safety validate → finalize

## Validation gates

- Pydantic schemas (`core/schemas.py`)
- Required files check
- AST syntax check
- Dangerous pattern scanner
- Auto-repair pass on failure

## Admin

- `ADMIN_IDS` env list
- `/admin` — stats, metrics, block/unblock

## Health (webhook mode)

```
GET /health → {"status":"ok","bot":"...","metrics":{...}}
```
