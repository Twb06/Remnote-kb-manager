"""
Unit tests for resolve_slot in slot_matcher.py (v0.5.0)
"""
from src.routers.slot_matcher import resolve_slot

def test_resolve_slot_exact_match():
    # Exact canonical slot matching
    assert resolve_slot("overview") == "overview"
    assert resolve_slot("Presentation") == "presentation"
    assert resolve_slot("management  ") == "management"

def test_resolve_slot_alias_match():
    # Matching aliases
    assert resolve_slot("clinical presentation") == "presentation"
    assert resolve_slot("treatment") == "management"
    assert resolve_slot("causes") == "etiology"
    assert resolve_slot("clinical course") == "presentation"

def test_resolve_slot_substring_match():
    # Substring matching
    assert resolve_slot("epidemiology facts") == "epidemiology"
    assert resolve_slot("some signs here") == "signs"

def test_resolve_slot_fallback():
    # No match found, return normalized subject
    assert resolve_slot("completely unknown heading") == "completely unknown heading"
