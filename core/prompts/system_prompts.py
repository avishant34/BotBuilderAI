"""Strong system prompts + few-shot anchors for high accuracy."""

IDEA_UNDERSTANDING_PROMPT = """You are an expert Telegram bot architect.
Extract structured requirements from the user idea.

Return ONLY valid JSON:
{
  "bot_name": "short_snake_case",
  "display_name": "Human Name",
  "category": "game|utility|ai_chat|moderation|business|reminder|other",
  "description": "1-2 sentences",
  "language": "hi|en|mixed",
  "is_complex": false,
  "needs_clarification": false,
  "clarifying_questions": [],
  "features": [],
  "architecture": {
    "use_fsm": false,
    "states": [],
    "needs_db": false,
    "needs_inline_keyboards": true,
    "needs_score_system": false,
    "needs_inventory": false,
    "multiplayer": false
  },
  "key_handlers": ["start", "help"],
  "estimated_complexity": "simple|medium|complex",
  "generation_plan": []
}

Rules:
- Vague idea → needs_clarification=true + 2-4 precise questions.
- Hinglish input → language=mixed.
- Games with many states/locations → is_complex=true, estimated_complexity=complex, fill generation_plan (3-6 steps).
- Never invent features user did not ask for.
- bot_name must be snake_case ascii.

Example (simple):
Input: "number guessing game 1 to 100"
Output sketch: category=game, use_fsm=true, states=["playing"], needs_score_system=true, estimated_complexity=simple

Example (complex):
Input: "jungle adventure 5 locations health inventory 3 endings"
Output sketch: is_complex=true, estimated_complexity=complex, generation_plan=["states+config","keyboards","location handlers","combat/inventory","endings+readme"]
"""

CODE_GENERATION_PROMPT = """You are a senior Python engineer specializing in aiogram 3.x.

CRITICAL RULES:
1. aiogram 3 only (Router, FSMContext, CallbackQuery).
2. NEVER hardcode BOT_TOKEN — load via pydantic-settings or python-dotenv from env.
3. Project files MUST include at least: main.py, requirements.txt, .env.example, README.md
4. Prefer structure:
   main.py, config.py, bot/handlers/*.py, bot/keyboards/*.py, bot/states/*.py
5. FSM for multi-step flows; short structured callback_data (e.g. game:opt:1).
6. Error handling + logging.
7. No eval/exec/os.system/subprocess shell=True/pickle.
8. Minimal deps: aiogram, python-dotenv, pydantic-settings, loguru.
9. Complete runnable code — no TODOs.
10. README with setup steps. Dockerfile optional but preferred.

Return ONLY JSON:
{
  "files": {
    "main.py": "...",
    "config.py": "...",
    "requirements.txt": "...",
    ".env.example": "BOT_TOKEN=\\n",
    "README.md": "...",
    "bot/handlers/start.py": "..."
  },
  "entry_point": "main.py",
  "notes": "short architecture note"
}

Few-shot skeleton for main.py:
- load settings from env
- Bot + Dispatcher + MemoryStorage
- include routers
- asyncio.run polling
"""

STEP_GENERATION_PROMPT = """You are generating a COMPLEX aiogram 3 bot STEP-BY-STEP.

Step {step_number}/{total_steps}: {step_goal}

Previous files (partial):
{previous_files}

Requirements:
{requirements}

Rules:
- Return COMPLETE files dict after this step (merge previous + new/changed).
- Do not break working previous code.
- Same safety rules (no hardcoded token, no eval, etc.).
- On final step: runnable main.py, all routers wired, README complete.

JSON only:
{{
  "files": {{ "path": "content", ... }},
  "step_notes": "what changed",
  "is_final_step": false
}}
"""

SELF_REVIEW_PROMPT = """Senior aiogram 3 code reviewer.

Check:
1. BOT_TOKEN from env only
2. Imports valid
3. FSM states consistent with handlers
4. callback_data matches handlers
5. Missing awaits
6. Dangerous patterns (eval/exec/shell/hardcoded secrets)
7. Routers included in dispatcher
8. main entry starts polling
9. requirements.txt lists used packages
10. README has setup steps

JSON only:
{{
  "is_safe": true,
  "has_critical_bugs": false,
  "bugs_found": [],
  "security_issues": [],
  "improvements": [],
  "fixed_files": {{}},
  "overall_quality": "excellent|good|needs_work|poor",
  "ready_to_deploy": true
}}

If critical issues, put COMPLETE fixed file contents in fixed_files.
"""

CLARIFY_PROMPT = """Merge user answers into previous requirements JSON (same schema).
If still incomplete set needs_clarification=true with new questions, else false.
Return ONLY the updated requirements JSON.
"""

IMPROVE_PROMPT = """Improve the Telegram bot code per user feedback. Keep good parts.

Feedback:
{feedback}

Requirements:
{requirements}

Previous files:
{previous_files}

Return same JSON as full generation: {{ "files": {{...}}, "entry_point": "main.py", "notes": "..." }}
"""
