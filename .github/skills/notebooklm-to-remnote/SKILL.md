---
name: 'notebooklm-to-remnote'
description: 'Seamlessly transfer knowledge from NotebookLM to RemNote with intelligent organization and deduplication using remnote-cli (Fallback RAG-Sync Workflow).'
---

# NotebookLM to RemNote Fallback RAG-Sync Flow

**Activation Criteria**: Intent involving "study", "read book", "extract knowledge", "NotebookLM to RemNote", or keywords "notebook", "remnote", "workflow" when executing a purely agent-guided sync without invoking the main Python pipeline script.

Follow these steps to extract research from NotebookLM and integrate it precisely into your RemNote knowledge base.

---

## 1. Initialize Contexts
Ensure both systems are ready using the unified scripts.
- Run `/notebooklm_init` to run `bash scripts/notebooklm_init.sh`.
- Run `/remnote_init` to run `bash scripts/remnote_init.sh`.
- If either initialization fails, retry once. If errors persist, prompt the user.

---

## 2. Load Configuration & Parameters
1. Read the configuration file `.github/skills/notebooklm-to-remnote/config.json` inside the workspace `c:\Users\a0301\Documents\Projects\Antigravity_test` to load:
   - `target_folder_id`: The destination RemNote folder ID
   - `source_notebook_id`: NotebookLM ID containing reference materials
   - `targeted_notebook_id`: NotebookLM ID used for RAG gap-detection
2. Ask the user for the `<topic>` to synchronize (e.g., `Herpes Zoster Ophthalmicus (HZO)` or `Malignant Glaucoma`).

---

## 3. Extract Knowledge from Source Notebook (Phase 0a)
Extract the external research knowledge from the Source Notebook:
1. Set the active notebook to the Source Notebook:
   ```powershell
   .\antigravitytest-env\Scripts\notebooklm.exe use <source_notebook_id>
   ```
2. Query the notebook for the topic:
   ```powershell
   .\antigravitytest-env\Scripts\notebooklm.exe ask "Tell me everything about <topic> including clinical courses, examinations, and management." --json
   ```
3. Read the output. Extract the `text` field from the returned JSON envelope and save it to `.agents/tmp/new_knowledge_<topic>.md`.

---

## 4. Deduplicate & Upload Sources to Targeted Notebook (Phase 0b)
1. Switch to the Targeted Notebook:
   ```powershell
   .\antigravitytest-env\Scripts\notebooklm.exe use <targeted_notebook_id>
   ```
2. Retrieve the existing source list in targeted notebook:
   ```powershell
   .\antigravitytest-env\Scripts\notebooklm.exe source list --json
   ```
3. **Deduplicate**: Search the source list for any sources with the titles `remnote_export_<topic>.md` or `new_knowledge_<topic>.md`. For each duplicate found, delete it:
   ```powershell
   .\antigravitytest-env\Scripts\notebooklm.exe source delete <source_id> -y
   ```
4. **Upload Sources**:
   - Check if a local `remnote_export_<topic>.md` (previously exported by the user) exists. If it does, upload it:
     ```powershell
     .\antigravitytest-env\Scripts\notebooklm.exe source add remnote_export_<topic>.md --title "remnote_export_<topic>.md"
     ```
   - Upload the new knowledge extracted in step 3:
     ```powershell
     .\antigravitytest-env\Scripts\notebooklm.exe source add .agents/tmp/new_knowledge_<topic>.md --title "new_knowledge_<topic>.md"
     ```
5. **Wait for Indexing**: Check status and wait for both sources to be ready:
   ```powershell
   .\antigravitytest-env\Scripts\notebooklm.exe source wait <source_id> --timeout 120
   ```

---

## 5. Query Gaps (Phase 1)
1. Query the Targeted Notebook using this precise gap-detection prompt. Save this prompt text into `.agents/tmp/gap_prompt.txt`:
   ```
   Based on the existing 'remnote_export_<topic>.md' source, compare it against the new information provided in the source titled 'new_knowledge_<topic>.md'.
   Identify knowledge gaps and items needing updates.

   Generate a SINGLE hierarchical markdown list representing the merged knowledge tree.
   For each fact or note, you MUST prefix the item with '(create)' or '(update)' respectively, and format it using RemNote Flashcard syntax rules:
   1. Concept/Descriptor: Use ':>' (e.g., 'Normal IOP:>10~22 mmHg')
   2. Definition: Use '::' (e.g., 'Applanation tonometry::gold standard')
   3. Cloze Deletion: Use '{{keyword}}' for critical numbers, percentages, or terms.
   4. If it's a new fact, prefix with '(create)'
   5. If it's an update to an existing item, prefix with '(update)'

   When listing gaps, you must construct the hierarchical path by 'grafting' (appending) the new facts under the existing categories found in 'remnote_export_<topic>.md'. Do not create new top-level categories if they can logically fit under the existing ones. Crucially, when constructing this hierarchical path, you MUST NOT omit or skip any existing parent/category names from 'remnote_export_<topic>.md'. Every single level of the existing hierarchy must be fully preserved and listed step-by-step; otherwise, automated path matching will fail.

   Example output format:
   - Herpes Zoster Ophthalmicus (HZO)
     - Acute disease
       - Clinical course
         - (create) Zoster Sine Herpete::In some cases, patients can experience HZO and dermatomal pain without ever developing the classic vesicular rash
     - Treatment
       - (update) Standard treatment:>Valacyclovir 1g TID for 7~10 days
   ```
2. Execute the query:
   ```powershell
   .\antigravitytest-env\Scripts\notebooklm.exe ask --prompt-file .agents/tmp/gap_prompt.txt --json
   ```
3. Extract the `text` field from the output. Parse the hierarchical structure:
   - Identify lines containing `(create)` as **Gap items**.
   - Identify lines containing `(update)` as **Update items**.
   - Keep track of the full parent breadcrumb list leading to each leaf item.

---

## 6. Mode Selection (Agent Decision)
Analyze the `<topic>` input cognitively:
- **Disease Mode**: If the topic represents a specific, single disease entity (e.g., `Herpes Zoster Ophthalmicus (HZO)` or `Malignant Glaucoma`), apply **Section 7: Disease Mode Sync**.
- **General Mode**: If the topic represents a general field of study or a collection of topics (e.g., `Glaucoma` or `Ophthalmic Examination`), apply **Section 8: General Mode Sync**.

---

## 7. Disease Mode Sync (v0.5.1 Framework)
To prevent orphaned folders and follow RemNote structured templates:
1. **Search for Disease Node**:
   Search for `<topic>` in the target folder:
   ```powershell
   npx remnote-cli search "<topic>" --parent-id <target_folder_id> --json
   ```
2. **If NOT Exists (Journal Fallback)**:
   - To avoid polluting the core folder hierarchy with scattered folders, aggregate all gap and update facts into a structured markdown document.
   - Format the markdown with a `# <topic> Gaps` header.
   - Save this to `.agents/tmp/journal_fallback.md`.
   - Append this markdown chunk directly to today's Daily Document:
     ```powershell
     npx remnote-cli journal --content-file .agents/tmp/journal_fallback.md
     ```
   - Stop execution for this topic.
3. **If Exists (Template Sync)**:
   - Save the disease Rem ID as `<disease_rem_id>`.
   - Ensure the Medical Disease Template is tagged:
     ```powershell
     npx remnote-cli update-tags <disease_rem_id> --add-tag-ids "JC5AH8TyoHJTPwuZH"
     ```
   - **List Children Properties**: Retrieve auto-instantiated properties of the template:
     ```powershell
     npx remnote-cli list-children <disease_rem_id> --limit 50 --json
     ```
     Inspect the output to map property names (e.g., `Definition`, `Presentation`, `Treatment`, `Prognosis`, `Signs`, `Symptoms`) to their respective `remId` values.
   - **Slot Matching**: Group the parsed gap/update items cognitively by matching their breadcrumbs/subtopics to the template properties:
     - `Clinical course`, `Acute disease` -> `Presentation` property
     - `Standard treatment`, `Management`, `Therapy` -> `Treatment` property
     - `Findings`, `Signs` -> `Signs` property
     - `Symptoms` -> `Symptoms` property
     - Otherwise, map to the closest matching property.
   - **Write Properties**:
     For each grouped property, determine if the value contains multiple lines or bullet points:
     - **For Single-line properties**:
       Write directly using `set-property`:
       ```powershell
       npx remnote-cli set-property <disease_rem_id> --tag-id "JC5AH8TyoHJTPwuZH" --property-id <property_rem_id> --value "single line text" --text
       ```
     - **For Multiline/List properties (CRITICAL)**:
       Due to CLI constraints, `set-property` strips newlines and truncates multiline text. Instead, use `insert-children` directly on the instantiated property node:
       1. Find the `remId` of the instantiated property (by running `list-children <disease_rem_id>`).
       2. **Do NOT update or clear the title of the property Rem** (e.g. do not call `update <instantiated_property_rem_id> --title ...`), as this will overwrite the dynamic template link and break the template reference.
       3. Directly insert each bullet point using `insert-children` under that property Rem. Keep `--position last` BEFORE `--content` to prevent CLI parsing issues:
          ```powershell
          npx remnote-cli insert-children <instantiated_property_rem_id> --position last --content "- Concept :: Fact details"
          ```

---

## 8. General Mode Sync (Phase 2-4)
To map to unstructured parent-child Rems:
1. **ID Resolution via Direct Parent Search**:
   For each gap/update item, parse the breadcrumb path (e.g., `Ophthalmology > Glaucoma > Types > POAG`):
   - Perform a Direct Deepest Parent Search for the immediate parent (e.g., `Types`):
     ```powershell
     npx remnote-cli search "Types" --parent-id <target_folder_id> --json
     ```
   - Cross-validate the results: check if the matched node's `parentTitle` matches the ancestor category (`Glaucoma`).
   - If a match is found, store it as `<parent_rem_id>`.
   - **Fallback**: If direct search fails, resolve the path top-down from `<target_folder_id>`, searching for each folder name, and creating it if missing:
     ```powershell
     npx remnote-cli create "<category_name>" --parent-id <current_parent_id>
     ```
2. **Execute Actions**:
   - **For Gap (CREATE) Actions**:
     - Format the fact text according to `remnote_style_transformation` rules.
     - Save to `.agents/tmp/create_fact.md`.
     - Write under the resolved parent ID:
       ```powershell
       npx remnote-cli create --content-file .agents/tmp/create_fact.md --parent-id <parent_rem_id>
       ```
   - **For Update (UPDATE) Actions**:
     - Search for the existing term to get its Rem ID:
       ```powershell
       npx remnote-cli search "<term>" --parent-id <target_folder_id> --json
       ```
     - If the term's Rem ID `<term_rem_id>` is resolved:
       - Format the update fact and save to `.agents/tmp/update_fact.md`.
       - Append to the existing Rem:
         ```powershell
         npx remnote-cli insert-children <term_rem_id> --content-file .agents/tmp/update_fact.md --position last
         ```
     - If `<term_rem_id>` cannot be resolved, fallback to **CREATE** under `<parent_rem_id>`.

---

## 9. Update Navigation Map
- If a new sub-branch was created in General Mode, and its parent exists in the navigation map `c:\Users\a0301\Documents\Projects\Antigravity_test\.github\skills\remnote-kb-navigation\SKILL.md`, synchronize the new branch's title and ID back into the navigation map for future sessions.