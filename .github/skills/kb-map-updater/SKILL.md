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
| User says "refresh the KB map" / periodic full resync | fetch → `--rebuild` or `--update-summaries` |
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

#### Step 3 — Build / update kb_map.json

`build_kb_map.py` supports two batch modes (in addition to `--add` above):

##### `--update-summaries` (default): preserve structure, update summaries only

```bash
python .github/skills/kb-map-updater/build_kb_map.py
# same as: python ... --update-summaries
```

**What it does:**
- Keeps the existing `kb_map.json` structure **exactly as-is** (nodes, order, hierarchy).
- Only updates the `summary` field for nodes whose `remId` appears in the dump.
- Nodes absent from the dump are left unchanged.
- **Nodes in the dump that are NOT already in `kb_map.json` are ignored** — the map is treated as a manually curated allowlist.

> Use this in normal refresh cycles. It respects any manual curation (e.g. nodes deliberately excluded from the map).

##### `--rebuild`: full structure rebuild from dump

```bash
python .github/skills/kb-map-updater/build_kb_map.py --rebuild
```

**What it does:**
- Completely rebuilds `kb_map.json` structure from `toplevel_dump.json`.
- All children come directly from RemNote (modulo empty-title and portal filtering).
- Preserves existing `summary` values by `remId`.
- **WARNING**: any manually excluded nodes will be re-added. Use only when you intentionally want to sync structure (e.g. after adding a new top-level branch with many children).

> After `--rebuild`, manually remove any unwanted nodes from `kb_map.json` before committing.

#### Step 4 — Generate / update summaries

For each node in `kb_map.json` where `summary == ""`, the agent should:

1. Read the node's content from `toplevel_dump.json` (`contentStructured` for branches, full structured tree for terminals).
2. Write a **concise English summary** that combines:
   - **First sentence**: Brief one-line description of the node's medical topic.
   - **Keywords**: Followed by comma/semicolon-separated list of key medical terms, disease names, procedure names, and abbreviations.
   - Example format: `Measurement of intraocular pressure. IOP, tonometry, applanation, POAG, glaucoma`
   - Max ~200 characters.
3. **Idempotency rule**: If a node already has a non-empty `summary`, only update if the new content contains significantly different or new information (new key terms, major topic change). Otherwise, leave unchanged.

Update `kb_map.json` directly using `multi_replace_string_in_file` or by rewriting the JSON.

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

