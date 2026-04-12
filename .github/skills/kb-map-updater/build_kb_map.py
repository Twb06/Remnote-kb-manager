"""
Build or update kb_map.json from toplevel_dump.json (structured format).

THREE MODES:
  --update-summaries (DEFAULT)
      Preserves the existing kb_map.json structure exactly (which nodes are
      present, hierarchy, order). Only fills/updates the 'summary' field for
      nodes whose remId appears in toplevel_dump.json. Nodes not in the dump
      are left unchanged. Nodes in the dump but NOT already in kb_map.json
      are IGNORED — the map structure is treated as curated and authoritative.

  --rebuild
      Fully rebuilds kb_map.json structure from toplevel_dump.json, replacing
      all existing children. Use only when you intentionally want to sync the
      map structure with RemNote (e.g. after adding a new top-level branch).
      Existing summaries are preserved by remId across the rebuild.

  --add <remId1> [remId2] [remId3] ... [--summary <text>]
      Adds one or more nodes to kb_map.json by remId.
      - Always auto-placement: fetches parentRemId from RemNote and walks
        up the ancestor chain until it finds a node already in kb_map.json
        or root. Inserts as a child of that ancestor (or top-level if root).
      - Intermediate ancestors not in the map are automatically created
        along the path (chain fill), so the full hierarchy is preserved.
      - Title and remType always fetched from RemNote (daemon required).
      - Skips any remId already in kb_map.json (no duplicates, no error).
      - For top-level branches, reminds to also add to BRANCHES in
        fetch_toplevel.py.
      - Optional --summary applies to ALL nodes added in this invocation.

Summary field rules:
  - keyword-dense English, ~200 chars max
  - include abbreviations + full names for major medical terms
  - optimized for agent map-lookup accuracy (not human prose)
  - empty string ("") means not yet summarized

Usage:
    python .agents/skills/kb-map-updater/build_kb_map.py                  # update-summaries mode
    python .agents/skills/kb-map-updater/build_kb_map.py --update-summaries
    python .agents/skills/kb-map-updater/build_kb_map.py --rebuild
    python .agents/skills/kb-map-updater/build_kb_map.py --rebuild [dump.json]
    python .agents/skills/kb-map-updater/build_kb_map.py --add <remId>
    python .agents/skills/kb-map-updater/build_kb_map.py --add <remId1> <remId2> <remId3>
    python .agents/skills/kb-map-updater/build_kb_map.py --add <remId> --summary "keywords here"
"""
import json
import os
import subprocess
import sys

DUMP_PATH = "toplevel_dump.json"
KB_MAP_PATH = os.path.join(os.path.dirname(__file__), "..", "remnote-kb-navigation", "kb_map.json")
CLI = ["node", "./node_modules/remnote-cli/dist/index.js"]

ROOT_REMID = "Da8SsKWwuA9doqpsp"
ROOT_TITLE = "眼科"


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def load_dump(dump_path: str) -> dict:
    """Load toplevel_dump.json and index entries by remId."""
    with open(dump_path, encoding="utf-8") as f:
        dump = json.load(f)
    index = {}
    for entry in dump:
        rid = entry.get("remId", "")
        if rid:
            index[rid] = entry
        # Also index contentStructured children recursively
        _index_structured(entry.get("contentStructured", []), index)
    return index


def _index_structured(nodes: list, index: dict):
    """Recursively index contentStructured nodes by remId."""
    for n in nodes:
        rid = n.get("remId", "")
        if rid:
            index[rid] = n
        _index_structured(n.get("children", []) or [], index)


def load_existing_kb_map(kb_map_path: str):
    """Load existing kb_map.json. Returns (data_dict, summaries_dict)."""
    summaries = {}
    data = None
    if not os.path.exists(kb_map_path):
        return data, summaries
    try:
        with open(kb_map_path, encoding="utf-8") as f:
            data = json.load(f)
        _extract_summaries(data.get("branches", []), summaries)
    except Exception as e:
        print(f"[WARN] Failed to load existing kb_map.json: {e}", file=sys.stderr)
    return data, summaries


def _extract_summaries(nodes: list, out: dict):
    for n in nodes:
        rid = n.get("remId", "")
        if rid:
            out[rid] = n.get("summary", "")
        _extract_summaries(n.get("children", []), out)


def filter_children(content_structured: list) -> list:
    """Remove empty-title and portal nodes."""
    return [
        c for c in (content_structured or [])
        if c.get("title", "").strip() and c.get("remType") != "portal"
    ]


# ---------------------------------------------------------------------------
# Mode A: --update-summaries  (default)
#   Walk existing kb_map.json nodes; for each node whose remId is found in
#   the dump index, generate a summary from dump content.
#   Without --force: only fills empty summaries.
#   With --force: replaces ALL summaries with freshly generated content.
#   Structure is NOT changed.
# ---------------------------------------------------------------------------

def update_summaries_mode(dump_index: dict, existing_data: dict, *, force: bool = False) -> dict:
    """Return a new kb_map dict with summaries updated from dump_index.

    Args:
        force: if True, overwrite all summaries (even non-empty ones).
    """
    generated = 0
    kept = 0
    not_in_dump = 0

    def walk(nodes: list) -> list:
        nonlocal generated, kept, not_in_dump
        result = []
        for n in nodes:
            node = dict(n)  # shallow copy
            rid = node.get("remId", "")
            title = node.get("title", "")
            dump_entry = dump_index.get(rid)
            if dump_entry:
                has_summary = bool(node.get("summary", "").strip())
                if force or not has_summary:
                    node["summary"] = _generate_summary_from_dump(title, dump_entry)
                    generated += 1
                else:
                    kept += 1
            else:
                not_in_dump += 1
            node["children"] = walk(node.get("children", []))
            result.append(node)
        return result

    branches = walk(existing_data.get("branches", []))
    kb_map = {
        "root": existing_data.get("root", {"remId": ROOT_REMID, "title": ROOT_TITLE}),
        "branches": branches,
    }

    label = "update-summaries" + (" --force" if force else "")
    print(f"  [{label}] {generated} generated, {kept} kept, {not_in_dump} not in dump.", file=sys.stderr)
    print(f"  Structure is UNCHANGED. Run with --rebuild to sync structure from RemNote.", file=sys.stderr)
    return kb_map


# ---------------------------------------------------------------------------
# Mode B: --rebuild
#   Fully rebuild structure from dump, preserving existing summaries by remId.
# ---------------------------------------------------------------------------

def build_entry_from_dump(node: dict, existing_summaries: dict) -> dict:
    """Build a kb_map node from a contentStructured item."""
    rem_id = node.get("remId", "")
    children_raw = filter_children(node.get("children", []) or node.get("contentStructured", []))
    return {
        "remId": rem_id,
        "title": (node.get("title") or node.get("headline") or "").strip(),
        "remType": node.get("remType", "text"),
        "summary": existing_summaries.get(rem_id, ""),
        "children": [build_entry_from_dump(c, existing_summaries) for c in children_raw],
    }


def rebuild_mode(dump_path: str, existing_summaries: dict) -> dict:
    """Rebuild kb_map.json structure entirely from toplevel_dump.json."""
    with open(dump_path, encoding="utf-8") as f:
        dump = json.load(f)

    branches = []
    for entry in dump:
        if "error" in entry:
            print(f"[SKIP] {entry.get('_label', '?')}: error in dump", file=sys.stderr)
            continue
        rem_id = entry.get("remId", "")
        title = (entry.get("title") or "").strip()
        rem_type = entry.get("remType", "document")
        children_raw = filter_children(entry.get("contentStructured", []))
        branch = {
            "remId": rem_id,
            "title": title,
            "remType": rem_type,
            "summary": existing_summaries.get(rem_id, ""),
            "children": [build_entry_from_dump(c, existing_summaries) for c in children_raw],
        }
        branches.append(branch)
        status = f"{len(children_raw)} children" if children_raw else "terminal"
        print(f"  {title} ({rem_id}): {status}", file=sys.stderr)

    kb_map = {
        "root": {"remId": ROOT_REMID, "title": ROOT_TITLE},
        "branches": branches,
    }
    total = sum(len(b["children"]) for b in branches)
    print(f"\n  [rebuild] {len(branches)} branches, {total} direct children.", file=sys.stderr)
    print(f"  WARNING: structure rebuilt from RemNote dump. Manual curation is overwritten.", file=sys.stderr)
    return kb_map


# ---------------------------------------------------------------------------
# Mode C: --add
#   Add a single node to kb_map.json. Fetches metadata from RemNote if
#   --title is not provided. Rejects duplicates.
# ---------------------------------------------------------------------------

def _find_node_by_id(nodes: list, target_id: str):
    """Find a node by remId in a nested tree. Returns (node, parent_list) or (None, None)."""
    for n in nodes:
        if n.get("remId") == target_id:
            return n, nodes
        found, parent = _find_node_by_id(n.get("children", []), target_id)
        if found is not None:
            return found, parent
    return None, None


def _all_rem_ids(nodes: list) -> set:
    """Collect all remIds from a nested node tree."""
    ids = set()
    for n in nodes:
        rid = n.get("remId", "")
        if rid:
            ids.add(rid)
        ids.update(_all_rem_ids(n.get("children", [])))
    return ids


def _fetch_rem_metadata(rem_id: str) -> dict:
    """Fetch title, remType, and parentRemId from RemNote via remnote-cli."""
    args = CLI + ["read", rem_id, "-d", "0", "--include-content", "structured", "--json"]
    try:
        proc = subprocess.run(args, capture_output=True, text=True, timeout=30, encoding="utf-8")
        data = json.loads(proc.stdout)
        return {
            "title": (data.get("title") or data.get("headline") or "").strip(),
            "remType": data.get("remType", "text"),
            "parentRemId": data.get("parentRemId", ""),
        }
    except Exception as e:
        print(f"ERROR: Failed to fetch rem {rem_id} from RemNote: {e}", file=sys.stderr)
        print("  Provide --title manually or ensure remnote-cli daemon is running.", file=sys.stderr)
        sys.exit(1)


def _resolve_ancestor_chain(start_parent_id: str, all_ids: set) -> tuple[list[dict], str | None]:
    """Walk up from start_parent_id, collecting intermediate nodes NOT in kb_map.

    Returns:
        (chain, attach_to)
        - chain: list of intermediate node metadata dicts in root→leaf order.
          Each dict has remId, title, remType.  Empty if start_parent_id is
          already in the map or is root.
        - attach_to: remId of the existing map node to attach under,
          or None if the chain reaches root (→ top-level).
    """
    if start_parent_id == ROOT_REMID:
        return [], None
    if start_parent_id in all_ids:
        return [], start_parent_id

    visited: set[str] = set()
    chain: list[dict] = []  # collected in leaf→root order, reversed at return
    current_id = start_parent_id

    while len(visited) < 20:
        if current_id in visited:
            print(f"ERROR: Cycle detected at '{current_id}'.", file=sys.stderr)
            sys.exit(1)
        visited.add(current_id)

        meta = _fetch_rem_metadata(current_id)
        chain.append({
            "remId": current_id,
            "title": meta["title"],
            "remType": meta["remType"],
        })

        grandparent = meta.get("parentRemId", "")
        if not grandparent:
            print(f"ERROR: rem '{current_id}' has no parentRemId. Cannot auto-place.", file=sys.stderr)
            sys.exit(1)

        if grandparent == ROOT_REMID:
            return list(reversed(chain)), None
        if grandparent in all_ids:
            return list(reversed(chain)), grandparent

        current_id = grandparent

    print(f"ERROR: Exceeded max depth (20) walking parent chain.", file=sys.stderr)
    sys.exit(1)


def _insert_node(branches: list, node: dict, parent_id: str | None):
    """Insert a node into the tree under parent_id, or as top-level if None."""
    if parent_id:
        pnode, _ = _find_node_by_id(branches, parent_id)
        if pnode is None:
            print(f"ERROR: parent '{parent_id}' not found in tree.", file=sys.stderr)
            sys.exit(1)
        pnode["children"].append(node)
        print(f"    + '{node['title']}' under '{pnode['title']}'", file=sys.stderr)
    else:
        node["remType"] = "document"
        branches.append(node)
        print(f"    + '{node['title']}' as top-level branch", file=sys.stderr)
        print(f"      REMINDER: Add to BRANCHES in fetch_toplevel.py", file=sys.stderr)


def add_node_mode(existing_data: dict, rem_ids: list[str], summary: str = "") -> dict:
    """Add one or more nodes to kb_map.json with auto-placement and chain fill.

    Args:
        summary: optional summary applied to target nodes (not intermediates).
    """
    branches = existing_data.get("branches", [])
    all_ids = _all_rem_ids(branches)
    added = 0

    for rem_id in rem_ids:
        if rem_id in all_ids:
            print(f"  SKIP: '{rem_id}' already exists in kb_map.json.", file=sys.stderr)
            continue

        # Fetch metadata
        print(f"\n  [{rem_id}] Fetching metadata...", file=sys.stderr)
        meta = _fetch_rem_metadata(rem_id)
        title = meta["title"]
        rem_type = meta["remType"]
        direct_parent = meta.get("parentRemId", "")

        if not title:
            print(f"  SKIP: RemNote returned empty title for {rem_id}.", file=sys.stderr)
            continue
        if not direct_parent:
            print(f"  SKIP: '{rem_id}' has no parentRemId.", file=sys.stderr)
            continue

        print(f"  title='{title}', remType='{rem_type}'", file=sys.stderr)

        # Resolve ancestor chain
        print(f"  Resolving placement...", file=sys.stderr)
        chain, attach_to = _resolve_ancestor_chain(direct_parent, all_ids)

        # Insert intermediate chain nodes (root→leaf order)
        if chain:
            print(f"  Filling {len(chain)} intermediate node(s):", file=sys.stderr)
            current_attach = attach_to
            for intermediate in chain:
                int_node = {
                    "remId": intermediate["remId"],
                    "title": intermediate["title"],
                    "remType": intermediate["remType"],
                    "summary": "",
                    "children": [],
                }
                _insert_node(branches, int_node, current_attach)
                all_ids.add(intermediate["remId"])
                current_attach = intermediate["remId"]
                added += 1

        # Insert the target node
        new_node = {
            "remId": rem_id,
            "title": title,
            "remType": rem_type,
            "summary": summary,
            "children": [],
        }
        # direct_parent should now be in all_ids (or is root)
        resolved_parent = direct_parent if direct_parent != ROOT_REMID else None
        _insert_node(branches, new_node, resolved_parent)
        all_ids.add(rem_id)
        added += 1

    print(f"\n  Total: {added} node(s) added.", file=sys.stderr)
    return {
        "root": existing_data.get("root", {"remId": ROOT_REMID, "title": ROOT_TITLE}),
        "branches": branches,
    }


# ---------------------------------------------------------------------------
# Summary generation helper
# ---------------------------------------------------------------------------

def _generate_summary_from_dump(node_title: str, dump_entry: dict) -> str:
    """Generate a one-sentence description + keywords for a node."""
    keywords = [node_title.lower()]
    
    # Extract children titles from contentStructured
    content = dump_entry.get("contentStructured", [])
    child_titles = []
    for child in content[:5]:  # limit to first 5 children
        ct = (child.get("title") or child.get("headline") or "").strip()
        if ct:
            child_titles.append(ct.lower())
    
    keywords.extend(child_titles)
    
    # Generate description based on node type and title
    descriptions = {
        "Visual Acuity Testing": "Standardized methods for measuring visual acuity",
        "Photostress Test": "Assessment of macular function after bright light exposure",
        "Worth 4 Dot": "Evaluation of binocular vision and fusion",
        "CFP": "Color fundus photography for retinal documentation",
        "Infrared": "Infrared imaging for ocular structure visualization",
        "Red free": "Red-free light imaging for nerve fiber layer assessment",
        "Cobolt": "Cobalt blue light examination for anterior segment",
        "Prism": "Prism-based assessment of ocular alignment",
        "FAF": "Fundus autofluorescence imaging of retinal pigment epithelium",
        "FAG": "Fluorescein angiography for retinal circulation visualization",
        "ICG": "Indocyanine green angiography for choroidal vasculature assessment",
        "OCT": "Optical coherence tomography for retinal cross-sectional imaging",
        "Slit-lamp": "Microscopic examination of anterior ocular structures",
        "Instruments": "Diagnostic instruments for ophthalmic examination",
        "Findings": "Clinical findings on ophthalmologic examination",
    }
    
    description = descriptions.get(node_title, f"{node_title}")
    
    # Combine description + keywords
    all_keywords = list(dict.fromkeys(keywords))  # deduplicate
    summary = f"{description}. {', '.join(all_keywords[:10])}"  # limit to 10 keywords
    
    return summary[:200]  # cap at 200 chars


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    args = sys.argv[1:]
    mode = "update-summaries"
    dump_path = DUMP_PATH
    add_rem_ids: list[str] = []
    manual_summary = ""
    force = False

    i = 0
    while i < len(args):
        a = args[i]
        if a == "--rebuild":
            mode = "rebuild"
        elif a == "--update-summaries":
            mode = "update-summaries"
        elif a == "--force":
            force = True
        elif a == "--add":
            mode = "add"
            # Collect all subsequent non-flag args as remIds
            i += 1
            while i < len(args) and not args[i].startswith("--"):
                add_rem_ids.append(args[i])
                i += 1
            if not add_rem_ids:
                print("ERROR: --add requires at least one remId.", file=sys.stderr)
                sys.exit(1)
            continue  # skip i += 1 at bottom
        elif a == "--summary":
            i += 1
            if i >= len(args):
                print("ERROR: --summary requires a value.", file=sys.stderr)
                sys.exit(1)
            manual_summary = args[i]
        elif not a.startswith("--"):
            dump_path = a
        i += 1

    existing_data, existing_summaries = load_existing_kb_map(KB_MAP_PATH)

    print(f"Mode: {mode}" + (" --force" if force else ""), file=sys.stderr)

    if mode == "add":
        if existing_data is None:
            print("ERROR: No existing kb_map.json found. Run --rebuild first.", file=sys.stderr)
            sys.exit(1)
        kb_map = add_node_mode(existing_data, add_rem_ids, manual_summary)
    elif mode == "update-summaries":
        if existing_data is None:
            print("ERROR: No existing kb_map.json found. Run --rebuild first.", file=sys.stderr)
            sys.exit(1)
        if not os.path.exists(dump_path):
            print(f"ERROR: {dump_path} not found. Run fetch_toplevel.py first.", file=sys.stderr)
            sys.exit(1)
        dump_index = load_dump(dump_path)
        kb_map = update_summaries_mode(dump_index, existing_data, force=force)
    else:  # rebuild
        if not os.path.exists(dump_path):
            print(f"ERROR: {dump_path} not found. Run fetch_toplevel.py first.", file=sys.stderr)
            sys.exit(1)
        kb_map = rebuild_mode(dump_path, existing_summaries)

    os.makedirs(os.path.dirname(KB_MAP_PATH), exist_ok=True)
    with open(KB_MAP_PATH, "w", encoding="utf-8") as f:
        json.dump(kb_map, f, ensure_ascii=False, indent=2)

    print(f"\nDone. Written to {KB_MAP_PATH}", file=sys.stderr)


if __name__ == "__main__":
    main()
