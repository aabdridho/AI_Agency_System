from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Literal

from pydantic import BaseModel


GoatTier = Literal[
    "triage",
    "quick",
    "build",
    "deep",
    "create",
    "review",
    "esc",
]


class TierSelection(BaseModel):
    model: str
    effort: str


class ResolvedTier(BaseModel):
    tier: GoatTier
    model_key: str
    executable_model: str | None
    owner: str
    effort: str | None
    source: str


# Canonical defaults. These mirror the Control Room defaults.
DEFAULT_TIERS: dict[str, dict[str, str]] = {
    "triage": {"model": "rules", "effort": "low"},
    "quick": {"model": "luna", "effort": "low"},
    "build": {"model": "sol", "effort": "medium"},
    "deep": {"model": "opus", "effort": "high"},
    "create": {"model": "sonnet", "effort": "medium"},
    "review": {"model": "sol", "effort": "medium"},
    "esc": {"model": "astra", "effort": "high"},
}


# Dashboard model key -> CLI model argument.
#
# OpenAI models are explicit canonical names.
# Claude aliases are intentionally kept as aliases because Claude Code
# resolves them and reports the canonical model in its JSON telemetry.
MODEL_CATALOG = {
    "rules": {
        "owner": "internal_decision",
        "cli_model": None,
    },
    "haiku": {
        "owner": "claude_code",
        "cli_model": "haiku",
    },
    "sonnet": {
        "owner": "claude_code",
        "cli_model": "sonnet",
    },
    "opus": {
        "owner": "claude_code",
        "cli_model": "opus",
    },
    "fable": {
        "owner": "claude_code",
        "cli_model": "fable",
    },
    "luna": {
        "owner": "codex",
        "cli_model": "gpt-6-luna",
    },
    "sol": {
        "owner": "codex",
        "cli_model": "gpt-6.1-sol",
    },
    "astra": {
        "owner": "codex",
        "cli_model": "gpt-6-astra",
    },
}


VALID_EFFORTS = {"low", "medium", "high", "xhigh"}


class GoatConfig:
    """
    Canonical runtime resolver for GOAT model tiers.

    UI writes:
        runtime_data/config/tiers.json

    Routing reads the same file.

    The browser is therefore not authoritative: this class validates every
    model and effort before execution receives them.
    """

    def __init__(
        self,
        path: str | Path = Path("runtime_data") / "config" / "tiers.json",
    ):
        self.path = Path(path)

    def load(self) -> tuple[dict[str, dict[str, str]], str]:
        tiers = deepcopy(DEFAULT_TIERS)
        source = "default"

        if not self.path.exists():
            return tiers, source

        try:
            payload = json.loads(
                self.path.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError):
            return tiers, source

        # Support both:
        # {"tiers": {...}}
        # and direct {...}
        saved = (
            payload.get("tiers")
            if isinstance(payload, dict) and "tiers" in payload
            else payload
        )

        if not isinstance(saved, dict):
            return tiers, source

        for tier, value in saved.items():
            if tier not in DEFAULT_TIERS:
                continue
            if not isinstance(value, dict):
                continue

            model = value.get("model")
            effort = value.get("effort")

            if model not in MODEL_CATALOG:
                continue
            if effort not in VALID_EFFORTS:
                continue

            # Triage is the only tier allowed to use rules.
            if model == "rules" and tier != "triage":
                continue

            tiers[tier] = {
                "model": model,
                "effort": effort,
            }
            source = "saved"

        return tiers, source

    def resolve(self, tier: GoatTier) -> ResolvedTier:
        tiers, source = self.load()

        raw = tiers[tier]
        model_key = raw["model"]
        effort = raw["effort"]
        model = MODEL_CATALOG[model_key]

        return ResolvedTier(
            tier=tier,
            model_key=model_key,
            executable_model=model["cli_model"],
            owner=model["owner"],
            effort=None if model_key == "rules" else effort,
            source=(
                "goat_runtime_config"
                if source == "saved"
                else "goat_default_config"
            ),
        )


class GoatTierClassifier:
    """
    Deterministic V0.13 task -> GOAT tier selection.

    This classifier decides required capability.
    GoatConfig separately decides which actual model serves that capability.
    """

    DEEP_TERMS = (
        "payment",
        "midtrans",
        "stripe",
        "auth",
        "authentication",
        "authorization",
        "security",
        "secure",
        "migration",
        "database migration",
        "production incident",
        "architecture",
        "architect",
        "oauth",
        "permission",
        "encryption",
        "billing",
        "transaction",
    )

    CREATIVE_TERMS = (
        "caption",
        "copywriting",
        "naskah",
        "script video",
        "marketing copy",
        "headline",
        "tagline",
        "creative",
        "kreatif",
        "story",
    )

    QUICK_TERMS = (
        "rename",
        "ubah teks",
        "ganti teks",
        "change text",
        "typo",
        "warna tombol",
        "button color",
        "small copy",
        "minor",
        "simple",
        "sederhana",
    )

    def classify(
        self,
        task_text: str,
        category: str,
    ) -> GoatTier:
        text = task_text.lower()

        if category == "qa":
            return "review"

        if any(term in text for term in self.DEEP_TERMS):
            return "deep"

        if any(term in text for term in self.CREATIVE_TERMS):
            return "create"

        if any(term in text for term in self.QUICK_TERMS):
            return "quick"

        if category == "architecture":
            return "deep"

        return "build"
