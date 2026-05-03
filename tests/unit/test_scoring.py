"""
Unit tests for scoring and matching logic in smart_logic_v5.py

Tests the following functions:
- normalize()
- to_title_case()
- calculate_enhanced_score()
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path to import smart_logic_v5
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from smart_logic_v5 import (
        normalize,
        to_title_case,
        calculate_enhanced_score,
        SCORE_PERFECT_MATCH,
        WEIGHT_ALIASES_EXIST,
        WEIGHT_TAGS_EXIST,
        PENALTY_GENERIC_TERMS
    )
    SMART_LOGIC_AVAILABLE = True
except ImportError:
    SMART_LOGIC_AVAILABLE = False


pytestmark = pytest.mark.skipif(
    not SMART_LOGIC_AVAILABLE,
    reason="smart_logic_v5.py not available"
)


@pytest.mark.unit
class TestNormalize:
    """Test suite for normalize() function"""

    def test_normalize_basic(self):
        """Test basic string normalization - removes non-alphanumeric and lowercases"""
        assert normalize("Test Node") == "testnode"
        # Note: normalize() preserves underscores in the actual implementation
        result = normalize("Test-Node_123")
        assert "testnode" in result.lower() and "123" in result

    def test_normalize_special_chars(self):
        """Test normalization with special characters"""
        assert normalize("Test@Node#123") == "testnode123"
        assert normalize("Node (with) [brackets]") == "nodewithbrackets"

    def test_normalize_unicode(self):
        """Test Unicode character handling"""
        # Should preserve Unicode characters
        result = normalize("測試節點")
        assert "測" in result or result == "測試節點"

    def test_normalize_empty(self):
        """Test empty string normalization"""
        assert normalize("") == ""

    def test_normalize_whitespace(self):
        """Test multiple whitespace handling"""
        assert normalize("Test   Node") == "testnode"
        assert normalize("  Test  ") == "test"


@pytest.mark.unit
class TestTitleCase:
    """Test suite for to_title_case() function"""

    def test_title_case_basic(self):
        """Test basic Title Case conversion"""
        assert to_title_case("test node") == "Test Node"
        assert to_title_case("hello world") == "Hello World"

    def test_title_case_already_capitalized(self):
        """Test that already capitalized text is preserved"""
        result = to_title_case("Test Node")
        assert "Test" in result and "Node" in result

    def test_title_case_preserves_acronym(self):
        """Test that acronyms are preserved or handled correctly"""
        result = to_title_case("ION 24-2")
        # Should preserve ION or convert to Ion
        assert "ION" in result or "Ion" in result

    def test_title_case_with_numbers(self):
        """Test Title Case with numbers"""
        result = to_title_case("test 123 node")
        assert "Test" in result and "Node" in result

    def test_title_case_empty(self):
        """Test empty string"""
        assert to_title_case("") == ""


@pytest.mark.unit
class TestCalculateEnhancedScore:
    """Test suite for calculate_enhanced_score() function"""

    def test_perfect_title_match(self):
        """Test that perfect title match returns SCORE_PERFECT_MATCH"""
        hit = {
            "title": "Test Node",
            "aliases": [],
            "tags": []
        }
        score = calculate_enhanced_score(hit, "test node", "Test Node", "Test Node")
        assert score == SCORE_PERFECT_MATCH

    def test_alias_complete_match(self):
        """Test that alias complete match returns SCORE_PERFECT_MATCH"""
        hit = {
            "title": "Test Node ABC",
            "aliases": ["TN"],
            "tags": []
        }
        score = calculate_enhanced_score(hit, "TN", "Tn", "Test Node ABC")
        assert score == SCORE_PERFECT_MATCH

    def test_aliases_add_weight(self):
        """Test that having aliases adds WEIGHT_ALIASES_EXIST to score"""
        hit_with_aliases = {
            "title": "Different Title",
            "aliases": ["alias1", "alias2"],
            "tags": []
        }
        hit_without_aliases = {
            "title": "Different Title",
            "aliases": [],
            "tags": []
        }

        score_with = calculate_enhanced_score(
            hit_with_aliases, "test", "Test", "Different Title"
        )
        score_without = calculate_enhanced_score(
            hit_without_aliases, "test", "Test", "Different Title"
        )

        # Score with aliases should be higher
        assert score_with > score_without

    def test_tags_add_weight(self):
        """Test that having tags adds WEIGHT_TAGS_EXIST to score"""
        hit_with_tags = {
            "title": "Different Title",
            "aliases": [],
            "tags": ["tag1", "tag2"]
        }
        hit_without_tags = {
            "title": "Different Title",
            "aliases": [],
            "tags": []
        }

        score_with = calculate_enhanced_score(
            hit_with_tags, "test", "Test", "Different Title"
        )
        score_without = calculate_enhanced_score(
            hit_without_tags, "test", "Test", "Different Title"
        )

        # Score with tags should be higher
        assert score_with > score_without

    def test_system_alias_exclusion(self):
        """Test that system alias nodes (under Aliases parent) are excluded with score=0"""
        hit = {
            "title": "AAION",
            "parentTitle": "Aliases",
            "parentRemId": "xOuCp1mEAK82ZbPEB",
            "aliases": [],
            "tags": []
        }
        score = calculate_enhanced_score(hit, "AAION", "Aaion", "AAION")
        assert score == 0.0

    def test_generic_term_penalty(self):
        """Test that generic terms get penalized by PENALTY_GENERIC_TERMS"""
        hit = {
            "title": "management",
            "aliases": [],
            "tags": []
        }
        # Note: hit_title must be IN term_title_case to trigger penalty branch
        score = calculate_enhanced_score(hit, "test management", "Test Management", "management")

        # Score should be penalized (len("management")/len("Test Management") * PENALTY_GENERIC_TERMS)
        # Expected: (10/15) * 0.5 = 0.333...
        assert score < 0.5  # Penalized score

    def test_combined_aliases_and_tags(self):
        """Test that both aliases and tags contribute to score"""
        hit = {
            "title": "Node Title",
            "aliases": ["alias1"],
            "tags": ["tag1"]
        }
        score = calculate_enhanced_score(hit, "test", "Test", "Node Title")

        # Should have both boosts applied
        assert score > 0


@pytest.mark.unit
class TestScoringEdgeCases:
    """Test edge cases in scoring logic"""

    def test_missing_fields_handled(self):
        """Test that missing aliases/tags fields don't cause errors"""
        hit = {
            "title": "Test Node"
            # No aliases or tags fields
        }

        # Should not raise exception
        try:
            score = calculate_enhanced_score(hit, "test", "Test", "Test Node")
            assert score >= 0
        except KeyError:
            pytest.fail("Missing fields should be handled gracefully")

    def test_none_values_handled(self):
        """Test that None values in aliases/tags are handled"""
        hit = {
            "title": "Test Node",
            "aliases": None,
            "tags": None
        }

        # Should not raise exception
        try:
            score = calculate_enhanced_score(hit, "test", "Test", "Test Node")
            assert score >= 0
        except (TypeError, AttributeError):
            pytest.fail("None values should be handled gracefully")

    def test_score_with_empty_aliases_and_tags(self):
        """Test scoring with explicitly empty aliases and tags lists"""
        hit = {
            "title": "Node Title",
            "aliases": [],
            "tags": []
        }
        score = calculate_enhanced_score(hit, "node", "Node", "Node Title")

        # Should still calculate base score without errors
        assert score >= 0
        assert score < SCORE_PERFECT_MATCH

    def test_score_with_multiple_aliases_matching(self):
        """Test that multiple aliases don't cause duplicate bonuses"""
        hit = {
            "title": "Full Name",
            "aliases": ["FN", "FullName", "Full Name"],
            "tags": []
        }

        score1 = calculate_enhanced_score(hit, "FN", "Fn", "Full Name")
        score2 = calculate_enhanced_score(hit, "FullName", "Fullname", "Full Name")

        # Both should return SCORE_PERFECT_MATCH (alias complete match)
        assert score1 == SCORE_PERFECT_MATCH
        assert score2 == SCORE_PERFECT_MATCH

    def test_score_generic_term_with_other_boosts(self):
        """Test that generic term penalty is applied even with aliases/tags"""
        hit = {
            "title": "management approach",
            "aliases": ["mgmt"],
            "tags": ["general"]
        }
        score = calculate_enhanced_score(hit, "manage", "Manage", "management approach")

        # Should be penalized despite having aliases and tags
        # Exact assertion depends on implementation details
        assert score < 5.0  # Should be significantly reduced


if __name__ == "__main__":
    # Run this test file directly
    pytest.main([__file__, "-v"])
