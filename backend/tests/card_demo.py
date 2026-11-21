"""Shared helper for card tests: the Pizzeria Amalfi demo context and its shortlisted candidates (no DB, no model)."""

import importlib.util
from functools import lru_cache
from pathlib import Path

from app.managers.card_manager import evaluate, shortlist
from app.services.card_templates import active_goals, templates_for

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "preview_cards.py"


@lru_cache(maxsize=1)
def demo_context():
    spec = importlib.util.spec_from_file_location("preview_cards", _SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.demo_context()


def demo_shortlist():
    context = demo_context()
    evaluated = [
        item
        for template in templates_for(active_goals(context))
        for candidate in template.detect(context)
        for item in [evaluate(context, template, candidate)]
        if item
    ]
    return context, shortlist(evaluated)
