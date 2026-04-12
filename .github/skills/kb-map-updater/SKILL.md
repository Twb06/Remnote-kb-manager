---
name: kb-map-updater
description: Batch-fetches all RemNote top-level branches and regenerates English summary hints in kb_map.json. Use when the KB map needs a full refresh or after bulk content changes.
---

# KB Map Updater

Refreshes `remnote-kb-navigation/kb_map.json` by batch-reading every top-level branch from RemNote and updating concise English summaries optimized for agent map-lookup accuracy.

## When to use

- User says "update the KB map", "refresh hints", or "sync the top-level map"
- Another skill (e.g. `notebooklm-to-remnote`) has just written new content and the map needs a refresh
- A periodic full-resync of all branch summaries is desired

## Prerequisites

1. **remnote-cli daemon** must be running and connected (`remnote-cli status` → `connected: true`).
2. **Node.js** available (remnote-cli is a Node package at `./node_modules/remnote-cli`).
3. **Python 3** available in the activated virtual environment.

## Workflow

### Step 1 — Ensure daemon is connected

```bash
node ./node_modules/remnote-cli/dist/index.js status
```

If not connected:

```bash
node ./node_modules/remnote-cli/dist/index.js daemon start
# wait ~5s, then re-check status
```

### Step 2 — Run the fetch script

```bash
python .agents/skills/kb-map-updater/fetch_toplevel.py
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

### Step 3 — Build / update kb_map.json

`build_kb_map.py` supports two modes:

#### Default (`--update-summaries`): preserve structure, update summaries only

```bash
python .agents/skills/kb-map-updater/build_kb_map.py
# same as: python ... --update-summaries
```

**What it does:**
- Keeps the existing `kb_map.json` structure **exactly as-is** (nodes, order, hierarchy).
- Only updates the `summary` field for nodes whose `remId` appears in the dump.
- Nodes absent from the dump are left unchanged.
- **Nodes in the dump that are NOT already in `kb_map.json` are ignored** — the map is treated as a manually curated allowlist.

> Use this in normal refresh cycles. It respects any manual curation (e.g. nodes deliberately excluded from the map).

#### `--rebuild`: full structure rebuild from dump

```bash
python .agents/skills/kb-map-updater/build_kb_map.py --rebuild
```

**What it does:**
- Completely rebuilds `kb_map.json` structure from `toplevel_dump.json`.
- All children come directly from RemNote (modulo empty-title and portal filtering).
- Preserves existing `summary` values by `remId`.
- **WARNING**: any manually excluded nodes will be re-added. Use only when you intentionally want to sync structure (e.g. after adding a new top-level branch with many children).

> After `--rebuild`, manually remove any unwanted nodes from `kb_map.json` before committing.

#### `--add`: add nodes to the map (auto-placement + chain fill)

```bash
# Add a single node (auto-resolves position from RemNote parent chain):
python .agents/skills/kb-map-updater/build_kb_map.py --add <remId>

# Add multiple nodes at once:
python .agents/skills/kb-map-updater/build_kb_map.py --add <remId1> <remId2> <remId3>

# Add with a pre-filled summary (applies to target nodes only, not intermediates):
python .agents/skills/kb-map-updater/build_kb_map.py --add <remId> --summary "IOP measurement, tonometry"
```

**What it does:**
- Skips any `remId` already in `kb_map.json` (no error, just warns).
- For each remId, fetches `title`, `remType`, and `parentRemId` from RemNote via `remnote-cli read`.
- **Auto-placement**: walks up the ancestor chain until it finds a node already in the map or root.
- **Chain fill**: if intermediate ancestors are NOT in the map, they are automatically created along the path. This preserves the full hierarchy from the map ancestor down to the target node.
- If the chain reaches root → top-level branch (reminds to update `BRANCHES`).
- Writes updated `kb_map.json`.

**Parameters:**
| Flag | Required | Description |
|------|----------|-------------|
| `--add <remId> [...]` | Yes | One or more RemNote rem IDs to add |
| `--summary <text>` | No | Pre-fill summary for target nodes (English keywords); default: `""` |

### Step 4 — Generate / update summaries

For each node in `kb_map.json` where `summary == ""`, the agent should:

1. Read the node's content from `toplevel_dump.json` (`contentStructured` for branches, full structured tree for terminals).
2. Write a **concise English summary** (one line) that:
   - Lists key medical terms, disease names, and procedure names.
   - Uses abbreviations when well-known (e.g. AMD, CSNB, TED, IOL, ERG).
   - Is optimized for **keyword-based map lookup** (agent routing accuracy, not human prose).
   - Max ~200 characters.
3. **Idempotency rule**: If a node already has a non-empty `summary`, only update if the new content contains significantly different or new information (new key terms, major topic change). Otherwise, leave unchanged.

Update `kb_map.json` directly using `multi_replace_string_in_file` or by rewriting the JSON.

**Target file:**
```
.agents/skills/remnote-kb-navigation/kb_map.json
```

### Step 5 — Verify

Spot-check 2-3 entries in `kb_map.json` to confirm:
- `remId` is correct
- `summary` field contains relevant medical keywords
- No hint/Chinese text in the summary field

## Maintaining the BRANCHES list

When a **new top-level branch** is added to RemNote (visible under root `Da8SsKWwuA9doqpsp`):

1. Add the node to `kb_map.json`:
   ```bash
   python .agents/skills/kb-map-updater/build_kb_map.py --add <remId>
   ```
2. If it was placed as a top-level branch, update the `BRANCHES` list in `fetch_toplevel.py`:
   ```python
   ("NewBranchTitle", "newRemId"),
   ```
3. Re-run Steps 2–4 to fetch content and fill summaries.

When adding **child nodes** under an existing branch:
```bash
# Single or multiple:
python .agents/skills/kb-map-updater/build_kb_map.py --add <remId1> <remId2>
```
Intermediate ancestors are auto-filled. No changes to `fetch_toplevel.py` needed for child nodes.

## Script locations

| Script | Purpose |
|--------|---------|
| `.agents/skills/kb-map-updater/fetch_toplevel.py` | Fetch structured content from RemNote |
| `.agents/skills/kb-map-updater/build_kb_map.py` | Build/update `kb_map.json` from dump |
| `toplevel_dump.json` | Raw dump output (workspace root, transient) |
| `.agents/skills/remnote-kb-navigation/kb_map.json` | Source-of-truth KB map |

## Summary field specification

| Rule | Detail |
|------|--------|
| Language | English only |
| Content | Keyword-dense: disease names, procedure names, abbreviations, key concepts |
| Length | ~200 chars max |
| Format | Flat comma/semicolon-separated keywords — NOT prose sentences |
| Update | Only update if new information is present (idempotent) |
| Example | `IOP, POAG, PACG, NVG, GON, gonioscopy, visual field, glaucoma surgery, SLT, trabeculectomy` |

