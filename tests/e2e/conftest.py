"""
E2E test fixtures for smart_logic_v5.py

Provides fixtures for end-to-end testing with real or mocked RemNote daemon.
"""

import pytest
import json
import os
from pathlib import Path
from typing import Dict, Any


@pytest.fixture(scope="session")
def e2e_fixtures_dir() -> Path:
    """Return path to E2E fixtures directory"""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def e2e_kb_map(e2e_fixtures_dir, tmp_path) -> Path:
    """Prepare E2E kb_map.json fixture"""
    kb_map_source = e2e_fixtures_dir / "e2e_kb_map.json"

    # Copy to temp directory for test isolation (remove BOM if exists)
    kb_map_test = tmp_path / "e2e_kb_map.json"
    content = kb_map_source.read_text(encoding="utf-8-sig")  # Read with BOM handling
    kb_map_test.write_text(content, encoding="utf-8")  # Write without BOM

    return kb_map_test


@pytest.fixture
def e2e_overview(e2e_fixtures_dir, tmp_path) -> Path:
    """Prepare E2E overview.md fixture"""
    overview_source = e2e_fixtures_dir / "e2e_overview.md"

    # Copy to temp directory (remove BOM if exists)
    overview_test = tmp_path / "e2e_overview.md"
    content = overview_source.read_text(encoding="utf-8-sig")
    overview_test.write_text(content, encoding="utf-8")

    return overview_test


@pytest.fixture
def e2e_content(e2e_fixtures_dir, tmp_path) -> Path:
    """Prepare E2E content.md fixture"""
    content_source = e2e_fixtures_dir / "e2e_content.md"

    # Copy to temp directory (remove BOM if exists)
    content_test = tmp_path / "e2e_content.md"
    content = content_source.read_text(encoding="utf-8-sig")
    content_test.write_text(content, encoding="utf-8")

    return content_test


@pytest.fixture
def remnote_daemon_available() -> bool:
    """Check if RemNote daemon is available"""
    # Try to import and test remnote-cli
    try:
        import subprocess
        result = subprocess.run(
            ["npx", "remnote-cli", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False


@pytest.fixture
def skip_if_no_remnote(remnote_daemon_available):
    """Skip test if RemNote daemon is not available"""
    if not remnote_daemon_available:
        pytest.skip("RemNote daemon not available - set REMNOTE_DAEMON_AVAILABLE=1 to enable")


@pytest.fixture
def e2e_test_env(e2e_kb_map, e2e_overview, e2e_content) -> Dict[str, Any]:
    """Prepare complete E2E test environment"""
    return {
        "kb_map": str(e2e_kb_map),
        "overview": str(e2e_overview),
        "content": str(e2e_content),
        "overview_text": e2e_overview.read_text(encoding="utf-8"),
        "content_text": e2e_content.read_text(encoding="utf-8")
    }


# Marker for E2E tests
def pytest_configure(config):
    """Register custom markers"""
    config.addinivalue_line(
        "markers", "e2e: mark test as end-to-end test (requires RemNote daemon)"
    )
