"""
Unit tests for rag_pipeline.py (v0.5.0)
"""
import pytest
import os
import json
from unittest.mock import AsyncMock, MagicMock, patch
from src.pipeline.rag_pipeline import RAGPipeline
from src.parsers.gap_parser import GapItem, UpdateItem

@pytest.fixture
def anyio_backend():
    return 'asyncio'

@pytest.fixture
def mock_clients():
    with patch('src.pipeline.rag_pipeline.NotebookLMClient') as mock_nb_cls, \
         patch('src.pipeline.rag_pipeline.RemNoteClient') as mock_rem_cls:
        
        mock_nb = mock_nb_cls.return_value
        mock_rem = mock_rem_cls.return_value
        
        # Setup basic async mocks
        mock_nb.ask = AsyncMock()
        mock_nb.add_source = AsyncMock()
        mock_nb.list_sources = AsyncMock()
        mock_nb.delete_source = AsyncMock()
        mock_nb.wait_source = AsyncMock()
        
        yield mock_nb, mock_rem

@pytest.mark.anyio
async def test_resolve_or_create_parent_path_cache_hit(mock_clients):
    _, mock_rem = mock_clients
    pipeline = RAGPipeline(dry_run=True, is_disease=True)
    
    # Pre-populate cache
    pipeline._path_id_cache = {
        "acute disease > clinical course": "rem-123"
    }
    
    res = await pipeline._resolve_or_create_parent_path(
        ["acute disease", "clinical course"], 
        "target-folder"
    )
    
    assert res == "rem-123"
    mock_rem.set_rem_title.assert_called_with("rem-123", "clinical course")
    mock_rem.search.assert_not_called()
    mock_rem.create.assert_not_called()

@pytest.mark.anyio
async def test_resolve_or_create_parent_path_direct_match(mock_clients):
    _, mock_rem = mock_clients
    pipeline = RAGPipeline(dry_run=True, is_disease=True)
    
    # Mock search response for direct match on deepest term "clinical course"
    mock_rem.search.return_value = [
        {
            "title": "clinical course",
            "parentTitle": "acute disease",
            "remId": "matched-123",
            "parentRemId": "parent-456"
        }
    ]
    
    res = await pipeline._resolve_or_create_parent_path(
        ["acute disease", "clinical course"],
        "target-folder"
    )
    
    assert res == "matched-123"
    assert pipeline._path_id_cache["acute disease > clinical course"] == "matched-123"
    assert pipeline._path_id_cache["acute disease"] == "parent-456"
    
    # Verifies direct search was called for the deepest category
    mock_rem.search.assert_called_once_with("clinical course", parent_id="target-folder")
    mock_rem.create.assert_not_called()

@pytest.mark.anyio
async def test_resolve_or_create_parent_path_fallback(mock_clients):
    _, mock_rem = mock_clients
    pipeline = RAGPipeline(dry_run=True, is_disease=True)
    
    # Direct match returns empty or mismatch
    mock_rem.search.side_effect = [
        [], # First search for deepest category "clinical course" fails direct match
        [{"title": "acute disease", "remId": "existing-acute"}], # Step 1 of fallback: search for "acute disease" finds existing
        []  # Step 2 of fallback: search for "clinical course" under "existing-acute" fails -> creates
    ]
    
    mock_rem.create.return_value = {"remId": "created-clinical"}
    
    res = await pipeline._resolve_or_create_parent_path(
        ["acute disease", "clinical course"],
        "target-folder"
    )
    
    assert res == "created-clinical"
    assert pipeline._path_id_cache["acute disease"] == "existing-acute"
    assert pipeline._path_id_cache["acute disease > clinical course"] == "created-clinical"
    
    mock_rem.create.assert_called_once_with("clinical course", parent_id="existing-acute")

@pytest.mark.anyio
async def test_execute_with_gaps_file(mock_clients, tmp_path):
    _, mock_rem = mock_clients
    pipeline = RAGPipeline(dry_run=True, is_disease=True)
    
    # Create temporary gaps markdown file with 4-space indent
    gaps_md = tmp_path / "gaps.md"
    gaps_md.write_text("""
- HZO
    - Acute disease
        - (create) Zoster Sine Herpete::Some fact content here
        - (update) Standard treatment::New Treatment Protocol
""", encoding="utf-8")

    mock_rem.search.return_value = [] # no existing items found
    
    with patch.object(pipeline, '_resolve_or_create_parent_path', new_callable=AsyncMock) as mock_resolve:
        mock_resolve.return_value = "parent-folder-id"
        
        await pipeline.execute(
            target_folder_id="target-folder",
            topic="HZO",
            gaps_file=str(gaps_md)
        )
        
        # Verify markdown parsing result triggered creations/updates
        assert mock_resolve.call_count == 2
        mock_resolve.assert_any_call(["HZO", "Acute disease"], "target-folder")
        mock_resolve.assert_any_call([], "target-folder")
        
        # RemNoteClient.create should be called with content and resolved parent id
        mock_rem.create.assert_any_call("Zoster Sine Herpete::Some fact content here", parent_id="parent-folder-id")
        mock_rem.create.assert_any_call("New Treatment Protocol", parent_id="parent-folder-id")
