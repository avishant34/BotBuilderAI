"""Pydantic schemas for strict LLM output validation."""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class ArchitectureSpec(BaseModel):
    use_fsm: bool = False
    states: List[str] = Field(default_factory=list)
    needs_db: bool = False
    needs_inline_keyboards: bool = True
    needs_score_system: bool = False
    needs_inventory: bool = False
    multiplayer: bool = False


class Requirements(BaseModel):
    bot_name: str = Field(min_length=2, max_length=64)
    display_name: str = Field(min_length=2, max_length=128)
    category: Literal[
        "game", "utility", "ai_chat", "moderation", "business", "reminder", "other"
    ] = "other"
    description: str = ""
    language: Literal["hi", "en", "mixed"] = "mixed"
    is_complex: bool = False
    needs_clarification: bool = False
    clarifying_questions: List[str] = Field(default_factory=list)
    features: List[str] = Field(default_factory=list)
    architecture: ArchitectureSpec = Field(default_factory=ArchitectureSpec)
    key_handlers: List[str] = Field(default_factory=list)
    estimated_complexity: Literal["simple", "medium", "complex"] = "simple"
    generation_plan: List[str] = Field(default_factory=list)

    @field_validator("bot_name")
    @classmethod
    def snake_case_name(cls, v: str) -> str:
        cleaned = "".join(c if c.isalnum() or c == "_" else "_" for c in v.lower())
        cleaned = cleaned.strip("_") or "telegram_bot"
        return cleaned[:64]


class ReviewResult(BaseModel):
    is_safe: bool = True
    has_critical_bugs: bool = False
    bugs_found: List[str] = Field(default_factory=list)
    security_issues: List[str] = Field(default_factory=list)
    improvements: List[str] = Field(default_factory=list)
    fixed_files: Dict[str, str] = Field(default_factory=dict)
    overall_quality: Literal["excellent", "good", "needs_work", "poor"] = "good"
    ready_to_deploy: bool = True


class GeneratedPackage(BaseModel):
    files: Dict[str, str] = Field(default_factory=dict)
    entry_point: str = "main.py"
    notes: str = ""
    review: Optional[ReviewResult] = None

    @field_validator("files")
    @classmethod
    def must_have_main(cls, v: Dict[str, str]) -> Dict[str, str]:
        if not v:
            raise ValueError("files dict is empty")
        return {k.replace("\\", "/").lstrip("./"): val for k, val in v.items()}


REQUIRED_FILES = ("main.py", "requirements.txt", ".env.example", "README.md")
RECOMMENDED_FILES = ("config.py", "Dockerfile")
