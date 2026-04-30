---
name: kb-map-updater
description: Maintains kb_map.json — a lightweight index of the RemNote KB for agent routing. Supports incremental node addition (--add) and periodic full resync (fetch + rebuild).
---

# KB Map Updater

Maintains `remnote-kb-navigation/kb_map.json` — a **lightweight index** (not a full mirror) of the RemNote knowledge base. Each entry stores `remId`, `title`, hierarchy, and a keyword-dense English summary for agent map-lookup routing.

## Key concept

`kb_map.json` is an **index**, not a complete replica of the KB. It tracks only the nodes the agent needs for navigation and routing. Most day-to-day updates use `--add` to insert specific nodes on demand — no batch fetch required.

## When to use

| Scenario | Action |
|----------|--------|
| Add a known remId to the index | `--add` (daily, no fetch) |
| Another skill just wrote new content | `--add` the new remIds |
| User says "refresh the KB map" / periodic full resync | fetch → `--rebuild` |
| Bootstrap (no kb_map.json yet) | fetch → `--rebuild` |

## Prerequisites

1. **remnote-cli daemon** must be running and connected (`remnote-cli status` → `connected: true`).
2. **Node.js** available (remnote-cli is a Node package at `./node_modules/remnote-cli`).
3. **Python 3** available in the activated virtual environment.

## Workflow

### Daily: add nodes incrementally (`--add`)

The most common operation. Adds one or more nodes by remId, auto-resolving their position from RemNote. **No fetch script needed.**

#### Step 1 — Ensure daemon is connected

```bash
node ./node_modules/remnote-cli/dist/index.js status
```

If not connected:

```bash
node ./node_modules/remnote-cli/dist/index.js daemon start
# wait ~5s, then re-check status
```

#### Step 2 — Add nodes

```bash
# Add a single node (auto-resolves position from RemNote parent chain):
python .github/skills/kb-map-updater/build_kb_map.py --add <remId>

# Add multiple nodes at once:
python .github/skills/kb-map-updater/build_kb_map.py --add <remId1> <remId2> <remId3>

# Add with a pre-filled summary:
python .github/skills/kb-map-updater/build_kb_map.py --add <remId> --summary "IOP measurement, tonometry"
```

**What it does:**
- Skips any `remId` already in `kb_map.json` (no error, just warns).
- For each remId, fetches `title`, `remType`, and `parentRemId` from RemNote via `remnote-cli read`.
- **Auto-placement**: walks up the ancestor chain until it finds a node already in the map or root.
- **Chain fill**: if intermediate ancestors are NOT in the map, they are automatically created along the path.
- If the chain reaches root → top-level branch (reminds to update `BRANCHES` in `fetch_toplevel.py`).
- Writes updated `kb_map.json`.

**Parameters:**
| Flag | Required | Description |
|------|----------|-------------|
| `--add <remId> [...]` | Yes | One or more RemNote rem IDs to add |
| `--summary <text>` | No | Pre-fill summary for target nodes (English keywords); default: `""` |

---

### Full resync (rare): fetch + rebuild

Only needed for bootstrap or periodic full refresh of structure/summaries.

#### Step 1 — Ensure daemon is connected

(Same as above.)

#### Step 2 — Run the fetch script

```bash
python .github/skills/kb-map-updater/fetch_toplevel.py
```

**What it does:**
- Reads the `BRANCHES` list (all top-level branch labels + rem IDs) defined inside the script.
- Reads `kb_map.json` to determine fetch depth per node:
  - Node has `children: [...]` (non-empty) → **depth=1** (branch, only need child list).
  - Node has `children: []` or is absent from map → **depth=2** (terminal, need content for summary).
- Uses `--include-content structured` format (returns `contentStructured` with remId per child).
- Bootstrap case (no `kb_map.json` yet): all top-level branches default to depth=1.
- Saves all results to `toplevel_dump.json`. Each result includes `_depth` and `contentStructured`.

Output: `toplevel_dump.json` — array of JSON objects, one per fetched node.

#### Step 3 — Rebuild kb_map.json structure

```bash
python .github/skills/kb-map-updater/build_kb_map.py --rebuild
```

**What it does:**
- Completely rebuilds `kb_map.json` structure from `toplevel_dump.json`.
- All children come directly from RemNote (modulo empty-title and portal filtering).
- Preserves existing `summary` values by `remId`.
- **WARNING**: any manually excluded nodes will be re-added. Use only when you intentionally want to sync structure (e.g. after adding a new top-level branch with many children).

> After `--rebuild`, manually remove any unwanted nodes from `kb_map.json` before committing.

> **Important**: This script handles structure only. It does NOT generate or update summaries. Summary writing is the agent's responsibility in Step 4.

#### Step 4 — Agent writes summaries (depth-based rules)

**This step is always performed by the AI agent**, not by any script. The agent reads `toplevel_dump.json` and `kb_map.json`, then writes summaries directly into `kb_map.json` using `multi_replace_string_in_file`.

##### Depth-based summary rules

| Node type | How to identify | Summary strategy |
|-----------|-----------------|------------------|
| **Branch node** (has children in kb_map.json) | `"children": [...]` is non-empty | Describe the scope/topic of the branch using its children as guide. Example: `"Surgical procedures in ophthalmology. instruments, corneal suture removal, TSCL, IOL, cataract"` |
| **Terminal node** (no children in kb_map.json) | `"children": []` is empty | Use medical domain knowledge + dump content to describe the specific concept. Example: `"Corneal suture removal technique. knot burial, loose suture, nylon, 10-0, slit lamp"` |

##### Process

1. Read `toplevel_dump.json` to understand each node's content (children titles, structured content).
2. Read `kb_map.json` to find nodes needing summaries (`summary == ""`  or low-quality placeholder summaries like `"Title: child1, child2"`).
3. For each node, write a summary following these rules:
   - **Format**: `[One-sentence description]. [keyword1, keyword2, ...]`
   - **Language**: English only
   - **Length**: ~300 chars max
   - **Content**: Include abbreviations, full names for major medical terms, disease names, procedure names
   - **Quality**: Must reflect medical domain knowledge, not just title word splitting
4. Write summaries into `kb_map.json` using `multi_replace_string_in_file`.
5. **Idempotency rule**: If a node already has a quality summary (not a placeholder), only update if the new content contains significantly different information.

**Target file:**
```
.github/skills/remnote-kb-navigation/kb_map.json
```

#### Step 5 — Verify

Spot-check 2-3 entries in `kb_map.json` to confirm:
- `remId` is correct
- `summary` field contains relevant medical keywords
- No hint/Chinese text in the summary field

## Maintaining the BRANCHES list

When a **new top-level branch** is added to RemNote (visible under root `Da8SsKWwuA9doqpsp`):

1. Add the node to `kb_map.json`:
   ```bash
   python .github/skills/kb-map-updater/build_kb_map.py --add <remId>
   ```
2. If it was placed as a top-level branch, update the `BRANCHES` list in `fetch_toplevel.py`:
   ```python
   ("NewBranchTitle", "newRemId"),
   ```
3. Re-run Steps 2–4 to fetch content and fill summaries.

When adding **child nodes** under an existing branch:
```bash
# Single or multiple:
python .github/skills/kb-map-updater/build_kb_map.py --add <remId1> <remId2>
```
Intermediate ancestors are auto-filled. No changes to `fetch_toplevel.py` needed for child nodes.

## Script locations

| Script | Purpose |
|--------|---------|
| `.github/skills/kb-map-updater/fetch_toplevel.py` | Fetch structured content from RemNote |
| `.github/skills/kb-map-updater/build_kb_map.py` | Build/update `kb_map.json` from dump |
| `toplevel_dump.json` | Raw dump output (workspace root, transient) |
| `.github/skills/remnote-kb-navigation/kb_map.json` | Source-of-truth KB index |

## Summary field specification

| Rule | Detail |
|------|--------|
| Language | English only |
| Content | One-sentence description; followed by keyword-dense list: disease names, procedure names, abbreviations, key concepts |
| Length | ~200 chars max |
| Format | `[Description]. [keyword1, keyword2, ...]` — description first, then flat comma/semicolon-separated keywords |
| Update | Only update if new information is present (idempotent) |
| Example | `Measurement of intraocular pressure using various methods. IOP, tonometry, applanation, POAG, PACG, NVG, gonioscopy, visual field, glaucoma surgery, SLT, trabeculectomy` |

