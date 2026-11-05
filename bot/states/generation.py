from aiogram.fsm.state import State, StatesGroup


class GenerationStates(StatesGroup):
    waiting_idea = State()
    waiting_clarification = State()
    waiting_feedback = State()
    waiting_bot_name = State()
    reviewing = State()
    # Step-by-step complex generation
    step_confirm = State()
    step_running = State()


class AdminStates(StatesGroup):
    waiting_block_id = State()
    waiting_unblock_id = State()
