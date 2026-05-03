"""
Unit tests for parsing functions in smart_logic_v5.py

Tests the following functions:
- parse_kb_map()
- parse_overview()
- parse_md_to_sections()
- extract_knowledge_lines()
"""

import pytest
import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from smart_logic_v5 import (
        parse_kb_map,
        parse_overview,
        parse_md_to_sections
    )
    SMART_LOGIC_AVAILABLE = True
except ImportError:
    SMART_LOGIC_AVAILABLE = False


pytestmark = pytest.mark.skipif(
    not SMART_LOGIC_AVAILABLE,
    reason="smart_logic_v5.py not available"
)


@pytest.mark.unit
class TestParseKbMap:
    """Test suite for parse_kb_map() function"""

    def test_parse_kb_map_json_basic(self, tmp_path, sample_kb_map):
        """Test basic kb_map.json parsing"""
        # Write sample kb_map to temp file
        kb_file = tmp_path / "test_kb_map.json"
        kb_file.write_text(json.dumps(sample_kb_map), encoding="utf-8")

        # Parse the kb_map
        entries = parse_kb_map(str(kb_file))

        # Should return list of entries
        assert isinstance(entries, list)
        assert len(entries) > 0

    def test_parse_kb_map_structure(self, tmp_path, sample_kb_map):
        """Test that parsed entries have correct structure"""
        kb_file = tmp_path / "test_kb_map.json"
        kb_file.write_text(json.dumps(sample_kb_map), encoding="utf-8")

        entries = parse_kb_map(str(kb_file))

        # Each entry should have required fields
        for entry in entries:
            assert "title" in entry
            assert "remId" in entry
            assert "indent" in entry

    def test_parse_kb_map_nested_children(self, tmp_path):
        """Test parsing nested children with correct indentation"""
        kb_map = {
            "root": {"remId": "root", "title": "Root"},
            "branches": [
                {
                    "remId": "b1",
                    "title": "Branch",
                    "summary": "Branch summary",
                    "children": [
                        {
                            "remId": "c1",
                            "title": "Child",
                            "summary": "Child summary",
                            "children": []
                        }
                    ]
                }
            ]
        }
        kb_file = tmp_path / "test_kb_map.json"
        kb_file.write_text(json.dumps(kb_map), encoding="utf-8")

        entries = parse_kb_map(str(kb_file))

        # Should have 2 entries (branch and child)
        assert len(entries) == 2

        # Check indentation levels
        assert entries[0]["indent"] == 0  # Branch
        assert entries[1]["indent"] == 2  # Child (2 spaces per level)

    def test_parse_kb_map_missing_file(self):
        """Test handling of missing kb_map file"""
        result = parse_kb_map("nonexistent_file.json")

        # Should return empty list or handle gracefully
        assert isinstance(result, list)

    def test_parse_kb_map_legacy_format(self, tmp_path):
        """Test parsing legacy SKILL.md format (non-JSON)"""
        # Create legacy format file (covers lines 140-157)
        # Format: - `title` - `remId` - summary
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text(
            "- `Vision Loss` - `remId123` - Overview of vision loss\n"
            "  - `GCA` - `gca456` - Giant Cell Arteritis\n",
            encoding="utf-8"
        )

        entries = parse_kb_map(str(skill_file))

        # Should parse legacy format
        assert len(entries) == 2
        assert entries[0]["title"] == "Vision Loss"
        assert entries[0]["remId"] == "remId123"
        assert entries[1]["indent"] == 2

    def test_parse_kb_map_with_special_characters(self, tmp_path):
        """Test parsing kb_map with special characters in titles"""
        kb_map = {
            "root": {"remId": "root", "title": "Root"},
            "branches": [
                {
                    "remId": "b1",
                    "title": "Node with (parentheses) & symbols",
                    "summary": "Summary with 'quotes' and \"double quotes\"",
                    "children": []
                }
            ]
        }
        kb_file = tmp_path / "test_kb_map.json"
        kb_file.write_text(json.dumps(kb_map), encoding="utf-8")

        entries = parse_kb_map(str(kb_file))

        assert len(entries) == 1
        assert "parentheses" in entries[0]["title"]
        # Check hint content (summary is converted to hint)
        assert "hint" in entries[0] or "summary" in entries[0]

    def test_parse_kb_map_large_file(self, tmp_path):
        """Test parsing large kb_map with 100+ nodes"""
        branches = []
        for i in range(100):
            branches.append({
                "remId": f"node_{i}",
                "title": f"Node {i}",
                "summary": f"Summary {i}",
                "children": []
            })

        kb_map = {
            "root": {"remId": "root", "title": "Root"},
            "branches": branches
        }
        kb_file = tmp_path / "large_kb_map.json"
        kb_file.write_text(json.dumps(kb_map), encoding="utf-8")

        entries = parse_kb_map(str(kb_file))

        # Should handle large files efficiently
        assert len(entries) == 100
        # Verify structure
        assert all("title" in entry and "remId" in entry for entry in entries)

    def test_parse_kb_map_missing_file_logs_warning(self, capsys):
        """Test that missing kb_map file logs warning (covers lines 106-108)"""
        result = parse_kb_map("nonexistent_path.json")

        # Should return empty list
        assert result == []

        # Should log warning to stdout (JSON file error)
        captured = capsys.readouterr()
        assert "[WARN] Failed to read kb_map.json" in captured.out
        assert "nonexistent_path.json" in captured.out


@pytest.mark.unit
class TestParseOverview:
    """Test suite for parse_overview() function"""

    def test_parse_overview_basic(self, sample_overview_md):
        """Test basic overview parsing"""
        result = parse_overview(sample_overview_md)

        # Should return dict with topic and subtopics
        assert isinstance(result, dict)
        assert "topic" in result
        assert "subtopics" in result

    def test_parse_overview_extracts_main_topic(self, sample_overview_md):
        """Test that main topic (bold) is correctly identified"""
        result = parse_overview(sample_overview_md)

        # Main topic should be extracted from bold text
        assert result["topic"] is not None
        assert len(result["topic"]) > 0

    def test_parse_overview_extracts_subtopics(self):
        """Test that subtopics are correctly extracted"""
        overview = """## Overview
- **Main Topic**
- Subtopic 1
- Subtopic 2
- Subtopic 3"""

        result = parse_overview(overview)

        # Should have 3 subtopics
        assert len(result["subtopics"]) == 3
        assert "Subtopic 1" in result["subtopics"]

    def test_parse_overview_empty(self):
        """Test parsing empty overview"""
        result = parse_overview("")

        # Should handle gracefully
        assert isinstance(result, dict)

    def test_parse_overview_with_nested_bullets(self):
        """Test overview with nested bullet structure"""
        overview = """## Overview
- **Main Topic**
  - Sub-bullet under main
  - Another sub-bullet
- Subtopic 1
- Subtopic 2"""

        result = parse_overview(overview)

        # Should handle nested structure
        assert result["topic"] == "Main Topic" or "Main Topic" in result.get("topic", "")
        assert len(result["subtopics"]) >= 2

    def test_parse_overview_no_overview_header(self):
        """Test overview without ## Overview header"""
        overview = """- **Main Topic**
- Subtopic 1"""

        result = parse_overview(overview)

        # Should still parse without header
        assert "topic" in result
        assert len(result.get("topic", "")) > 0

    def test_parse_overview_skips_empty_bullets(self):
        """Test parse_overview skips empty bullet points (covers line 800)"""
        text = """
## Overview
- **Main Topic**
-
- Subtopic 1
-
- Subtopic 2
"""
        result = parse_overview(text)

        # Empty bullets should be skipped
        assert result["topic"] == "Main Topic"
        assert result["subtopics"] == ["Subtopic 1", "Subtopic 2"]
        assert len(result["subtopics"]) == 2  # No empty items


@pytest.mark.unit
class TestParseMdToSections:
    """Test suite for parse_md_to_sections() function"""

    def test_parse_sections_basic(self, sample_content_md):
        """Test basic markdown section parsing"""
        sections = parse_md_to_sections(sample_content_md)

        # Should return dict of sections
        assert isinstance(sections, dict)
        assert len(sections) > 0

    def test_parse_sections_structure(self, sample_content_md):
        """Test that sections have correct structure"""
        sections = parse_md_to_sections(sample_content_md)

        # Each section should have body content
        for section_name, section_data in sections.items():
            assert isinstance(section_data, dict)
            assert "body" in section_data

    def test_parse_sections_extracts_content(self):
        """Test that section content is correctly extracted"""
        md = """- **Section A**
  - Content line 1
  - Content line 2

- **Section B**
  - Content line 3"""

        sections = parse_md_to_sections(md)

        # Should have 2 sections
        assert len(sections) >= 2

        # Sections should have content
        for section_data in sections.values():
            assert len(section_data["body"]) > 0

    def test_parse_sections_empty(self):
        """Test parsing empty markdown"""
        sections = parse_md_to_sections("")

        # Should handle gracefully
        assert isinstance(sections, dict)

    def test_parse_sections_with_empty_sections(self):
        """Test parsing with some empty sections"""
        md = """- **Section A**
  - Content here

- **Section B**

- **Section C**
  - More content"""

        sections = parse_md_to_sections(md)

        # Should handle empty sections
        assert "Section A" in sections or len(sections) >= 2

    def test_parse_sections_with_nested_bold(self):
        """Test parsing with nested bold markers"""
        md = """- **Section A**
  - Point with **emphasized** text
  - Another point"""

        sections = parse_md_to_sections(md)

        # Should parse correctly despite nested bold
        assert len(sections) > 0


# TODO: Add more parsing tests
# - Test extract_knowledge_lines()
# - Test edge cases (malformed markdown, special characters)
# - Test large kb_map files
# - Test backward compatibility with SKILL.md format


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
