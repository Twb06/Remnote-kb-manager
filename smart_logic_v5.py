"""
smart_logic_v5.py - All-in-one knowledge pipeline for NotebookLM → RemNote.

Pipeline:
  A. Lookup terms in kb_map.json top-level map (legacy SKILL.md supported)
  B. Search unmapped terms via remnote-cli
  B2. Hierarchical locate: route to best parent branch then read children to find term
  C. Read context tree (single depth-6 call, cached)
  D. Parent/Sibling mapping for missing terms
  E. Embedding-based knowledge intersection (MATCH / NEW / AMBIGUOUS)

Usage:
  python smart_logic_v5.py \
    --kb-map ".github/skills/remnote-kb-navigation/kb_map.json" \
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

# ═════════════════════════════════════════════════════════════════════════════
# Configuration Constants
# ═════════════════════════════════════════════════════════════════════════════

# ── Search & Matching Thresholds ────────────────────────────────────────────
SCORE_PERFECT_MATCH = 10.0          # Perfect title match base score
SCORE_EXACT_MATCH_BONUS = 10.0      # Bonus for exact normalized match
SCORE_TITLE_CASE_BONUS = 5.0        # Bonus for Title Case exact match

THRESHOLD_MAP_LOOKUP = 0.5          # Minimum score for kb_map lookup match
THRESHOLD_SEARCH_ACCEPT = 0.6       # Minimum score to accept search result
THRESHOLD_HIERARCHICAL = 0.5        # Minimum score for hierarchical locate match

# ── Scoring Weights ─────────────────────────────────────────────────────────
WEIGHT_ALIASES_EXIST = 2.0          # Boost when node has aliases
WEIGHT_TAGS_EXIST = 1.0             # Boost when node has tags
WEIGHT_SUBSTRING_OVERLAP = 0.5      # Bonus for substring containment in branch matching
PENALTY_GENERIC_TERMS = 0.3         # Penalty multiplier for generic short terms

# ── CLI Parameters ──────────────────────────────────────────────────────────
CLI_SEARCH_LIMIT = 50               # Max results per search query
CLI_BRANCH_DEPTH = 2                # Depth for branch reading in hierarchical locate
CLI_BRANCH_CHILD_LIMIT = 200        # Max children to read per branch
CLI_TREE_DEPTH = 6                  # Depth for full context tree reading
CLI_CROSS_VALIDATE_DEPTH = 2        # Depth for cross-validation branch reading

# ── Embedding Thresholds ────────────────────────────────────────────────────
EMBED_MATCH_THRESHOLD = 0.80        # Similarity threshold for MATCH classification
EMBED_NEW_THRESHOLD = 0.30          # Similarity threshold below which line is NEW

# ── Timeouts ────────────────────────────────────────────────────────────────
DEFAULT_TIMEOUT_SECONDS = 60        # Default CLI timeout in seconds

# ═════════════════════════════════════════════════════════════════════════════

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


# ── Step A: KB Map Lookup (kb_map.json primary, legacy SKILL.md supported) ──

MAP_PATTERN = re.compile(r'^(\s*)-\s*`([^`]+)`\s*-\s*`([^`]+)`(?:\s*-\s*(.*))?$')  # For legacy SKILL.md


def _parse_kb_map_json(kb_map_path: str) -> list[dict]:
    """Parse kb_map.json into flat entry list with indent, title, remId, summary."""
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
                    "summary": summary,  # 'summary' kept for hierarchical_locate compatibility
                })
            flatten(node.get("children", []), indent + 2)

    flatten(data.get("branches", []))
    return entries


def parse_kb_map(kb_map_path: str) -> list[dict]:
    """Parse KB map file into structured entries with indent, title, remId, summary.

    Accepts either:
      - kb_map.json  (primary format, recommended)
      - SKILL.md     (legacy format, backward compatible)
    """
    if kb_map_path.endswith(".json"):
        return _parse_kb_map_json(kb_map_path)

    # Legacy SKILL.md parsing
    entries = []
    if not os.path.exists(kb_map_path):
        print(f"[WARN] Map file not found at {kb_map_path}")
        return entries

    with open(kb_map_path, 'r', encoding='utf-8') as f:
        map_lines = f.readlines()

    for line in map_lines:
        m = MAP_PATTERN.match(line)
        if m:
            entries.append({
                "indent": len(m.group(1)),
                "title": m.group(2),
                "remId": m.group(3),
                "summary": (m.group(4) or "").strip()
            })
    return entries


def lookup_kb_map(kb_map_path: str, terms: list[str]) -> tuple[dict[str, str], list[dict]]:
    """
    Lookup terms in KB map (kb_map.json primary, legacy SKILL.md supported).
    Returns (found: {term: remId}, map_entries: list[dict]).
    """
    map_entries = parse_kb_map(kb_map_path)
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
                    score += SCORE_EXACT_MATCH_BONUS
                if score > best_score:
                    best_score = score
                    best_entry = entry
        if best_entry and best_score >= THRESHOLD_MAP_LOOKUP:
            found[term] = best_entry["remId"]
            print(f"  [MAP] '{term}' → {best_entry['title']} ({best_entry['remId']}) score={best_score:.2f}")

    return found, map_entries


# ── Step B: Normalized Search via CLI ──────────────────────────────────────

def to_title_case(text: str) -> str:
    """Convert to Title Case while preserving acronyms/numbers (e.g. 24-2)."""
    words = text.split()
    return " ".join([w[0].upper() + w[1:] if len(w) > 0 else w for w in words])


def calculate_enhanced_score(hit: dict, term: str, term_title_case: str, hit_title: str) -> float:
    """
    Enhanced scoring with:
    1. Aliases boost (complete match = 10.0, exists = +2)
    2. Tags boost (+1)
    3. System aliases exclusion (score = 0)

    Args:
        hit: The search result hit
        term: Original search term
        term_title_case: Title-cased search term
        hit_title: The title of the hit

    Returns:
        float: Enhanced score (0 = excluded, 10.0 = perfect match)
    """
    # ═══ EXCLUSION: System-generated Aliases nodes ═══
    parent_title = hit.get("parentTitle", "")
    parent_id = hit.get("parentRemId", "")

    if parent_title == "Aliases" or parent_id == "xOuCp1mEAK82ZbPEB":
        print(f"      [EXCLUDE] Skipping system alias node: {hit_title} (parent: {parent_title})")
        return 0.0

    # ═══ BASE SCORE: Title matching ═══
    base_score = 0.0

    if term_title_case == hit_title:
        base_score = SCORE_PERFECT_MATCH
    elif term_title_case in hit_title:
        base_score = len(term_title_case) / len(hit_title)
    elif hit_title in term_title_case:
        base_score = (len(hit_title) / len(term_title_case))
        # Penalty for generic short hits
        if hit_title.lower() in ["pattern", "test", "management", "treatment", "diagnosis"]:
            base_score *= PENALTY_GENERIC_TERMS

    # ═══ BOOST 1: Aliases ═══
    aliases = hit.get("aliases", [])
    if isinstance(aliases, list) and aliases:
        # Has aliases: boost points
        base_score += WEIGHT_ALIASES_EXIST

        # Check for complete match in aliases
        for alias in aliases:
            if isinstance(alias, str):
                if alias.lower() == term.lower() or alias.lower() == term_title_case.lower():
                    # Perfect alias match: maximum score
                    print(f"      [ALIAS-MATCH] Perfect match in aliases: {alias}")
                    return SCORE_PERFECT_MATCH

    # ═══ BOOST 2: Tags ═══
    tags = hit.get("tags", [])
    if isinstance(tags, list) and tags:
        # Has tags: boost point
        base_score += WEIGHT_TAGS_EXIST

    return base_score


def search_unmapped(terms: list[str], already_mapped: dict[str, str]) -> dict[str, tuple[str, list[dict]]]:
    """
    Search unmapped terms in RemNote with enhanced scoring.

    Returns: {term: (best_rem_id, top_5_candidates)}
             where top_5_candidates = [(score, hit), ...]
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
            result = run_cli(["search", q, "--limit", str(CLI_SEARCH_LIMIT)])
            hits = result if isinstance(result, list) else result.get("results", [])
            all_hits.extend(hits)

        if not all_hits:
            print(f"    [MISS] No hits for queries: {queries}")
            continue

        # 3. Score all hits with enhanced scoring
        scored_hits = []
        seen_ids = set()

        for hit in all_hits:
            if not isinstance(hit, dict):
                continue
            rid = hit.get("remId") or hit.get("_id")
            if not rid or rid in seen_ids:
                continue
            seen_ids.add(rid)

            hit_title = (hit.get("title") or hit.get("text", "")).strip()
            if not hit_title:
                continue

            # Enhanced scoring with aliases, tags, and exclusions
            score = calculate_enhanced_score(hit, term, term_title_case, hit_title)

            if score > 0:  # Only include non-zero scores
                scored_hits.append((score, hit))

        # 4. Sort and get top 5
        scored_hits.sort(reverse=True, key=lambda x: x[0])
        top_5 = scored_hits[:5]

        if not top_5:
            print(f"    [MISS] No quality matches for '{term}' after scoring")
            continue

        # 5. Best result
        best_score, best_hit = top_5[0]
        if best_score >= THRESHOLD_SEARCH_ACCEPT:
            rid = best_hit.get("remId") or best_hit.get("_id")
            found[term] = (rid, [hit for _, hit in top_5])
            print(f"    [FOUND] '{term}' → '{best_hit.get('title', '')}' ({rid}) score={best_score:.2f}")
            print(f"    [TOP5] Candidates (scores): {[(h.get('title', '')[:30], f'{s:.2f}') for s, h in top_5]}")
        else:
            best_title = best_hit.get('title', 'None')
            print(f"    [MISS] No high-quality match for '{term}' (best hit: '{best_title}', score: {best_score:.2f})")

    return found


# ── Step B2: Hierarchical Locate (map-guided branch read) ──────────────────

def hierarchical_locate(
    terms: list[str],
    already_found: dict[str, str],
    map_entries: list[dict]
) -> tuple[dict[str, str], dict[str, str]]:
    """
    For terms that Step A (map grep) and Step B (search) both missed,
    use the map as a routing table:
      1. Score each top-level branch (indent=0) by keyword relevance
         using title + summary fields.
      2. Read the best candidate branch at depth 2 to discover children.
      3. Match term against discovered children titles.

    Returns:
        (found: {term: rem_id}, branch_contexts: {term: branch_rem_id})
    """
    found = {}
    branch_contexts = {}  # NEW: Track which branch each term was found in

    missing = [t for t in terms if t not in already_found]
    if not missing:
        return found, branch_contexts

    # Build branch index: top-level entries (indent=0) with their sub-entries
    branches = []
    for i, entry in enumerate(map_entries):
        if entry["indent"] == 0:
            # Collect all child summarys/titles for this branch
            child_words = set()
            for j in range(i + 1, len(map_entries)):
                if map_entries[j]["indent"] == 0:
                    break
                child_words.update(
                    normalize(w) for w in map_entries[j]["title"].split() if len(w) > 2
                )
                if map_entries[j]["summary"]:
                    child_words.update(
                        normalize(w) for w in map_entries[j]["summary"].split() if len(w) > 1
                    )
            branches.append({
                "remId": entry["remId"],
                "title": entry["title"],
                "summary": entry["summary"],
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
                | set(normalize(w) for w in branch["summary"].split() if len(w) > 1)
                | branch["child_words"]
            )
            # Score by word overlap + substring containment bonus
            overlap = len(term_words & branch_all_words)
            for bw in branch_all_words:
                if term_norm in bw or bw in term_norm:
                    overlap += WEIGHT_SUBSTRING_OVERLAP
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
        return found, branch_contexts

    # Read each candidate branch at depth 2 and match
    read_cache: dict[str, list[dict]] = {}
    for branch_id, target_terms in branch_to_terms.items():
        branch_name = next((b["title"] for b in branches if b["remId"] == branch_id), branch_id)
        print(f"  [B2] Reading branch '{branch_name}' ({branch_id}) for terms: {target_terms}")

        if branch_id not in read_cache:
            data = run_cli(["read", branch_id, "--depth", str(CLI_BRANCH_DEPTH), "--child-limit", str(CLI_BRANCH_CHILD_LIMIT)])
            if isinstance(data, dict) and "error" not in data:
                children = _flatten_children(data, max_depth=CLI_BRANCH_DEPTH)
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
                    score = SCORE_PERFECT_MATCH
                elif term_norm in child_norm:
                    score = len(term_norm) / len(child_norm)
                elif child_norm in term_norm:
                    score = len(child_norm) / len(term_norm)
                # Title Case exact match bonus
                if term_tc == child_title:
                    score += SCORE_TITLE_CASE_BONUS

                if score > best_score:
                    best_score = score
                    best_child = child

            if best_child and best_score >= THRESHOLD_HIERARCHICAL:
                rid = best_child.get("remId") or best_child.get("_id")
                if rid:
                    found[term] = rid
                    branch_contexts[term] = branch_id  # NEW: Track branch
                    print(f"    [B2-FOUND] '{term}' → '{best_child['title']}' ({rid}) score={best_score:.2f}")
            else:
                print(f"    [B2-MISS] '{term}' not found in branch '{branch_name}'")

    return found, branch_contexts  # NEW: Return both


def extract_all_rem_ids_from_tree(node: dict, max_depth: int, current_depth: int = 0) -> list[str]:
    """
    Recursively extract all rem IDs from a tree structure up to max_depth.

    Args:
        node: The tree node (dict with 'remId' and 'children')
        max_depth: Maximum depth to traverse
        current_depth: Current recursion depth

    Returns:
        List of rem IDs (as strings)
    """
    ids = []

    if not isinstance(node, dict):
        return ids

    # Extract current node's ID (skip root at depth 0 if needed)
    rid = node.get("remId") or node.get("_id")
    if rid and current_depth > 0:
        ids.append(str(rid))

    # Recurse into children if within depth limit
    if current_depth < max_depth:
        children = node.get("children", [])
        if isinstance(children, list):
            for child in children:
                ids.extend(extract_all_rem_ids_from_tree(child, max_depth, current_depth + 1))

    return ids


def cross_validate_b_and_b2(
    term: str,
    step_b_top5: list[dict],
    step_b2_rem_id: Optional[str],
    step_b2_branch_id: Optional[str]
) -> Optional[str]:
    """
    Cross-validate Step B and B2 results by checking intersection.

    Strategy:
    1. If B2 found a result in a specific branch, read that branch (depth=2)
    2. Check if any of B's top 5 candidates exist in that branch
    3. If yes → return the highest-ranked B candidate that's in the branch
    4. If no → decide between B and B2 based on confidence

    Args:
        term: The search term
        step_b_top5: Top 5 candidates from Step B (list of hit dicts)
        step_b2_rem_id: The rem_id found by Step B2 (can be None)
        step_b2_branch_id: The branch where B2 found the result (can be None)

    Returns:
        The validated rem_id, or None if no confident result
    """
    # Edge case: No candidates from either step
    if not step_b_top5 and not step_b2_rem_id:
        print(f"    [VALIDATE] No results from B or B2 for '{term}'")
        return None

    # Edge case: Only B has results
    if step_b_top5 and not step_b2_branch_id:
        best_id = step_b_top5[0].get("remId") or step_b_top5[0].get("_id")
        print(f"    [VALIDATE] Using B result (B2 has nothing): {best_id}")
        return best_id

    # Edge case: Only B2 has results
    if not step_b_top5 and step_b2_rem_id:
        print(f"    [VALIDATE] Using B2 result (B has nothing): {step_b2_rem_id}")
        return step_b2_rem_id

    # Main case: Both have results - perform cross-validation
    print(f"    [VALIDATE] Cross-validating B and B2 results for '{term}'...")
    print(f"    [VALIDATE] B top 5: {[h.get('title', '')[:30] for h in step_b_top5]}")
    print(f"    [VALIDATE] B2 branch: {step_b2_branch_id}")

    # Read B2 branch with depth to get all children
    branch_data = run_cli(["read", step_b2_branch_id, "--depth", str(CLI_CROSS_VALIDATE_DEPTH)])
    if isinstance(branch_data, dict) and "error" not in branch_data:
        branch_children_ids = set(extract_all_rem_ids_from_tree(branch_data, max_depth=CLI_CROSS_VALIDATE_DEPTH))
        print(f"    [VALIDATE] B2 branch contains {len(branch_children_ids)} rem IDs")
    else:
        print(f"    [VALIDATE] Failed to read B2 branch: {branch_data.get('error', 'unknown')}")
        branch_children_ids = set()

    # Check intersection: Find highest-ranked B candidate in B2 branch
    for rank, candidate in enumerate(step_b_top5, start=1):
        candidate_id = candidate.get("remId") or candidate.get("_id")
        candidate_title = candidate.get("title", "")

        if candidate_id in branch_children_ids:
            print(f"    [VALIDATED] ✅ '{term}' → {candidate_id} ({candidate_title[:40]})")
            print(f"    [VALIDATED] Found at B rank #{rank}, confirmed in B2 branch")
            return candidate_id

    # No intersection found
    print(f"    [VALIDATE] ⚠️ No overlap between B top 5 and B2 branch children")

    # Decision: Trust B2 if it has a result, otherwise use B's top result
    if step_b2_rem_id:
        print(f"    [VALIDATE] Using B2 result (no intersection): {step_b2_rem_id}")
        return step_b2_rem_id
    else:
        best_id = step_b_top5[0].get("remId") or step_b_top5[0].get("_id")
        print(f"    [VALIDATE] Using B top result (B2 has no specific result): {best_id}")
        return best_id


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

def read_context_tree(rem_id: str, timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS) -> dict:
    """Read a single Rem at full depth with structured content. Cache-friendly."""
    print(f"  [READ] Fetching tree for {rem_id} (depth {CLI_TREE_DEPTH}, timeout {timeout_seconds}s)...")
    data = run_cli(["read", rem_id, "--depth", str(CLI_TREE_DEPTH), "--include-content", "structured"])
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
    match_threshold: float = EMBED_MATCH_THRESHOLD,
    new_threshold: float = EMBED_NEW_THRESHOLD
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

def run_pipeline(kb_map_path: str, overview_text: str, content_text: str) -> str:
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

    # ── Step A: KB Map Lookup ──
    print(f"\n[Step A] KB map lookup...")
    map_results, map_entries = lookup_kb_map(kb_map_path, all_terms)
    print(f"  Found {len(map_results)}/{len(all_terms)} via map")

    # ── Step B: Search unmapped (returns top 5 candidates) ──
    print(f"\n[Step B] Searching unmapped terms...")
    unmapped_after_a = [t for t in all_terms if t not in map_results]
    search_results_with_candidates = search_unmapped(unmapped_after_a, map_results)

    # Extract best remIds from B results
    search_results = {term: rem_id for term, (rem_id, _) in search_results_with_candidates.items()}
    print(f"  Found {len(search_results)}/{len(unmapped_after_a)} via search")

    # ── Step B2: Hierarchical Locate (returns branch contexts) ──
    unmapped_after_b = [t for t in unmapped_after_a if t not in search_results]
    if unmapped_after_b:
        print(f"\n[Step B2] Hierarchical locate for {len(unmapped_after_b)} missing terms...")
        b2_results, branch_contexts = hierarchical_locate(
            unmapped_after_b,
            {**map_results, **search_results},
            map_entries
        )
        print(f"  Found {len(b2_results)}/{len(unmapped_after_b)} via hierarchical locate")
    else:
        b2_results = {}
        branch_contexts = {}

    # ── Cross-Validation: Merge B and B2 with validation ──
    print(f"\n[Cross-Validation] Merging B + B2 results...")
    term_to_id = {**map_results}  # Start with map results (highest confidence)

    for term in unmapped_after_a:
        if term in search_results:
            # B found something - check if B2 also found it
            _, step_b_top5 = search_results_with_candidates.get(term, (None, []))
            step_b2_rem_id = b2_results.get(term)
            step_b2_branch_id = branch_contexts.get(term)

            validated_id = cross_validate_b_and_b2(
                term,
                step_b_top5,
                step_b2_rem_id,
                step_b2_branch_id
            )

            if validated_id:
                term_to_id[term] = validated_id

        elif term in b2_results:
            # Only B2 found something
            term_to_id[term] = b2_results[term]
            print(f"  [B2-ONLY] '{term}' → {b2_results[term]} (from B2 only)")

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
    parser.add_argument("--kb-map", required=True, help="Path to kb_map.json (or legacy SKILL.md)")
    parser.add_argument("--overview-file", required=True, help="Path to overview markdown")
    parser.add_argument("--content-file", required=True, help="Path to answer markdown")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS, help="CLI timeout in seconds")
    args = parser.parse_args()

    with open(args.overview_file, 'r', encoding='utf-8-sig') as f:
        overview = f.read()
    with open(args.content_file, 'r', encoding='utf-8-sig') as f:
        content = f.read()

    print(run_pipeline(args.kb_map, overview, content))
