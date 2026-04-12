"""
Batch-fetch all top-level RemNote branches using --include-content structured,
and save raw JSON results to toplevel_dump.json.

Depth strategy (reads from kb_map.json if available):
  - branch with known non-empty children  → depth=1 (only need child IDs)
  - terminal node (children: []) or leaf  → depth=2 (need content for summary)

Usage:
    python .agents/skills/kb-map-updater/fetch_toplevel.py [remId ...]

Output:
    toplevel_dump.json  (workspace root, or dump_<remId>.json for targeted fetch)
"""
import subprocess
import json
import sys
import os

CLI = ["node", "./node_modules/remnote-cli/dist/index.js"]

# All top-level branch IDs (source of truth for branch list)
# Format: (label, rem_id)
BRANCHES = [
    ("Basic optics",             "4uE8lPWyfyfMkV0NY"),
    ("Fundamentals",             "t2RMKcbnchc4jlcbx"),
    ("Procedure",                "qMErQqVFhEEkLYn2G"),
    ("Examination",              "mvIEkYdmzLIKXsPz1"),
    ("Common presentation",      "5CwJCcEZY38vm4dtb"),
    ("External disease",         "TtzBhK6lHH71f8XQF"),
    ("Cornea",                   "W7KYjX2Q6Z722xbS8"),
    ("Lens and Cataract",        "OgQr7FNqhHLU0qlUs"),
    ("Glaucoma",                 "NG49CdruX4zDzD2Rq"),
    ("Iris",                     "HI4spvrHQIjuw5sua"),
    ("Uveitis",                  "kl4ItbmoLAmfqce7L"),
    ("Retina",                   "axP0MADOJiMeJBf76"),
    ("Neuro-ophthalmology",      "JC3yhtfC24Gv1sMCY"),
    ("Systematic",               "rGexWin57k2Yp7LxY"),
    ("Pediatric ophthalmology",  "bI7e9zIlyeyoPzBDV"),
    ("Ophthamlology medication", "9o9I65kDVTQpu32Ob"),
    ("GVHD",                     "2KIH8sENSdJ4x3jKk"),
    ("Case discussion",          "re3th39xJtgK9Z42Y"),
    ("Meta-analysis",            "t70gU6mbwxvCe23N8"),
]

KB_MAP_PATH = os.path.join(os.path.dirname(__file__), "..", "remnote-kb-navigation", "kb_map.json")


def load_kb_map():
    """Load kb_map.json. Returns (has_children: set[remId], leaves_by_branch: dict).

    has_children: remIds whose children list is non-empty (→ depth=1).
    leaves_by_branch: branch remId → [(leaf_label, leaf_remId), ...].
    """
    has_children = set()
    leaves_by_branch = {}

    if not os.path.exists(KB_MAP_PATH):
        return has_children, leaves_by_branch

    try:
        with open(KB_MAP_PATH, encoding="utf-8") as f:
            data = json.load(f)
        for branch in data.get("branches", []):
            brid = branch.get("remId", "")
            children = [
                c for c in branch.get("children", [])
                if c.get("title", "").strip() and c.get("remType") != "portal"
            ]
            if children:
                has_children.add(brid)
                leaves_by_branch[brid] = [(c.get("title", ""), c.get("remId", "")) for c in children]
    except Exception as e:
        print(f"[WARN] Failed to load kb_map.json: {e}", file=sys.stderr)

    return has_children, leaves_by_branch


def fetch_branch(label, rem_id, depth=2):
    """Fetch a single branch/leaf using structured content format.

    depth=1: branch with known children (only need to confirm child list).
    depth=2: terminal node (children=[]) — need content to generate summary.
    """
    args = CLI + [
        "read", rem_id, "-d", str(depth),
        "--include-content", "structured",
        "--child-limit", "500", "--json"
    ]
    try:
        proc = subprocess.run(args, capture_output=True, text=True, timeout=90, encoding="utf-8")
        data = json.loads(proc.stdout)
        data["_label"] = label
        data["_depth"] = depth
        return data
    except json.JSONDecodeError:
        # Retry once on parse failure
        try:
            proc = subprocess.run(args, capture_output=True, text=True, timeout=120, encoding="utf-8")
            data = json.loads(proc.stdout)
            data["_label"] = label
            data["_depth"] = depth
            data["_retried"] = True
            return data
        except Exception as e2:
            return {"_label": label, "remId": rem_id, "error": str(e2)}
    except Exception as e:
        return {"_label": label, "remId": rem_id, "error": str(e)}


def main():
    results = []
    ok_count = 0
    err_count = 0

    rem_ids = sys.argv[1:]
    has_children, leaves_by_branch = load_kb_map()

    branch_remids = {rem_id for _, rem_id in BRANCHES}
    remid2label = {rem_id: label for label, rem_id in BRANCHES}

    def get_depth(rem_id):
        # Has known non-empty children in kb_map → depth=1 (branch)
        if rem_id in has_children:
            return 1
        # Bootstrap (no kb_map yet): all top-level branches default to depth=1
        if rem_id in branch_remids and not os.path.exists(KB_MAP_PATH):
            return 1
        return 2

    targets = []
    if rem_ids:
        for rem_id in rem_ids:
            label = remid2label.get(rem_id, rem_id)
            targets.append((label, rem_id))
            # For a branch remId, also fetch its known leaves
            for leaf_label, leaf_remid in leaves_by_branch.get(rem_id, []):
                targets.append((leaf_label, leaf_remid))
    else:
        targets = BRANCHES[:]

    for label, rem_id in targets:
        depth = get_depth(rem_id)
        print(f"Fetching: {label} ({rem_id}) [depth={depth}]...", file=sys.stderr)
        data = fetch_branch(label, rem_id, depth=depth)
        results.append(data)

        if "error" in data:
            print(f"  ERROR: {data['error']}", file=sys.stderr)
            err_count += 1
        else:
            n = len(data.get("contentStructured", []))
            retried = " (retried)" if data.get("_retried") else ""
            print(f"  OK: {n} children{retried}", file=sys.stderr)
            ok_count += 1

    out_path = "toplevel_dump.json" if not rem_ids else f"dump_{'_'.join(rem_ids)}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\nDone. {ok_count} OK, {err_count} errors. Saved to {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
