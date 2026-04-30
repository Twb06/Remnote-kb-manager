"""
Build or update kb_map.json from toplevel_dump.json (structured format).

This script handles STRUCTURE ONLY. Summary writing is the AI agent's
responsibility (see SKILL.md Step 4).

TWO MODES:
  --rebuild
      Fully rebuilds kb_map.json structure from toplevel_dump.json, replacing
      all existing children. Use only when you intentionally want to sync the
      map structure with RemNote (e.g. after adding a new top-level branch).
      Existing summaries are preserved by remId across the rebuild.

  --add <remId> <summary>
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
      - Can be specified multiple times to add multiple nodes with their summaries.

Summary field rules:
  - keyword-dense English, ~200 chars max
  - include abbreviations + full names for major medical terms
  - optimized for agent map-lookup accuracy (not human prose)
  - empty string ("") means not yet summarized
  - Summary content is written by the AI agent, NOT by this script

Usage:
    python .github/skills/kb-map-updater/build_kb_map.py --rebuild
    python .github/skills/kb-map-updater/build_kb_map.py --rebuild [dump.json]
    python .github/skills/kb-map-updater/build_kb_map.py --add <remId> "summary text"
    python .github/skills/kb-map-updater/build_kb_map.py --add <remId1> "summary1" --add <remId2> "summary2"
    python .github/skills/kb-map-updater/build_kb_map.py --add <remId> ""  # empty summary
"""
import argparse
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
# Mode A: --rebuild
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
# Mode B: --add
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
        error_msg = f"Failed to fetch rem {rem_id} from RemNote: {e}. Provide --title manually or ensure remnote-cli daemon is running."
        print(f"ERROR: {error_msg}", file=sys.stderr)
        raise RuntimeError(error_msg) from e


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
            error_msg = f"Cycle detected at '{current_id}'."
            print(f"ERROR: {error_msg}", file=sys.stderr)
            raise RuntimeError(error_msg)
        visited.add(current_id)

        meta = _fetch_rem_metadata(current_id)
        chain.append({
            "remId": current_id,
            "title": meta["title"],
            "remType": meta["remType"],
        })

        grandparent = meta.get("parentRemId", "")
        if not grandparent:
            error_msg = f"rem '{current_id}' has no parentRemId. Cannot auto-place."
            print(f"ERROR: {error_msg}", file=sys.stderr)
            raise RuntimeError(error_msg)

        if grandparent == ROOT_REMID:
            return list(reversed(chain)), None
        if grandparent in all_ids:
            return list(reversed(chain)), grandparent

        current_id = grandparent

    error_msg = "Exceeded max depth (20) walking parent chain."
    print(f"ERROR: {error_msg}", file=sys.stderr)
    raise RuntimeError(error_msg)


def _insert_node(branches: list, node: dict, parent_id: str | None):
    """Insert a node into the tree under parent_id, or as top-level if None."""
    if parent_id:
        pnode, _ = _find_node_by_id(branches, parent_id)
        if pnode is None:
            error_msg = f"parent '{parent_id}' not found in tree."
            print(f"ERROR: {error_msg}", file=sys.stderr)
            raise RuntimeError(error_msg)
        pnode["children"].append(node)
        print(f"    + '{node['title']}' under '{pnode['title']}'", file=sys.stderr)
    else:
        node["remType"] = "document"
        branches.append(node)
        print(f"    + '{node['title']}' as top-level branch", file=sys.stderr)
        print(f"      REMINDER: Add to BRANCHES in fetch_toplevel.py", file=sys.stderr)


def add_node_mode(existing_data: dict, nodes: list[dict]) -> dict:
    """Add one or more nodes to kb_map.json with auto-placement and chain fill.

    Args:
        nodes: list of dicts with 'remId' and 'summary' keys.
               Example: [{'remId': 'abc', 'summary': 'text'}, ...]
    """
    branches = existing_data.get("branches", [])
    all_ids = _all_rem_ids(branches)
    added = 0

    for node_spec in nodes:
        rem_id = node_spec['remId']
        node_summary = node_spec.get('summary', '')
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
            "summary": node_summary,
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
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Build or update kb_map.json from RemNote structure.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n"
               "  %(prog)s --rebuild\n"
               "  %(prog)s --add abc123 'Summary text here'\n"
               "  %(prog)s --add id1 'sum1' --add id2 'sum2'\n"
    )

    parser.add_argument('--rebuild', action='store_true',
                        help='Rebuild kb_map.json from toplevel_dump.json')
    parser.add_argument('--add', action='append', nargs=2,
                        metavar=('REMID', 'SUMMARY'),
                        help='Add a node with remId and summary (can be repeated)')
    parser.add_argument('dump_path', nargs='?', default=DUMP_PATH,
                        help='Path to dump file (for --rebuild mode)')

    args = parser.parse_args()

    # Determine mode
    if args.rebuild and args.add:
        parser.error("Cannot use --rebuild and --add together.")

    if not args.rebuild and not args.add:
        parser.error("Must specify either --rebuild or --add.")

    mode = "rebuild" if args.rebuild else "add"
    existing_data, existing_summaries = load_existing_kb_map(KB_MAP_PATH)

    print(f"Mode: {mode}", file=sys.stderr)

    # Transaction: build complete kb_map first, only write if successful
    kb_map = None
    try:
        if mode == "add":
            if existing_data is None:
                print("ERROR: No existing kb_map.json found. Run --rebuild first.", file=sys.stderr)
                sys.exit(1)
            # Convert argparse result to list of dicts
            nodes_to_add = [{"remId": remid, "summary": summary}
                           for remid, summary in args.add]
            kb_map = add_node_mode(existing_data, nodes_to_add)
        else:  # rebuild
            if not os.path.exists(args.dump_path):
                print(f"ERROR: {args.dump_path} not found. Run fetch_toplevel.py first.", file=sys.stderr)
                sys.exit(1)
            kb_map = rebuild_mode(args.dump_path, existing_summaries)

        # Only write if processing succeeded
        os.makedirs(os.path.dirname(KB_MAP_PATH), exist_ok=True)
        with open(KB_MAP_PATH, "w", encoding="utf-8") as f:
            json.dump(kb_map, f, ensure_ascii=False, indent=2)

        print(f"\nDone. Written to {KB_MAP_PATH}", file=sys.stderr)

    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user. No changes written.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: Operation failed: {e}", file=sys.stderr)
        print("No changes written to kb_map.json (rollback).", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
