"""
NotebookLM Client Wrapper using Python SDK
"""
import os
import json
from typing import Optional, Dict, Any, List
from notebooklm import NotebookLMClient as ActualClient

class NotebookLMClient:
    def __init__(self, cli_bin: str = ""):
        # Keep cli_bin signature for backward compatibility, but ignore it
        pass

    async def add_source(self, file_path: str, title: str, notebook_id: Optional[str] = None) -> Optional[str]:
        if not notebook_id:
            print("[NotebookLM] Error: notebook_id is required for add_source")
            return None
        client = await ActualClient.from_storage()
        async with client:
            try:
                # Our local python-api version of add_file takes:
                # (notebook_id, file_path, mime_type=None, wait=False, wait_timeout=120.0)
                # It does not accept 'title' argument. It automatically uses the filename.
                source = await client.sources.add_file(
                    notebook_id=notebook_id,
                    file_path=file_path,
                    wait=True
                )
                return source.id
            except Exception as e:
                msg = f"[NotebookLM] Error adding source: {str(e)}"
                print(msg.encode('cp950', errors='replace').decode('cp950'))
                return None

    async def wait_source(self, source_id: str, timeout: int = 120, notebook_id: Optional[str] = None) -> bool:
        if not notebook_id:
            return False
        client = await ActualClient.from_storage()
        async with client:
            try:
                source = await client.sources.wait_until_ready(
                    notebook_id=notebook_id,
                    source_id=source_id,
                    timeout=float(timeout)
                )
                return source.is_ready
            except Exception as e:
                msg = f"[NotebookLM] Error waiting for source: {str(e)}"
                print(msg.encode('cp950', errors='replace').decode('cp950'))
                return False
        
    async def ask(self, prompt: str, json_output: bool = True, notebook_id: Optional[str] = None) -> str:
        if not notebook_id:
            print("[NotebookLM] Error: notebook_id is required for ask")
            return ""
        client = await ActualClient.from_storage()
        async with client:
            try:
                # ChatAPI.ask takes 'question' parameter instead of 'prompt'
                result = await client.chat.ask(
                    notebook_id=notebook_id,
                    question=prompt
                )
                if json_output:
                    # Package as JSON compatible with the original CLI response
                    return json.dumps({
                        "text": result.answer,
                        "citations": [
                            {"citation_number": ref.citation_number, "source_id": ref.source_id}
                            for ref in result.references
                        ]
                    }, ensure_ascii=False)
                else:
                    return result.answer
            except Exception as e:
                msg = f"[NotebookLM] Error asking: {str(e)}"
                print(msg.encode('cp950', errors='replace').decode('cp950'))
                return ""

    async def list_sources(self, notebook_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if not notebook_id:
            return []
        client = await ActualClient.from_storage()
        async with client:
            try:
                sources = await client.sources.list(notebook_id=notebook_id)
                return [
                    {
                        "id": src.id,
                        "title": src.title,
                        "status": "ready" if src.is_ready else "processing",
                        "created_at": src.created_at.isoformat() if src.created_at else None
                    }
                    for src in sources
                ]
            except Exception as e:
                msg = f"[NotebookLM] Error listing sources: {str(e)}"
                print(msg.encode('cp950', errors='replace').decode('cp950'))
                return []

    async def delete_source(self, source_id: str, notebook_id: Optional[str] = None) -> bool:
        if not notebook_id:
            return False
        client = await ActualClient.from_storage()
        async with client:
            try:
                await client.sources.delete(notebook_id=notebook_id, source_id=source_id)
                return True
            except Exception as e:
                msg = f"[NotebookLM] Error deleting source: {str(e)}"
                print(msg.encode('cp950', errors='replace').decode('cp950'))
                return False
