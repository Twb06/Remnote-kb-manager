"""
smart_logic_v5.py - All-in-one knowledge pipeline for NotebookLM → RemNote.

Pipeline:
  A. Lookup terms in SKILL.md top-level map
  B. Search unmapped terms via remnote-cli
  B2. Hierarchical locate: route to best parent branch then read children to find term
  C. Read context tree (single depth-6 call, cached)
  D. Parent/Sibling mapping for missing terms
  E. Embedding-based knowledge intersection (MATCH / NEW / AMBIGUOUS)

Usage:
  python smart_logic_v5.py \
    --skill-map ".agents/skills/remnote-kb-navigation/SKILL.md" \
    --overview-file ".agents/tmp/overview.md" \
    --content-file ".agents/tmp/answer.md"
"""

import subprocess
import json
import sys
import re
import argparse
import os
from typing import Optional

# Fix Windows console encoding (cp950/cp1252 can't print Unicode)
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# ── CLI wrapper (carried from v4) ──────────────────────────────────────────

CLI_CMD = ["npx", "remnote-cli", "--json"]

def run_cli(command: list[str]) -> dict:
    """Execution wrapper with robust encoding for Windows."""
    full_cmd = CLI_CMD + command
    try:
        result = subprocess.run(
            full_cmd, capture_output=True, text=True,
            shell=True, encoding='utf-8', errors='replace'
        )
        if result.returncode != 0:
            return {"error": result.stderr.strip() or f"CLI error code {result.returncode}"}
        output = result.stdout.strip()
        json_match = re.search(r'(\{.*\}|\[.*\])', output, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))
        return {"error": "No JSON found in output", "raw": output}
    except Exception as e:
        return {"error": str(e)}


def normalize(text: str) -> str:
    """Lowercase, strip non-alphanumeric for fuzzy matching."""
    return re.sub(r'\W+', '', str(text)).lower()


# ── Step A: Map Lookup (supports SKILL.md and kb_map.json) ─────────────────

MAP_PATTERN = re.compile(r'^(\s*)-\s*`([^`]+)`\s*-\s*`([^`]+)`(?:\s*-\s*(.*))?$')


def _parse_kb_map_json(kb_map_path: str) -> list[dict]:
    """Parse kb_map.json into flat entry list with indent, title, remId, hint (=summary)."""
    entries = []
    try:
        with open(kb_map_path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"[WARN] Failed to read kb_map.json at {kb_map_path}: {e}")
        return entries

    def flatten(nodes, indent=0):
        for node in nodes:
            rid = node.get("remId", "")
            title = (node.get("title") or "").strip()
            summary = node.get("summary", "")
            if title and rid:
                entries.append({
                    "indent": indent,
                    "title": title,
                    "remId": rid,
                    "hint": summary,  # 'hint' kept for hierarchical_locate compatibility
                })
            flatten(node.get("children", []), indent + 2)

    flatten(data.get("branches", []))
    return entries


def parse_skill_map(skill_path: str) -> list[dict]:
    """Parse map file into structured entries with indent, title, remId, hint.

    Accepts either:
      - kb_map.json  (preferred, structured format)
      - SKILL.md     (legacy regex format, backward compatible)
    """
    if skill_path.endswith(".json"):
        return _parse_kb_map_json(skill_path)

    # Legacy SKILL.md parsing
    entries = []
    if not os.path.exists(skill_path):
        print(f"[WARN] Map file not found at {skill_path}")
        return entries

    with open(skill_path, 'r', encoding='utf-8') as f:
        map_lines = f.readlines()

    for line in map_lines:
        m = MAP_PATTERN.match(line)
        if m:
            entries.append({
                "indent": len(m.group(1)),
                "title": m.group(2),
                "remId": m.group(3),
                "hint": (m.group(4) or "").strip()
            })
    return entries


def lookup_skill_map(skill_path: str, terms: list[str]) -> tuple[dict[str, str], list[dict]]:
    """
    Grep the map (kb_map.json or SKILL.md) for matching terms.
    Returns (found: {term: remId}, map_entries: list[dict]).
    """
    map_entries = parse_skill_map(skill_path)
    found = {}

    for term in terms:
        term_norm = normalize(term)
        if len(term_norm) < 2:
            continue
        best_score = 0
        best_entry = None
        for entry in map_entries:
            entry_norm = normalize(entry["title"])
            if term_norm in entry_norm or entry_norm in term_norm:
                score = len(term_norm) / max(1, len(entry_norm))
                # Bonus for exact match
                if term_norm == entry_norm:
                    score += 10
                if score > best_score:
                    best_score = score
                    best_entry = entry
        if best_entry and best_score >= 0.5:
            found[term] = best_entry["remId"]
            print(f"  [MAP] '{term}' → {best_entry['title']} ({best_entry['remId']}) score={best_score:.2f}")

    return found, map_entries


# ── Step B: Normalized Search via CLI ──────────────────────────────────────

def to_title_case(text: str) -> str:
    """Convert to Title Case while preserving acronyms/numbers (e.g. 24-2)."""
    words = text.split()
    return " ".join([w[0].upper() + w[1:] if len(w) > 0 else w for w in words])

def search_unmapped(terms: list[str], already_mapped: dict[str, str]) -> dict[str, str]:
    """
    Search unmapped terms in RemNote.
    Strategy:
    1. Convert term to Title Case (user convention).
    2. Run raw search via CLI.
    3. Score hits based on raw title overlap (no normalization).
    """
    found = {}
    for term in terms:
        if term in already_mapped:
            continue

        # 1. Format to Title Case and generate sub-queries
        term_title_case = to_title_case(term)
        queries = [term_title_case]
        parts = re.split(r'[\s\-_]+', term)
        for p in parts:
            p = p.strip()
            if len(p) > 2:
                ptc = to_title_case(p)
                if ptc not in queries:
                    queries.append(ptc)

        print(f"  [SEARCH] Multi-query (Title Case) for '{term}': {queries}")

        # 2. Raw Search with aggregation
        all_hits = []
        for q in queries:
            result = run_cli(["search", q, "--limit", "50"])
            hits = result if isinstance(result, list) else result.get("results", [])
            all_hits.extend(hits)

        if not all_hits:
            print(f"    [MISS] No hits for queries: {queries}")
            continue

        best_score = 0
        best_hit = None
        seen_ids = set()

        for hit in all_hits:
            if not isinstance(hit, dict):
                continue
            rid = hit.get("remId") or hit.get("_id")
            if not rid or rid in seen_ids:
                continue
            seen_ids.add(rid)

            hit_title = (hit.get("title") or hit.get("text", "")).strip()
            if not hit_title: continue

            # Raw Scoring (Case Sensitive or Case Insensitive based on user preference)
            # User said "topic的話所有單字字首會大寫"
            score = 0
            if term_title_case == hit_title:
                score = 10.0
            elif term_title_case in hit_title:
                score = len(term_title_case) / len(hit_title)
            elif hit_title in term_title_case:
                score = (len(hit_title) / len(term_title_case))
                # Penalty for generic short hits
                if hit_title.lower() in ["pattern", "test", "management", "treatment"]:
                    score *= 0.3

            if score > best_score:
                best_score = score
                best_hit = hit

        # Threshold 0.6 for quality Title Case matches
        if best_hit and best_score >= 0.6:
            rid = best_hit.get("remId") or best_hit.get("_id")
            found[term] = rid
            print(f"    [FOUND] '{term}' → '{best_hit.get('title', '')}' ({rid}) score={best_score:.2f}")
        else:
            best_title = best_hit.get('title', 'None') if best_hit else 'None'
            print(f"    [MISS] No high-quality match for '{term}' (best hit: '{best_title}', score: {best_score:.2f})")

    return found


# ── Step B2: Hierarchical Locate (map-guided branch read) ──────────────────

def hierarchical_locate(
    terms: list[str],
    already_found: dict[str, str],
    map_entries: list[dict]
) -> dict[str, str]:
    """
    For terms that Step A (map grep) and Step B (search) both missed,
    use the map as a routing table:
      1. Score each top-level branch (indent=0) by keyword relevance
         using title + hint fields.
      2. Read the best candidate branch at depth 2 to discover children.
      3. Match term against discovered children titles.

    This costs ~1 CLI read per missing term group (batched by branch),
    far cheaper than an agent reading the entire KB.
    """
    found = {}
    missing = [t for t in terms if t not in already_found]
    if not missing:
        return found

    # Build branch index: top-level entries (indent=0) with their sub-entries
    branches = []
    for i, entry in enumerate(map_entries):
        if entry["indent"] == 0:
            # Collect all child hints/titles for this branch
            child_words = set()
            for j in range(i + 1, len(map_entries)):
                if map_entries[j]["indent"] == 0:
                    break
                child_words.update(
                    normalize(w) for w in map_entries[j]["title"].split() if len(w) > 2
                )
                if map_entries[j]["hint"]:
                    child_words.update(
                        normalize(w) for w in map_entries[j]["hint"].split() if len(w) > 1
                    )
            branches.append({
                "remId": entry["remId"],
                "title": entry["title"],
                "hint": entry["hint"],
                "child_words": child_words
            })

    # Group missing terms by best-matching branch to minimize reads
    branch_to_terms: dict[str, list[str]] = {}
    for term in missing:
        term_words = set(normalize(w) for w in re.split(r'[\s\-_]+', term) if len(w) > 2)
        term_norm = normalize(term)

        best_branch = None
        best_overlap = 0
        for branch in branches:
            branch_all_words = (
                set(normalize(w) for w in branch["title"].split() if len(w) > 2)
                | set(normalize(w) for w in branch["hint"].split() if len(w) > 1)
                | branch["child_words"]
            )
            # Score by word overlap + substring containment bonus
            overlap = len(term_words & branch_all_words)
            for bw in branch_all_words:
                if term_norm in bw or bw in term_norm:
                    overlap += 0.5
            if overlap > best_overlap:
                best_overlap = overlap
                best_branch = branch

        if best_branch and best_overlap > 0:
            bid = best_branch["remId"]
            if bid not in branch_to_terms:
                branch_to_terms[bid] = []
            branch_to_terms[bid].append(term)

    if not branch_to_terms:
        print("  [B2] No candidate branches found for missing terms")
        return found

    # Read each candidate branch at depth 2 and match
    read_cache: dict[str, list[dict]] = {}
    for branch_id, target_terms in branch_to_terms.items():
        branch_name = next((b["title"] for b in branches if b["remId"] == branch_id), branch_id)
        print(f"  [B2] Reading branch '{branch_name}' ({branch_id}) for terms: {target_terms}")

        if branch_id not in read_cache:
            data = run_cli(["read", branch_id, "--depth", "2", "--child-limit", "200"])
            if isinstance(data, dict) and "error" not in data:
                children = _flatten_children(data, max_depth=2)
                read_cache[branch_id] = children
            else:
                print(f"    [ERROR] Failed to read branch: {data.get('error', 'unknown')}")
                read_cache[branch_id] = []

        children = read_cache[branch_id]
        for term in target_terms:
            term_tc = to_title_case(term)
            term_norm = normalize(term)
            best_child = None
            best_score = 0

            for child in children:
                child_title = child.get("title", "")
                child_norm = normalize(child_title)
                if not child_norm:
                    continue

                score = 0
                if term_norm == child_norm:
                    score = 10.0
                elif term_norm in child_norm:
                    score = len(term_norm) / len(child_norm)
                elif child_norm in term_norm:
                    score = len(child_norm) / len(term_norm)
                # Title Case exact match bonus
                if term_tc == child_title:
                    score += 5.0

                if score > best_score:
                    best_score = score
                    best_child = child

            if best_child and best_score >= 0.5:
                rid = best_child.get("remId") or best_child.get("_id")
                if rid:
                    found[term] = rid
                    print(f"    [B2-FOUND] '{term}' → '{best_child['title']}' ({rid}) score={best_score:.2f}")
            else:
                print(f"    [B2-MISS] '{term}' not found in branch '{branch_name}'")

    return found


def _flatten_children(node: dict, max_depth: int, current_depth: int = 0) -> list[dict]:
    """Flatten a tree node into a list of {title, remId} entries up to max_depth."""
    results = []
    if not isinstance(node, dict):
        return results

    title = node.get("title", "").strip()
    rid = node.get("remId") or node.get("_id", "")
    if title and rid and current_depth > 0:  # skip root itself
        results.append({"title": title, "remId": str(rid)})

    if current_depth < max_depth:
        for child in node.get("children", []):
            results.extend(_flatten_children(child, max_depth, current_depth + 1))

    return results


# ── Step C: Context Read (single call, cached) ────────────────────────────

def read_context_tree(rem_id: str, timeout_seconds: int = 60) -> dict:
    """Read a single Rem at depth 6 with structured content. Cache-friendly."""
    print(f"  [READ] Fetching tree for {rem_id} (depth 6, timeout {timeout_seconds}s)...")
    data = run_cli(["read", rem_id, "--depth", "6", "--include-content", "structured"])
    if isinstance(data, dict) and "error" in data:
        print(f"    [ERROR] {data['error']}")
    return data


# ── Step D: Parent/Sibling Mapping ─────────────────────────────────────────

def map_destinations(
    terms: list[str],
    term_to_id: dict[str, str],
    context_trees: dict[str, dict],
    topic: Optional[str] = None
) -> dict[str, dict]:
    """
    For every term, determine the action target:
      - Found terms → action target is the term's own remId (append under it)
      - Missing terms → infer parent (Topic found? Use Topic. Sibling found? Use Sibling's parent.)

    Returns {term: {"remId": ..., "action": "UPDATE" | "CREATE", "parentRemId": ...}}
    """
    mapping = {}

    # Topic ID
    topic_id = term_to_id.get(topic) if topic else None

    # Collect parentRemIds from found terms' context trees
    found_parents = {}
    for term, rid in term_to_id.items():
        for tree_root_id, tree in context_trees.items():
            node = get_node_by_id(tree, rid)
            if node:
                pid = node.get("parentRemId") or node.get("parentId")
                if pid:
                    found_parents[term] = pid
                break

    for term in terms:
        if term in term_to_id:
            mapping[term] = {
                "remId": term_to_id[term],
                "action": "UPDATE",
                "parentRemId": found_parents.get(term)
            }
        else:
            # Infer:
            # 1. Use found Topic as parent if it's a subtopic
            # 2. Use a found sibling's parentRemId
            inferred_parent = None
            if topic_id and term != topic:
                inferred_parent = topic_id
            elif found_parents:
                # Use the first available parent from a sibling
                inferred_parent = next(iter(found_parents.values()))

            mapping[term] = {
                "remId": None,
                "action": "CREATE",
                "parentRemId": inferred_parent
            }
            print(f"  [MAP] '{term}' → CREATE under parent {inferred_parent or 'UNKNOWN'}")

    return mapping


def get_node_by_id(node: dict, target_id: str) -> Optional[dict]:
    """Recursively find a node by remId in a tree."""
    if not isinstance(node, dict):
        return None
    if str(node.get("remId")) == str(target_id) or str(node.get("_id")) == str(target_id):
        return node
    kids = node.get("children", []) or node.get("contentStructured", [])
    for k in kids:
        res = get_node_by_id(k, target_id)
        if res:
            return res
    return None


# ── Step E: Embedding-based Knowledge Intersection ─────────────────────────

def extract_knowledge_lines(node: dict, depth: int = 0) -> list[str]:
    """Flatten a structured tree into individual knowledge lines."""
    lines = []
    if not isinstance(node, dict):
        return lines

    title = node.get("title", "").strip()
    content = node.get("content", "").strip()

    if title:
        lines.append(title)
    if content:
        # Split multi-line content
        for cl in content.split('\n'):
            cl = cl.strip()
            if cl:
                lines.append(cl)

    kids = node.get("children", []) or node.get("contentStructured", [])
    for k in kids:
        lines.extend(extract_knowledge_lines(k, depth + 1))
    return lines


def compare_knowledge(
    existing_lines: list[str],
    new_md_lines: list[str],
    match_threshold: float = 0.80,
    new_threshold: float = 0.30
) -> dict:
    """
    Use sentence embeddings to classify each new line as MATCH, NEW, or AMBIGUOUS.

    Returns:
      {
        "match": [{"line": ..., "similarity": ..., "matched_to": ...}],
        "new": [{"line": ..., "best_similarity": ...}],
        "ambiguous": [{"line": ..., "best_similarity": ..., "closest_match": ...}]
      }
    """
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np

    if not new_md_lines:
        return {"match": [], "new": [], "ambiguous": []}

    if not existing_lines:
        # Nothing to compare against — everything is new
        return {
            "match": [],
            "new": [{"line": line, "best_similarity": 0.0} for line in new_md_lines],
            "ambiguous": []
        }

    print(f"  [EMBED] Loading model...")
    model = SentenceTransformer('all-MiniLM-L6-v2')

    print(f"  [EMBED] Encoding {len(existing_lines)} existing + {len(new_md_lines)} new lines...")
    existing_vecs = model.encode(existing_lines, show_progress_bar=False)
    new_vecs = model.encode(new_md_lines, show_progress_bar=False)

    # Compute pairwise cosine similarity: shape (len(new), len(existing))
    sim_matrix = cosine_similarity(new_vecs, existing_vecs)

    result = {"match": [], "new": [], "ambiguous": []}

    for i, new_line in enumerate(new_md_lines):
        best_idx = int(np.argmax(sim_matrix[i]))
        best_sim = float(sim_matrix[i][best_idx])
        closest = existing_lines[best_idx]

        if best_sim >= match_threshold:
            result["match"].append({
                "line": new_line,
                "similarity": round(best_sim, 3),
                "matched_to": closest
            })
        elif best_sim < new_threshold:
            result["new"].append({
                "line": new_line,
                "best_similarity": round(best_sim, 3)
            })
        else:
            result["ambiguous"].append({
                "line": new_line,
                "best_similarity": round(best_sim, 3),
                "closest_match": closest
            })

    return result


# ── Markdown Parsing ───────────────────────────────────────────────────────

def parse_overview(overview_text: str) -> dict:
    """
    Parse ## overview section into topic + subtopics.
    Returns {"topic": "Main Topic", "subtopics": ["Sub1", "Sub2", ...]}
    """
    lines = overview_text.strip().split('\n')
    topic = None
    subtopics = []

    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        # First non-header bullet = topic
        clean = re.sub(r'^[-*]\s*', '', line).strip()
        clean = clean.replace('**', '').strip()
        if not clean:
            continue
        if topic is None:
            topic = clean
        else:
            subtopics.append(clean)

    return {"topic": topic or "", "subtopics": subtopics}


def parse_md_to_sections(md: str) -> dict[str, dict]:
    """Split markdown into sections by top-level bullet headers."""
    sections = {}
    lines = md.strip().split('\n')
    current_topic = None
    for line in lines:
        match = re.match(r'^[-*]\s+\**([^*:\n]+)\**', line)
        if match:
            current_topic = match.group(1).split('::')[0].strip()
            sections[current_topic] = {"header": line, "body": []}
        elif current_topic:
            sections[current_topic]["body"].append(line)
    return sections


# ── Main Pipeline ──────────────────────────────────────────────────────────

def run_pipeline(skill_map_path: str, overview_text: str, content_text: str) -> str:
    """
    Execute the full pipeline:
    A → B → B2 → C → D → E → output JSON.
    """
    # Parse overview
    overview = parse_overview(overview_text)
    topic = overview["topic"]
    subtopics = overview["subtopics"]
    all_terms = [topic] + subtopics if topic else subtopics

    print(f"{'='*60}")
    print(f"Pipeline start: topic='{topic}', subtopics={subtopics}")
    print(f"{'='*60}")

    if not all_terms:
        return json.dumps({"error": "No terms found in overview"}, indent=2)

    # ── Step A: Map Lookup ──
    print(f"\n[Step A] Skill map lookup...")
    map_results, map_entries = lookup_skill_map(skill_map_path, all_terms)

    # ── Step B: Search unmapped ──
    print(f"\n[Step B] Searching unmapped terms...")
    search_results = search_unmapped(all_terms, map_results)

    # Merge A + B
    term_to_id = {**map_results, **search_results}

    # ── Step B2: Hierarchical Locate (fallback for still-missing terms) ──
    still_missing = [t for t in all_terms if t not in term_to_id]
    if still_missing:
        print(f"\n[Step B2] Hierarchical locate for {len(still_missing)} missing terms...")
        b2_results = hierarchical_locate(all_terms, term_to_id, map_entries)
        term_to_id.update(b2_results)

    missing_terms = [t for t in all_terms if t not in term_to_id]

    print(f"\n  Summary: {len(term_to_id)} mapped, {len(missing_terms)} missing")
    for t, rid in term_to_id.items():
        print(f"    ✓ '{t}' → {rid}")
    for t in missing_terms:
        print(f"    ✗ '{t}' → not found")

    # ── Step C: Read context trees ──
    print(f"\n[Step C] Reading context trees...")
    context_trees = {}

    # Strategy: read the topic first (if found). Subtopics are likely under it.
    # If topic not found but subtopics are, read the first subtopic's parent.
    read_targets = set()
    if topic and topic in term_to_id:
        read_targets.add(term_to_id[topic])
    else:
        # Read the first found subtopic to get the parent tree
        for st in subtopics:
            if st in term_to_id:
                read_targets.add(term_to_id[st])
                break  # One read is enough to discover siblings

    for rid in read_targets:
        tree = read_context_tree(rid)
        if isinstance(tree, dict) and "error" not in tree:
            context_trees[rid] = tree

    # ── Step D: Parent/Sibling Mapping ──
    print(f"\n[Step D] Mapping destinations...")
    destination_map = map_destinations(all_terms, term_to_id, context_trees, topic=topic)

    # ── Step E: Embedding Intersection ──
    print(f"\n[Step E] Knowledge intersection via embeddings...")
    content_sections = parse_md_to_sections(content_text)

    final_output = {
        "auto_actions": [],
        "ambiguous": [],
        "skipped": []
    }

    # Pre-calculate normalized section keys
    norm_content_sections = {normalize(k): v for k, v in content_sections.items()}

    for term in all_terms:
        term_norm = normalize(term)
        dest = destination_map.get(term, {})
        # Match using normalized term
        section = norm_content_sections.get(term_norm)

        # Fallback: fuzzy search for the key in sections if not exact normalized match
        if not section:
            for k_norm, v in norm_content_sections.items():
                if term_norm in k_norm or k_norm in term_norm:
                    section = v
                    print(f"  [MATCH] Fuzzy matched section header '{v['header']}' for term '{term}'")
                    break

        if not section:
            print(f"  [SKIP] No content section found for '{term}' (norm: '{term_norm}')")
            continue

        new_lines = [l.strip() for l in section["body"] if l.strip()]

        if dest["action"] == "UPDATE" and dest["remId"]:
            # Extract existing knowledge from cached tree
            existing_lines = []
            for tree in context_trees.values():
                node = get_node_by_id(tree, dest["remId"])
                if node:
                    existing_lines = extract_knowledge_lines(node)
                    break

            if existing_lines:
                comparison = compare_knowledge(existing_lines, new_lines)

                if comparison["new"]:
                    final_output["auto_actions"].append({
                        "action": "UPDATE",
                        "remId": dest["remId"],
                        "title": term,
                        "content": "\n".join([item["line"] for item in comparison["new"]])
                    })
                if comparison["ambiguous"]:
                    final_output["ambiguous"].append({
                        "term": term,
                        "remId": dest["remId"],
                        "items": comparison["ambiguous"]
                    })
                if comparison["match"]:
                    final_output["skipped"].append({
                        "term": term,
                        "count": len(comparison["match"]),
                        "reason": "Already exists (embedding match)"
                    })
            else:
                # No existing content to compare — treat all as new
                final_output["auto_actions"].append({
                    "action": "UPDATE",
                    "remId": dest["remId"],
                    "title": term,
                    "content": "\n".join(new_lines)
                })

        elif dest["action"] == "CREATE":
            parent_id = dest.get("parentRemId")
            full_content = section["header"] + "\n" + "\n".join(section["body"])
            final_output["auto_actions"].append({
                "action": "CREATE",
                "parentRemId": parent_id,
                "title": term,
                "content": full_content
            })

    # Print summary
    print(f"\n{'='*60}")
    print(f"Pipeline complete:")
    print(f"  Auto actions: {len(final_output['auto_actions'])}")
    print(f"  Ambiguous (needs agent review): {len(final_output['ambiguous'])}")
    print(f"  Skipped (duplicates): {len(final_output['skipped'])}")
    print(f"{'='*60}\n")

    return json.dumps(final_output, indent=2, ensure_ascii=False)


# ── CLI Entry Point ────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Smart knowledge pipeline v5")
    parser.add_argument("--skill-map", required=True, help="Path to SKILL.md")
    parser.add_argument("--overview-file", required=True, help="Path to overview markdown")
    parser.add_argument("--content-file", required=True, help="Path to answer markdown")
    parser.add_argument("--timeout", type=int, default=60, help="CLI timeout in seconds")
    args = parser.parse_args()

    with open(args.overview_file, 'r', encoding='utf-8-sig') as f:
        overview = f.read()
    with open(args.content_file, 'r', encoding='utf-8-sig') as f:
        content = f.read()

    print(run_pipeline(args.skill_map, overview, content))
