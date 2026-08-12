"""
Unit tests for gap_parser.py (v0.5.0)
"""
import pytest
import json
from src.parsers.gap_parser import parse_gap_response, GapItem, UpdateItem

def test_parse_gap_response_plain_text():
    # Test plain text gap response parsing
    response_text = """
- Herpes Zoster Ophthalmicus (HZO)
    - Acute disease
        - Clinical course
            - (create) Zoster Sine Herpete::Patients can experience HZO dermatomal pain without rash.
            - (update) Standard treatment:>Valacyclovir 1g TID for 7~10 days
            - Normal item without tag should be ignored
        - (update) Another Section: This is new info
"""
    gaps, updates = parse_gap_response(response_text)
    
    assert len(gaps) == 1
    assert gaps[0].term == "Zoster Sine Herpete::Patients can experience HZO dermatomal pain without rash."
    assert gaps[0].content == "Zoster Sine Herpete::Patients can experience HZO dermatomal pain without rash."
    assert gaps[0].breadcrumb == "[Herpes Zoster Ophthalmicus (HZO) > Acute disease > Clinical course]"
    assert gaps[0].breadcrumb_parts == ["Herpes Zoster Ophthalmicus (HZO)", "Acute disease", "Clinical course"]

    assert len(updates) == 2
    assert updates[0].existing_term == "Standard treatment"
    assert updates[0].new_content == "Valacyclovir 1g TID for 7~10 days"
    
    assert updates[1].existing_term == "Another Section"
    assert updates[1].new_content == "This is new info"

def test_parse_gap_response_json_wrapped():
    # Test json response wrapped in markdown block
    response_json = {
        "text": """
- HZO
    - (create) New Fact Example::Value
    - (update) **Existing Fact** : Updated Content here
"""
    }
    json_text = f"```json\n{json.dumps(response_json)}\n```"
    gaps, updates = parse_gap_response(json_text)
    
    assert len(gaps) == 1
    assert gaps[0].term == "New Fact Example::Value"
    assert gaps[0].breadcrumb == "[HZO]"
    
    assert len(updates) == 1
    # Bold marker ** should be stripped from existing_term
    assert updates[0].existing_term == "Existing Fact"
    assert updates[0].new_content == "Updated Content here"

def test_parse_gap_response_empty():
    gaps, updates = parse_gap_response("")
    assert len(gaps) == 0
    assert len(updates) == 0
    
    gaps, updates = parse_gap_response("gaps\nupdates\n.\n")
    assert len(gaps) == 0
    assert len(updates) == 0

def test_parse_gap_response_update_delimiters():
    # Test update split with different delimiters
    text = """
- Category
    - (update) Key::Val1
    - (update) Key2:>Val2
    - (update) Key3:Val3
    - (update) Key4 (no delimiter)
"""
    _, updates = parse_gap_response(text)
    assert len(updates) == 4
    
    assert updates[0].existing_term == "Key"
    assert updates[0].new_content == "Val1"
    
    assert updates[1].existing_term == "Key2"
    assert updates[1].new_content == "Val2"
    
    assert updates[2].existing_term == "Key3"
    assert updates[2].new_content == "Val3"
    
    assert updates[3].existing_term == "Key4 (no delimiter)"
    assert updates[3].new_content == "Key4 (no delimiter)"
