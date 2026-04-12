---
name: 'notebooklm-to-remnote'
description: 'Seamlessly transfer knowledge from NotebookLM to RemNote with intelligent organization and deduplication using remnote-cli.'
---

# NotebookLM to RemNote Knowledge Flow

**Activation Criteria**: Intent involving "study", "read book", "extract knowledge", "NotebookLM to RemNote", or keywords "notebook", "remnote", "workflow".

Follow these steps to extract research from NotebookLM and integrate it precisely into your RemNote knowledge base.

## 1. Initialize Contexts
Ensure both systems are ready using the unified scripts.
- Use `/notebooklm_init.md` to run `bash scripts/notebooklm_init.sh`.
- Use `/remnote_init.md` to run `bash scripts/remnote_init.sh`.
- Whenever which system failed to login or initiate, retry the above method twich, if still error, let the user manually check or login.

## 2. Generate/Extract Knowledge from NotebookLM
Decide what information to transfer.
- Ask a question to the specified notebook, sending input in English only.
- **Prompt Requirement**: NotebookLM must return exactly two main headers: `## overview` and `## answer`.
- **`## overview`**: Must contain the topic and its specific subtopics.
  - Subtopics should be specific entities/terms (e.g., medical terms like "10-2 pattern", "24-2 pattern").
  - **Crucial**: Do NOT include sentences or generic category headers like "Diagnosis", "Treatment", or "Management" under subtopics within overview.
- **`## answer`**: Must contain a detailed hierarchical markdown list answering the topic.
```bash
./antigravitytest-env/Scripts/notebooklm ask "user question...
Please provide two main sections in your response:

## overview
List the main topic and its specific subtopics.
- The subtopics MUST be specific terms or entities (e.g., medical terms like '10-2 pattern', '24-2 pattern').
- Do NOT use sentences or generic category headers (e.g., avoid 'Diagnosis', 'Treatment', 'Management', 'Overview' etc.).
- Format as a simple markdown list.

## answer
Provide the detailed answer for the topic and its subtopics as a detailed hierarchical markdown list.
"
```
- NotebookLM may take 30s to 2m to respond. Wait for the full output.

## 3. Stage Files for Pipeline
Save the NotebookLM output into separate files for the pipeline script.
- Save the `## overview` section to `.agents/tmp/overview.md`
- Save the `## answer` section to `.agents/tmp/answer.md`

## 4. Run Smart Pipeline (`smart_logic_v5.py`)
This script handles search, mapping, reading, and deduplication in a single call (zero agent token cost).
```bash
python smart_logic_v5.py \
  --skill-map ".agents/skills/remnote-kb-navigation/kb_map.json" \
  --overview-file ".agents/tmp/overview.md" \
  --content-file ".agents/tmp/answer.md"
```
**What the script does internally (Steps A–E):**
  - **A. Map Lookup**: Reads `kb_map.json` and matches terms against all node titles and summaries.
  - **B. Normalized Search**: Calls `npx remnote-cli search` for unmapped terms, scores results.
  - **C. Context Read**: Single `read --depth 6` on the main topic (or first found subtopic).
  - **D. Parent/Sibling Mapping**: Maps missing terms to create under topic or as siblings.
  - **E. Embedding Intersection**: Uses `sentence-transformers` to classify each knowledge line as MATCH (skip), NEW (keep), or AMBIGUOUS (needs agent review).

**Script output** is a JSON with three keys:
  - `auto_actions`: Ready-to-execute actions (UPDATE or CREATE) with filtered delta content.
  - `ambiguous`: Items the agent must review (similarity 0.3–0.8).
  - `skipped`: Duplicate knowledge that was auto-filtered.

## 5. Agent Review & Format Transformation
- **Review Ambiguous Items**: For each item in `ambiguous`, judge whether it is truly new or duplicate. Move confirmed-new items to `auto_actions`.
- **Format Transformation**: Apply `remnote_style_transformation` skill to all delta content (from `auto_actions`) in one batch before staging.
- **Staging**: Save each action's content into `.agents/tmp/` (e.g., `.agents/tmp/delta_1.md`, `.agents/tmp/new_1.md`).

## 6. Execution via CLI
Commit the changes using RemNote CLI commands.
- **For UPDATE actions**: `npx remnote-cli update <remId> --append-file ".agents/tmp/delta_N.md" --add-tags "AI generated"`
- **For CREATE actions**: `npx remnote-cli create --parent <parentRemId> --title "Term" --content-file ".agents/tmp/new_N.md"`
- **Rule**: Never delete or overwrite. Always append or create to preserve flashcard metadata.
- **Rule**: Always store content in `.agents/tmp/` files to avoid CLI escaping issues.

## 7. Update Navigation Map
Maintain the navigation system.
- **Significance Rule**: A new sub-branch is "significant" if a sibling topic already exists in `kb_map.json` under the same parent branch.
- **Map Update**: If significant, add the new entry (`remId`, `title`, `summary`) to the correct `children` array in `kb_map.json`.