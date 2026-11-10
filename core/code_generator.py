"""
Production multi-pass generation pipeline.

Flow:
1. Understand idea → Pydantic Requirements
2. Clarify if needed
3. Complex → step-by-step | Simple → one-shot
4. Validate schema + structure + AST syntax + safety
5. Self-review + re-validate
6. Return only if safe enough (or flagged)
"""
from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger
from pydantic import ValidationError as PydanticValidationError

from core.exceptions import SafetyError, ValidationError
from core.llm import llm_client
from core.metrics import metrics
from core.prompts.system_prompts import (
    CLARIFY_PROMPT,
    CODE_GENERATION_PROMPT,
    IDEA_UNDERSTANDING_PROMPT,
    IMPROVE_PROMPT,
    SELF_REVIEW_PROMPT,
    STEP_GENERATION_PROMPT,
)
from core.schemas import GeneratedPackage, Requirements, ReviewResult
from core.validators import validate_package


class CodeGenerator:
    def __init__(self) -> None:
        self.llm = llm_client

    def _parse_requirements(self, raw: Dict[str, Any]) -> Requirements:
        try:
            return Requirements.model_validate(raw)
        except PydanticValidationError as e:
            logger.warning(f"Requirements validation soft-fail: {e}")
            # best-effort defaults
            raw.setdefault("bot_name", "telegram_bot")
            raw.setdefault("display_name", raw.get("bot_name", "Telegram Bot"))
            try:
                return Requirements.model_validate(raw)
            except PydanticValidationError as e2:
                raise ValidationError(f"Invalid requirements: {e2}") from e2

    def _parse_package(self, raw: Dict[str, Any]) -> GeneratedPackage:
        try:
            return GeneratedPackage.model_validate(raw)
        except PydanticValidationError as e:
            if "files" in raw and isinstance(raw["files"], dict):
                return GeneratedPackage(files=raw["files"], notes=str(raw.get("notes", "")))
            raise ValidationError(f"Invalid package: {e}") from e

    async def understand_idea(self, user_idea: str, language_hint: str = "mixed") -> Requirements:
        t0 = time.perf_counter()
        messages = [
            {"role": "system", "content": IDEA_UNDERSTANDING_PROMPT},
            {
                "role": "user",
                "content": f"User idea:\n{user_idea}\n\nPreferred language hint: {language_hint}",
            },
        ]
        raw = await self.llm.chat_json(messages, temperature=0.1)
        req = self._parse_requirements(raw)
        metrics.timing("gen.understand_ms", (time.perf_counter() - t0) * 1000)
        metrics.incr("gen.understand")
        logger.info(
            f"Understood: name={req.bot_name} cat={req.category} "
            f"complex={req.is_complex}/{req.estimated_complexity}"
        )
        return req

    async def apply_clarifications(self, previous: Requirements, answers: str) -> Requirements:
        messages = [
            {"role": "system", "content": CLARIFY_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Previous requirements:\n{previous.model_dump_json(indent=2)}\n\n"
                    f"User answers:\n{answers}"
                ),
            },
        ]
        raw = await self.llm.chat_json(messages, temperature=0.1)
        return self._parse_requirements(raw)

    async def generate_code(self, requirements: Requirements) -> GeneratedPackage:
        t0 = time.perf_counter()
        messages = [
            {"role": "system", "content": CODE_GENERATION_PROMPT},
            {
                "role": "user",
                "content": (
                    "Generate a complete production-ready Telegram bot.\n\n"
                    f"{requirements.model_dump_json(indent=2)}"
                ),
            },
        ]
        raw = await self.llm.chat_json(messages, temperature=0.12, max_tokens=16000)
        pkg = self._parse_package(raw)
        metrics.timing("gen.code_ms", (time.perf_counter() - t0) * 1000)
        metrics.incr("gen.code")
        return pkg

    async def generate_step(
        self,
        requirements: Requirements,
        step_number: int,
        total_steps: int,
        step_goal: str,
        previous_files: Dict[str, str],
    ) -> Dict[str, Any]:
        prev_preview = {
            k: (v[:2000] + "..." if len(v) > 2000 else v) for k, v in list(previous_files.items())[:20]
        }
        prompt = STEP_GENERATION_PROMPT.format(
            step_number=step_number,
            total_steps=total_steps,
            step_goal=step_goal,
            previous_files=json.dumps(prev_preview, ensure_ascii=False, indent=2),
            requirements=requirements.model_dump_json(indent=2),
        )
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"Implement step {step_number}: {step_goal}"},
        ]
        raw = await self.llm.chat_json(messages, temperature=0.12, max_tokens=16000)
        if "files" not in raw:
            raise ValidationError("Step generation missing 'files'")
        return raw

    async def self_review(self, pkg: GeneratedPackage) -> GeneratedPackage:
        files_preview = {
            name: content[:2800] + ("..." if len(content) > 2800 else "")
            for name, content in list(pkg.files.items())[:25]
        }
        messages = [
            {"role": "system", "content": SELF_REVIEW_PROMPT},
            {
                "role": "user",
                "content": (
                    "Review this Telegram bot project carefully:\n\n"
                    f"{json.dumps(files_preview, ensure_ascii=False, indent=2)}"
                ),
            },
        ]
        raw = await self.llm.chat_json(messages, temperature=0.05)
        try:
            review = ReviewResult.model_validate(raw)
        except PydanticValidationError:
            review = ReviewResult(
                is_safe=raw.get("is_safe", True),
                has_critical_bugs=raw.get("has_critical_bugs", False),
                bugs_found=raw.get("bugs_found") or [],
                security_issues=raw.get("security_issues") or [],
                overall_quality=raw.get("overall_quality") or "good",
                ready_to_deploy=raw.get("ready_to_deploy", True),
                fixed_files=raw.get("fixed_files") or {},
            )

        if review.fixed_files:
            for fname, content in review.fixed_files.items():
                if content and len(content) > 40:
                    pkg.files[fname.replace("\\", "/")] = content
                    logger.info(f"Self-fix applied: {fname}")

        pkg.review = review
        metrics.incr("gen.review")
        return pkg

    def validate(self, files: Dict[str, str]) -> Tuple[bool, List[str]]:
        ok, issues = validate_package(files)
        if not ok:
            metrics.incr("gen.validation_fail")
        else:
            metrics.incr("gen.validation_ok")
        return ok, issues

    def _is_complex(self, req: Requirements) -> bool:
        if req.is_complex or req.estimated_complexity == "complex":
            return True
        return len(req.generation_plan) >= 3

    async def full_pipeline(
        self, user_idea: str, language_hint: str = "mixed"
    ) -> Dict[str, Any]:
        t0 = time.perf_counter()
        metrics.incr("gen.pipeline_start")

        req = await self.understand_idea(user_idea, language_hint)

        if req.needs_clarification and req.clarifying_questions:
            return {
                "requirements": req.model_dump(),
                "needs_clarification": True,
                "needs_step_by_step": False,
                "clarifying_questions": req.clarifying_questions,
                "code": None,
                "review": None,
                "is_safe": True,
                "validation_issues": [],
            }

        if self._is_complex(req):
            plan = req.generation_plan or [
                "Project structure, config, states",
                "Keyboards and start/help handlers",
                "Core game/logic handlers",
                "Score/health/inventory + endings",
                "main.py, README, Dockerfile, final polish",
            ]
            data = req.model_dump()
            data["generation_plan"] = plan
            return {
                "requirements": data,
                "needs_clarification": False,
                "needs_step_by_step": True,
                "generation_plan": plan,
                "clarifying_questions": [],
                "code": None,
                "review": None,
                "is_safe": True,
                "validation_issues": [],
            }

        # One-shot path
        pkg = await self.generate_code(req)
        pkg = await self.self_review(pkg)
        ok, issues = self.validate(pkg.files)

        # One automatic repair pass if validation failed
        if not ok:
            logger.warning(f"Validation failed ({len(issues)} issues), attempting repair")
            metrics.incr("gen.auto_repair")
            repair_feedback = "Fix these validation issues:\n" + "\n".join(f"- {i}" for i in issues[:12])
            improved = await self.improve_from_feedback(req, pkg.files, repair_feedback)
            pkg = self._parse_package(improved.get("code") or {"files": pkg.files})
            if improved.get("review"):
                try:
                    pkg.review = ReviewResult.model_validate(improved["review"])
                except Exception:
                    pass
            ok, issues = self.validate(pkg.files)

        review_dict = pkg.review.model_dump() if pkg.review else {}
        is_safe = ok and review_dict.get("is_safe", True) and not review_dict.get("has_critical_bugs", False)

        if not is_safe:
            metrics.incr("gen.unsafe")
        else:
            metrics.incr("gen.success")

        metrics.timing("gen.pipeline_ms", (time.perf_counter() - t0) * 1000)

        return {
            "requirements": req.model_dump(),
            "needs_clarification": False,
            "needs_step_by_step": False,
            "clarifying_questions": [],
            "code": {
                "files": pkg.files,
                "notes": pkg.notes,
                "entry_point": pkg.entry_point,
                "review": review_dict,
            },
            "review": review_dict,
            "is_safe": is_safe,
            "validation_issues": issues,
        }

    async def run_step_pipeline(
        self,
        requirements: Dict[str, Any],
        step_index: int,
        previous_files: Dict[str, str],
    ) -> Dict[str, Any]:
        req = self._parse_requirements(requirements)
        plan = req.generation_plan or requirements.get("generation_plan") or []
        total = len(plan)
        if step_index >= total:
            raise ValidationError("Step index out of range")

        step_goal = plan[step_index]
        raw = await self.generate_step(
            requirements=req,
            step_number=step_index + 1,
            total_steps=total,
            step_goal=step_goal,
            previous_files=previous_files,
        )
        files = raw.get("files") or {}
        # merge: new wins
        merged = {**previous_files, **files}
        is_last = (step_index + 1) >= total or bool(raw.get("is_final_step"))

        review_dict: Dict[str, Any] = {}
        is_safe = True
        issues: List[str] = []

        if is_last:
            pkg = GeneratedPackage(files=merged, notes=raw.get("step_notes", ""))
            pkg = await self.self_review(pkg)
            merged = pkg.files
            ok, issues = self.validate(merged)
            if not ok:
                metrics.incr("gen.auto_repair")
                repair = "Fix validation issues:\n" + "\n".join(f"- {i}" for i in issues[:12])
                improved = await self.improve_from_feedback(req, merged, repair)
                merged = (improved.get("code") or {}).get("files") or merged
                ok, issues = self.validate(merged)
            review_dict = pkg.review.model_dump() if pkg.review else {}
            is_safe = ok and review_dict.get("is_safe", True)
            if is_safe:
                metrics.incr("gen.success")
            else:
                metrics.incr("gen.unsafe")

        return {
            "files": merged,
            "step_notes": raw.get("step_notes", step_goal),
            "step_index": step_index,
            "total_steps": total,
            "is_last": is_last,
            "review": review_dict,
            "is_safe": is_safe,
            "validation_issues": issues,
        }

    async def improve_from_feedback(
        self,
        requirements: Requirements | Dict[str, Any],
        previous_files: Dict[str, str],
        feedback: str,
    ) -> Dict[str, Any]:
        if isinstance(requirements, dict):
            req_json = json.dumps(requirements, ensure_ascii=False, indent=2)
        else:
            req_json = requirements.model_dump_json(indent=2)

        preview = {k: v[:1800] for k, v in list(previous_files.items())[:20]}
        messages = [
            {
                "role": "system",
                "content": IMPROVE_PROMPT.format(
                    feedback=feedback,
                    requirements=req_json,
                    previous_files=json.dumps(preview, ensure_ascii=False, indent=2),
                ),
            },
            {"role": "user", "content": "Produce the improved complete project as JSON."},
        ]
        raw = await self.llm.chat_json(messages, temperature=0.12, max_tokens=16000)
        pkg = self._parse_package(raw)
        pkg = await self.self_review(pkg)
        ok, issues = self.validate(pkg.files)
        review_dict = pkg.review.model_dump() if pkg.review else {}
        return {
            "code": {
                "files": pkg.files,
                "notes": pkg.notes,
                "review": review_dict,
            },
            "review": review_dict,
            "is_safe": ok and review_dict.get("is_safe", True),
            "validation_issues": issues,
        }


code_generator = CodeGenerator()
