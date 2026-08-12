"""
slot_matcher.py - Disease template slot mapping for RAG pipeline.

Anchored to the Disease Template defined in:
  .github/skills/remnote_style_transformation/SKILL.md
"""
import re
from typing import List, Dict

DISEASE_SLOTS = frozenset({
    "overview",
    "presentation",
    "examination",
    "management",
    "epidemiology",
    "etiology",
    "risk factors",
    "risk factor",
    "general pathology",
    "pathophysiology",
    "history",
    "physical examination",
    "symptoms",
    "signs",
    "clinical diagnosis",
    "diagnosis"
})

SLOT_ALIASES = {
    "clinical presentation": "presentation",
    "clinical course": "presentation",
    "workup": "examination",
    "treatment": "management",
    "symptom": "symptoms",
    "sign": "signs",
    "causes": "etiology",
    "etiology/pathophysiology": "pathophysiology"
}

def _normalize(text: str) -> str:
    """Lowercase and collapse whitespace."""
    return re.sub(r"\s+", " ", text.strip().lower())

def resolve_slot(subject: str) -> str:
    """
    Map a subject string to a canonical disease template slot name.
    """
    normalized = _normalize(subject)

    if normalized in SLOT_ALIASES:
        return SLOT_ALIASES[normalized]

    if normalized in DISEASE_SLOTS:
        return normalized

    # Substring match against canonical slots
    for slot in sorted(DISEASE_SLOTS, key=len, reverse=True):
        if normalized.startswith(slot) or slot in normalized:
            return slot

    return normalized
