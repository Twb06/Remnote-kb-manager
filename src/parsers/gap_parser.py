"""
Gap Parser - Phase 1: NotebookLM JSON Response Parser

Responsible for parsing the structured output from NotebookLM:
- Extracts gaps and updates from a single hierarchical tree using (create) and (update) tags.
- Reuses build_ast_tree and flatten_with_breadcrumbs from ast_parser.
"""

from typing import List, Dict, Optional
from dataclasses import dataclass, field
import json
import re

from src.parsers.ast_parser import build_ast_tree, flatten_with_breadcrumbs

@dataclass
class GapItem:
    """NotebookLM identified knowledge gaps."""
    term: str
    content: str
    breadcrumb: str
    breadcrumb_parts: list
    source_references: list = field(default_factory=list)

@dataclass
class UpdateItem:
    """NotebookLM identified items needing updates."""
    existing_term: str
    update_reason: str
    new_content: str
    source_references: list = field(default_factory=list)

def parse_gap_response(json_text: str) -> tuple[List[GapItem], List[UpdateItem]]:
    """
    Parses NotebookLM's JSON response to extract gaps and updates using (create)/(update) tags.
    """
    # Attempt to load json directly if wrapped in markdown
    json_text = json_text.strip()
    match = re.search(r'```(?:json)?\s*(\{.*\}|\[.*\])\s*```', json_text, re.DOTALL)
    if match:
        json_text = match.group(1)
    
    try:
        data = json.loads(json_text)
        text_content = data.get("text", "")
    except json.JSONDecodeError:
        text_content = json_text
        
    lines = []
    for line in text_content.splitlines():
        stripped = line.strip()
        # Skip empty lines, lone periods, and section headers
        if not stripped or stripped == "." or stripped.lower() in ["gaps", "updates", "# gaps", "# updates", "## gaps", "## updates"]:
            continue
        lines.append(line)
        
    gap_items = []
    update_items = []
    
    if lines:
        root_nodes = build_ast_tree(lines)
        flat_items = flatten_with_breadcrumbs(root_nodes, prefix_format="plain")
        for item in flat_items:
            text = item["text"]
            text_lower = text.lower()
            
            # Check if this leaf/fact node is marked with (create) or (update)
            if "(create)" in text_lower or "(update)" in text_lower:
                is_create = "(create)" in text_lower
                
                # Strip tag prefix from the term, case-insensitive
                clean_term = re.sub(r'\((?:create|update)\)\s*', '', text, flags=re.IGNORECASE).strip()
                
                # Strip tag prefix from the breadcrumb components
                parent_parts = [
                    re.sub(r'\((?:create|update)\)\s*', '', p, flags=re.IGNORECASE).strip()
                    for p in item["breadcrumb_parts"][:-1]
                ]
                clean_breadcrumb = " > ".join(parent_parts)
                
                if is_create:
                    gap_items.append(GapItem(
                        term=clean_term,
                        content=clean_term,
                        breadcrumb=f"[{clean_breadcrumb}]" if clean_breadcrumb else "",
                        breadcrumb_parts=parent_parts
                    ))
                else:
                    # Split existing_term and new_content on first ::, :>, or :
                    parts = re.split(r'::|:>|:', clean_term, maxsplit=1)
                    existing_term = parts[0].strip()
                    
                    # Remove surrounding bold markers ** standard in LLM markdown
                    existing_term = re.sub(r'\*\*+', '', existing_term).strip()
                    
                    new_content = parts[1].strip() if len(parts) > 1 else clean_term
                    
                    update_items.append(UpdateItem(
                        existing_term=existing_term,
                        update_reason="Need update based on new knowledge",
                        new_content=new_content
                    ))
                    
    return gap_items, update_items
