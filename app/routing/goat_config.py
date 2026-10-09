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


# V0.16 domain-aware defaults.
#
# GOAT tiers describe required capability.
# Task category decides which provider family is normally the best fit.
#
# This prevents a global "build = Codex" rule from accidentally routing
# nearly every normal implementation task to the same provider.
DOMAIN_TIER_DEFAULTS = {
    "frontend": {
        "quick": {"model": "sonnet", "effort": "low"},
        "build": {"model": "sonnet", "effort": "medium"},
        "deep": {"model": "opus", "effort": "high"},
    },
    "backend": {
        "quick": {"model": "luna", "effort": "low"},
        "build": {"model": "sol", "effort": "medium"},
        "deep": {"model": "sol", "effort": "high"},
    },
    "setup": {
        "quick": {"model": "luna", "effort": "low"},
        "build": {"model": "sol", "effort": "medium"},
        "deep": {"model": "sol", "effort": "high"},
    },
    "architecture": {
        "quick": {"model": "sonnet", "effort": "low"},
        "build": {"model": "opus", "effort": "medium"},
        "deep": {"model": "opus", "effort": "high"},
    },
    "general_engineering": {
        "quick": {"model": "luna", "effort": "low"},
        "build": {"model": "sol", "effort": "medium"},
        "deep": {"model": "sol", "effort": "high"},
    },
}


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

    def routing_mode(self) -> str:
        """
        Routing mode contract.

        AUTO:
            Domain/risk-aware GOAT routing chooses the execution model.

        MANUAL:
            Explicit dashboard tier selections are authoritative.

        Legacy config files without a mode are treated as AUTO so an old
        saved tier snapshot cannot silently pin every task to one provider.
        """
        if not self.path.exists():
            return "auto"

        try:
            payload = json.loads(
                self.path.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError):
            return "auto"

        if not isinstance(payload, dict):
            return "auto"

        mode = str(payload.get("mode") or "auto").lower()

        return "manual" if mode == "manual" else "auto"

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

    def _saved_tier_selection(
        self,
        tier: GoatTier,
    ) -> TierSelection | None:
        """
        Return a valid explicit user/dashboard override for exactly one tier.

        Domain-aware defaults must never override an explicit runtime choice.
        """
        if not self.path.exists():
            return None

        try:
            payload = json.loads(
                self.path.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError):
            return None

        saved = (
            payload.get("tiers")
            if isinstance(payload, dict) and "tiers" in payload
            else payload
        )

        if not isinstance(saved, dict):
            return None

        value = saved.get(tier)

        if not isinstance(value, dict):
            return None

        model = value.get("model")
        effort = value.get("effort")

        if model not in MODEL_CATALOG:
            return None

        if effort not in VALID_EFFORTS:
            return None

        if model == "rules" and tier != "triage":
            return None

        return TierSelection(
            model=model,
            effort=effort,
        )

    def _resolved_model(
        self,
        *,
        tier: GoatTier,
        model_key: str,
        effort: str,
        source: str,
    ) -> ResolvedTier:
        model = MODEL_CATALOG[model_key]

        return ResolvedTier(
            tier=tier,
            model_key=model_key,
            executable_model=model["cli_model"],
            owner=model["owner"],
            effort=None if model_key == "rules" else effort,
            source=source,
        )

    def resolve_for_task(
        self,
        tier: GoatTier,
        category: str,
    ) -> ResolvedTier:
        """
        Resolve an execution model using both capability tier and task domain.

        Special tiers keep their canonical behavior. Normal coding tiers are
        provider-neutral and use category-aware defaults.
        """
        # Saved dashboard tier values become authoritative only in
        # explicit MANUAL routing mode.
        if (
            self.routing_mode() == "manual"
            and self._saved_tier_selection(tier) is not None
        ):
            return self.resolve(tier)

        if tier in {
            "triage",
            "create",
            "review",
            "esc",
        }:
            return self.resolve(tier)

        profile = (
            DOMAIN_TIER_DEFAULTS
            .get(category, {})
            .get(tier)
        )

        if not profile:
            return self.resolve(tier)

        return self._resolved_model(
            tier=tier,
            model_key=profile["model"],
            effort=profile["effort"],
            source="goat_domain_default",
        )

    def resolve_escalation(
        self,
        primary_owner: str,
    ) -> ResolvedTier:
        """
        One bounded escalation, intentionally crossing provider families.

        Codex primary -> Claude escalation.
        Claude primary -> Codex escalation.
        """
        # Explicit dashboard escalation config is authoritative only
        # when the operator intentionally selected MANUAL routing.
        if (
            self.routing_mode() == "manual"
            and self._saved_tier_selection("esc") is not None
        ):
            return self.resolve("esc")

        if primary_owner == "codex":
            return self._resolved_model(
                tier="esc",
                model_key="fable",
                effort="high",
                source="goat_cross_provider_escalation",
            )

        if primary_owner == "claude_code":
            return self._resolved_model(
                tier="esc",
                model_key="astra",
                effort="high",
                source="goat_cross_provider_escalation",
            )

        return self.resolve("esc")

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
