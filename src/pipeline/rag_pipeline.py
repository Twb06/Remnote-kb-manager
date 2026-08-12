"""
rag_pipeline.py - NotebookLM RAG-Driven RemNote Sync (v0.5.0)

Implements Phase 0 to Phase 4.
"""
from typing import List, Dict, Optional
import json
import os
import re
import time

from src.pipeline.notebooklm_client import NotebookLMClient
from src.pipeline.remnote_client import RemNoteClient
from src.parsers.gap_parser import parse_gap_response, GapItem, UpdateItem
from src.routers.slot_matcher import resolve_slot
from src.pipeline.core import PipelineV6, get_clean_search_term

class RAGPipeline:
    def __init__(self, dry_run: bool = False, is_disease: bool = False):
        self.notebooklm = NotebookLMClient()
        self.remnote = RemNoteClient(dry_run=dry_run)
        self.core_pipeline = PipelineV6()
        self.is_disease = is_disease
        self.dry_run = dry_run

    async def _resolve_or_create_parent_path(self, breadcrumb_parts: list[str], target_folder_id: str) -> str:
        """
        在大資料夾 target_folder_id 之下，依據 breadcrumb_parts 逐層定位或建立父節點，
        並回傳最末層父分類的 remId。使用記憶體快取與最深層直接定位策略。
        """
        if not breadcrumb_parts:
            return target_folder_id
            
        # 讀取本地快取檔的第一行大標題做為根主題名稱，避免重覆建立根節點
        root_theme_name = ""
        topic_val = getattr(self, "topic", "")
        if topic_val:
            export_file = f"remnote_export_{topic_val}.md"
            if os.path.exists(export_file):
                try:
                    with open(export_file, "r", encoding="utf-8") as f:
                        first_line = f.readline().strip()
                        root_theme_name = re.sub(r'^(?:#+|title:)\s*', '', first_line, flags=re.IGNORECASE).strip().lower()
                except Exception:
                    pass

        self.remnote.set_rem_title(target_folder_id, root_theme_name or topic_val or "Subject Folder")

        clean_parts = []
        for i, category_name in enumerate(breadcrumb_parts):
            if not category_name.strip():
                continue
            cat_lower = category_name.strip().lower()
            # 如果第一層分類的名字與主學科或導出的標題相同，直接視為 root node，不用在 root 下重複建立自己
            if i == 0 and topic_val and (cat_lower == topic_val.lower() or (root_theme_name and cat_lower == root_theme_name)):
                continue
            clean_parts.append(category_name.strip())

        if not clean_parts:
            return target_folder_id

        # 整個路徑快取 Key
        full_path_key = " > ".join([p.lower() for p in clean_parts])
        if not hasattr(self, "_path_id_cache"):
            self._path_id_cache = {}
            
        if full_path_key in self._path_id_cache:
            res_id = self._path_id_cache[full_path_key]
            self.remnote.set_rem_title(res_id, clean_parts[-1])
            return res_id

        # 1. 嘗試「最深層分類直接搜尋策略」 (Direct Deepest Parent Search)
        if len(clean_parts) >= 2:
            deepest_folder_name = clean_parts[-1]
            parent_folder_name = clean_parts[-2]
            
            # 直接在 target_folder_id 下面搜尋 deepest_folder_name 
            search_res = self.remnote.search(deepest_folder_name, parent_id=target_folder_id)
            results = []
            if isinstance(search_res, dict):
                results = search_res.get("results", [])
            elif isinstance(search_res, list):
                results = search_res
                
            matched_id = None
            matched_parent_id = None
            
            for res in results:
                title = res.get("title") or res.get("headline") or ""
                parent_title = res.get("parentTitle") or ""
                # 去除前後空格並轉小寫比對
                if title.strip().lower() == deepest_folder_name.lower() and parent_title.strip().lower() == parent_folder_name.lower():
                    matched_id = res.get("remId") or res.get("_id")
                    matched_parent_id = res.get("parentRemId")
                    break
            
            if matched_id:
                # 匹配成功！將此路徑與父路徑同時納入快取中，直接掠過搜尋路徑
                self._path_id_cache[full_path_key] = matched_id
                self.remnote.set_rem_title(matched_id, deepest_folder_name)
                
                parent_path_key = " > ".join([p.lower() for p in clean_parts[:-1]])
                if matched_parent_id:
                    self._path_id_cache[parent_path_key] = matched_parent_id
                    self.remnote.set_rem_title(matched_parent_id, parent_folder_name)
                    
                print(f"  [Direct Match] Directly located '{deepest_folder_name}' -> '{matched_id}' (Parent: '{parent_folder_name}')")
                return matched_id

        # 2. Fallback: 按照 breadcrumb 乖乖逐層安全爬取與建立
        current_parent_id = target_folder_id
        current_path_parts = []
        
        for category_name in clean_parts:
            current_path_parts.append(category_name.lower())
            sub_path_key = " > ".join(current_path_parts)
            
            if sub_path_key in self._path_id_cache:
                current_parent_id = self._path_id_cache[sub_path_key]
                self.remnote.set_rem_title(current_parent_id, category_name)
                continue
                
            # 在當前層級下尋找此子分類
            search_res = self.remnote.search(category_name, parent_id=current_parent_id)
            results = []
            if isinstance(search_res, dict):
                results = search_res.get("results", [])
            elif isinstance(search_res, list):
                results = search_res
                
            rem_id = None
            if len(results) > 0:
                for res in results:
                    title = res.get("title") or res.get("headline") or ""
                    if title.strip().lower() == category_name.lower():
                        rem_id = res.get("remId") or res.get("_id")
                        break
            
            if rem_id:
                current_parent_id = rem_id
                self.remnote.set_rem_title(rem_id, category_name)
            else:
                # 建立此父分類節點
                create_res = self.remnote.create(category_name, parent_id=current_parent_id)
                # 乾跑模式下建立獨特的新建分類 ID，以便印出各自的 parent title
                new_id = create_res.get("remId") or create_res.get("_id")
                if not new_id or new_id == "dry-run-create-id":
                    new_id = f"dry-run-id-{category_name.strip().lower().replace(' ', '-')}"
                current_parent_id = new_id
                self.remnote.set_rem_title(new_id, category_name)
                
            # 寫入快取
            self._path_id_cache[sub_path_key] = current_parent_id
            
        return current_parent_id

    async def execute(self, target_folder_id: str, topic: str, source_notebook_id: str = "", remnote_notebook_id: str = "", query: str = "", gaps_file: Optional[str] = None):
        self.topic = topic
        print(f"=== Starting RAG Pipeline for topic: {topic} ===")
        print(f"Dry run: {self.dry_run}, Is Disease: {self.is_disease}")
        export_file = f"remnote_export_{topic}.md"
        new_knowledge_file = f"new_knowledge_{topic}.md"
        
        response_json = None
        if gaps_file and os.path.exists(gaps_file):
            print(f"\n[Phase 1] Bypassing NotebookLM query. Reading gaps tree from local file: {gaps_file}")
            with open(gaps_file, "r", encoding="utf-8") as f:
                text_content = f.read()
            response_json = json.dumps({"text": text_content, "citations": []})
        else:
            # --- Phase 0: Update Check and Export ---
            if os.path.exists(export_file):
                print(f"\n[Phase 0] Using cached RemNote KB file: {export_file}")
            else:
                print("\n[Phase 0] Checking if update is needed...")
                print(f"Exporting RemNote folder {target_folder_id}...")
                kb_markdown = self.remnote.read_markdown(target_folder_id)
                if kb_markdown:
                    with open(export_file, "w", encoding="utf-8") as f:
                        f.write(kb_markdown)
                    print(f"Successfully exported RemNote folder to {export_file} ({len(kb_markdown)} chars)")
                else:
                    print("Warning: Failed to export RemNote content. Falling back to simple placeholder.")
                    if not os.path.exists(export_file):
                        with open(export_file, "w", encoding="utf-8") as f:
                            f.write(f"RemNote Knowledge Base for {topic}\n")
            print("\n[Phase 0a] Querying external knowledge from Source Notebook...")
            if source_notebook_id and query:
                print(f"Asking notebook {source_notebook_id}: {query}")
                # Ask notebook LM without json format since we just want raw knowledge
                raw_answer = await self.notebooklm.ask(query, json_output=False, notebook_id=source_notebook_id)
                if raw_answer:
                    with open(new_knowledge_file, "w", encoding="utf-8") as f:
                        f.write(raw_answer)
                    print(f"Saved external knowledge to {new_knowledge_file}")
                else:
                    raise RuntimeError("Failed to query external knowledge from NotebookLM source notebook.")
            else:
                print("No source notebook or query provided. Skipping Phase 0a.")
                
            print("\n[Phase 0b] Deduplicating and Uploading sources to RemNote Notebook...")
            if remnote_notebook_id:
                # 1. List existing sources to find matches
                existing_sources = await self.notebooklm.list_sources(notebook_id=remnote_notebook_id)
                
                # Identify target filenames (which NotebookLM uses as titles)
                kb_filename = os.path.basename(export_file)
                new_knowledge_filename = os.path.basename(new_knowledge_file)
                
                # Find and delete matching sources to prevent duplicates
                for source in existing_sources:
                    title = source.get("title", "")
                    source_id = source.get("id") or source.get("sourceId")
                    if source_id and (title == kb_filename or title == new_knowledge_filename):
                        # For safe logging in Windows terminal
                        safe_title = title.encode('cp950', 'replace').decode('cp950')
                        print(f"Deleting duplicate source in RemNote Notebook: '{safe_title}' (ID: {source_id})")
                        await self.notebooklm.delete_source(source_id, notebook_id=remnote_notebook_id)
                
                # 2. Upload RemNote KB source
                if os.path.exists(export_file):
                    print(f"Uploading {export_file} as '{kb_filename}' to RemNote Notebook...")
                    kb_source_id = await self.notebooklm.add_source(export_file, kb_filename, notebook_id=remnote_notebook_id)
                    if kb_source_id:
                        print(f"Waiting for RemNote KB source indexing (ID: {kb_source_id})...")
                        await self.notebooklm.wait_source(kb_source_id, notebook_id=remnote_notebook_id)
                    else:
                        print("Warning: Could not automatically upload RemNote KB to RemNote NotebookLM.")
                
                # 3. Upload new knowledge source
                if os.path.exists(new_knowledge_file):
                    print(f"Uploading {new_knowledge_file} as '{new_knowledge_filename}' to RemNote Notebook...")
                    new_knowledge_source_id = await self.notebooklm.add_source(new_knowledge_file, new_knowledge_filename, notebook_id=remnote_notebook_id)
                    if new_knowledge_source_id:
                        print(f"Waiting for new knowledge source indexing (ID: {new_knowledge_source_id})...")
                        await self.notebooklm.wait_source(new_knowledge_source_id, notebook_id=remnote_notebook_id)
                    else:
                        print("Warning: Could not automatically upload new knowledge to RemNote NotebookLM.")
                else:
                    print(f"Warning: {new_knowledge_file} missing, skipping upload.")
            else:
                print("No RemNote notebook specified. Skipping Phase 0b.")

            # --- Phase 1: Query Gaps ---
            print("\n[Phase 1] Querying RemNote NotebookLM for gaps...")
            kb_filename = os.path.basename(export_file)
            new_knowledge_filename = os.path.basename(new_knowledge_file)
            prompt = f"""Based on the existing '{kb_filename}' source, compare it against the new information provided in the source titled '{new_knowledge_filename}'.
Identify knowledge gaps and items needing updates.

Generate a SINGLE hierarchical markdown list representing the merged knowledge tree.
For each fact or note, you MUST prefix the item with '(create)' or '(update)' respectively, and format it using RemNote Flashcard syntax rules:
1. Concept/Descriptor: Use ':>' (e.g., 'Normal IOP:>10~22 mmHg')
2. Definition: Use '::' (e.g., 'Applanation tonometry::gold standard')
3. Cloze Deletion: Use '{{{{keyword}}}}' for critical numbers, percentages, or terms.
4. If it's a new fact, prefix with '(create)'
5. If it's an update to an existing item, prefix with '(update)'

When listing gaps, you must construct the hierarchical path by 'grafting' (appending) the new facts under the existing categories found in '{kb_filename}'. Do not create new top-level categories if they can logically fit under the existing ones. Crucially, when constructing this hierarchical path, you MUST NOT omit or skip any existing parent/category names from '{kb_filename}'. Every single level of the existing hierarchy must be fully preserved and listed step-by-step; otherwise, automated path matching will fail.

Example output format:
- Herpes Zoster Ophthalmicus (HZO)
  - Acute disease
    - Clinical course
      - (create) Zoster Sine Herpete::In some cases, patients can experience HZO and dermatomal pain without ever developing the classic vesicular rash
  - Treatment
    - (update) Standard treatment:>Valacyclovir 1g TID for 7~10 days
"""
            response_json = await self.notebooklm.ask(prompt, json_output=True, notebook_id=remnote_notebook_id)
            if not response_json:
                raise RuntimeError("Failed to get a response from NotebookLM. Connection failed or response is empty.")
            
        gap_items, update_items = parse_gap_response(response_json)
        print(f"Found {len(gap_items)} gap items and {len(update_items)} update items.")
        
        # --- Phase 2: ID Resolution ---
        print("\n[Phase 2] Resolving RemNote IDs...")
        
        # Load local export file to cache and pre-filter searches
        kb_content = ""
        if os.path.exists(export_file):
            with open(export_file, "r", encoding="utf-8") as f:
                kb_content = f.read().lower()
                
        resolved_actions = []
        
        # Process Gaps
        if self.is_disease:
            for item in gap_items:
                canonical_slot = resolve_slot(item.term)
                # Ensure safe printing for Windows cp950 console
                safe_term = item.term.encode('cp950', 'replace').decode('cp950')
                safe_slot = canonical_slot.encode('cp950', 'replace').decode('cp950')
                print(f"  [Slot Match] Normalized '{safe_term}' -> '{safe_slot}'")
                item.term = canonical_slot
                
        for item in gap_items:
            search_term = item.term
            clean_term = get_clean_search_term(search_term) or search_term
            
            # Cache pre-filtering logic: Gaps not present in the local Markdown export bypass API search
            exists_locally = False
            if kb_content:
                term_lower = clean_term.lower()
                pattern = rf"(?:^|\n)\s*[-*]?\s*(?:\*\*)?{re.escape(term_lower)}(?:\*\*)?(?:\s*::|\s*$)"
                if re.search(pattern, kb_content, re.IGNORECASE):
                    exists_locally = True
            
            rem_id = None
            if exists_locally:
                search_res = self.remnote.search(clean_term, parent_id=target_folder_id)
                if isinstance(search_res, list) and len(search_res) > 0:
                    rem_id = search_res[0].get("remId") or search_res[0].get("_id")
            
            action = "UPDATE" if rem_id else "CREATE"
            resolved_actions.append({
                "action": action,
                "term": item.term,
                "rem_id": rem_id,
                "content": item.content,
                "breadcrumb": item.breadcrumb,
                "breadcrumb_parts": item.breadcrumb_parts
            })
            
        # Process Updates
        for item in update_items:
            search_term = item.existing_term
            if self.is_disease:
                search_term = resolve_slot(item.existing_term)
                
            clean_term = get_clean_search_term(search_term) or search_term
            search_res = self.remnote.search(clean_term, parent_id=target_folder_id)
            rem_id = None
            if isinstance(search_res, list) and len(search_res) > 0:
                rem_id = search_res[0].get("remId") or search_res[0].get("_id")
                
            resolved_actions.append({
                "action": "UPDATE" if rem_id else "CREATE",
                "term": item.existing_term,
                "rem_id": rem_id,
                "content": item.new_content,
                "breadcrumb": "",
                "breadcrumb_parts": []
            })
            
        # --- Phase 3: NLI Check ---
        print("\n[Phase 3] Skipping NLI validation as per user request.")
        
        # --- Phase 4: Write to RemNote ---
        print("\n[Phase 4] Writing to RemNote...")
        for action in resolved_actions:
            if action["action"] == "CREATE":
                print(f"Creating: {action['term']}")
                # Resolve the deepest parent remId from breadcrumb parts recursively
                parent_id = await self._resolve_or_create_parent_path(action.get("breadcrumb_parts", []), target_folder_id)
                self.remnote.create(action["content"], parent_id=parent_id)
            elif action["action"] == "UPDATE":
                if action["rem_id"]:
                    print(f"Updating {action['rem_id']} with: {action['content']}")
                    self.remnote.update(action["rem_id"], action["content"])
                else:
                    print(f"Warning: UPDATE requested for {action['term']} but no Rem ID found. Skipping.")
                    
        print("\n=== RAG Pipeline execution finished ===")

