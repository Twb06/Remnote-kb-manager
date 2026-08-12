---
name: remnote_style_transformation
description: Formats concepts, summaries, or text into plain-text hierarchical lists tailored for RemNote import. Allows for strict Disease templates or flexible General Medical templates.
---

# RemNote Style Transformation Skill

This skill allows the Agent to structure learning concepts or analyze external URLs directly into RemNote-optimized flashcard formatting automatically.

## When to Use
- When the user asks to "organize this summary for RemNote".
- When the user asks to "extract RemNote flashcards from [URL]".
- When the user uses explicit language saying they want something processed and structured for RemNote.

## How to use

### Situation A: Text is already in the chat.
If the user provides raw text or previously generated concepts in the chat itself, and asks you to format it for RemNote: applies the `RemNote Formatting Rules` directly. No external tools needed. Output the result in a markdown block.

### Situation B: The user provides a URL or refers to external content
Execute the extraction script in the workspace that integrates NotebookLM with a specialized system prompt.
1. Make sure you are in the workspace `c:\Users\a0301\Documents\Projects\Antigravity_test`.
2. Run the script:
   ```powershell
   .\antigravitytest-env\Scripts\python src\extractor.py <URL> --notebook-name "Automated RemNote Extraction"
   ```
3. Read the output of the CLI execution.
4. Output the exact contents to the user inside a markdown code block so the user can easily copy and paste it into RemNote.

### Situation C: Template-based transformation
If the user provides or points to a specific template in the `templates/` directory:
1.  Read the content of the target template file (e.g., `templates/Glaucoma.md`).
2.  Analyze the hierarchy and "slot" structure of the template.
3.  Map the raw knowledge extracted from NotebookLM into the corresponding headers/slots of the template.
4.  Ensure strict adherence to `RemNote Formatting Rules`.

## RemNote Formatting Rules (IMPORTANT)

When formatting content meant for RemNote manually (Situation A), act as an expert in clinical medicine and note structuring:

### 1. Basic Formatting
- **Title Case**: All titles that is specific a disease or unique keyword (e.g., "Glaucoma" is a specific disease and doesn't use in other circumstances, and "false-positive rate" could be use globally under each disease or exams) must be Capitalized Title Case, and Alias or abbreviation could be provided after the full name (e.g., "Normal-Tension Glaucoma (NTG)", not "normal-tension glaucoma")
- **Flatten Hierarchy**: Remove all Markdown headers (`#`, `##`, `###`). Use indented unordered lists (`- `) exclusively. Top level has no indent, children get **exactly 2 spaces** per depth level
- **Tags Cleaning**: Strictly remove any HTML/XML like `<cite>` tags or similar tracking attributes
- **No Filler Text**: Under NO circumstances append conclusions, greetings, or post-generation questions. ONLY output the formatted plaintext inside a SINGLE `CODE BLOCK`

### 2. Flashcard Syntax (Critical - Match User's Style)
Apply flashcard markers strategically based on content type:

**Concept/Descriptor (Most Common)**:
- Use `:>` for definitions, key facts, or answers
- Example: `Normal IOP:>10~22 mmHg` or `Risk factor:>high IOP, resistance of optic nerve`

**Definition (::)**:
- Use `::` for term definitions or equivalences
- Example: `Applanation tonometry::gold standard` or `chronic CSCR::persistent subretinal fluid for >6 months`

**Cloze Deletion ({{}})**:
- Use for **numbers, percentages, key terms** that should be memorized
- Example: `{{10}}% per each 1 mmHg`, `Rates greater than {{15%}}`, `{{gaze tracker}}`
- With hint: `{{text}{({hint})}}` (例如 `{{10}}{({percentage})}`)

**Multi-line Cards**:
- Use `>>>` on parent for multi-line back content
- Example:
  ```
  - Aqueous humor production and drainage >>>
      - Trabecular meshwork (70-90%)
      - Uveoscleral outflow (10-30%)
  ```

**Basic Q&A**:
- Use `>>` for simple question-answer pairs when `:>` is not suitable
- Example: `Risk of VF progression increases {{10}}% per each 1 mmHg`

**Descriptor (;-)**:
- Use `;-` for brief descriptions or summaries under section headers
- Example: `[Overview]();-Elevated IOP (>21 mmHg) w/o optic nerve damage`

### 3. Medical Content Specifics

**Numbers and Ranges**:
- Use `~` for ranges: `10~22 mmHg` (not `-` or `to`)
- Always include units: `<555 μm`, `≥30`, `>24`
- Percentages in cloze: `{{15%}}`, `{{10}}%`

**Abbreviations**:
- Keep medical abbreviations standard: IOP, CCT, PSD, RNFL, OCT, FAG, ICG
- Define on first use if needed: `Normal-Tension Glaucoma (NTG)`

### 4. Structure Patterns from User Templates

**For Definitions**:
```markdown
- Normal IOP:>10~22 mmHg, 台灣人約10~20 mmHg
- Applanation tonometry::gold standard
```

**For Examinations/Findings**:
```markdown
- Signs >>>
  - round or oval **serous macular detachment**
  - **small, yellow subretinal deposits**
```

**For Risk Factors/Etiologies**:
```markdown
- Risk factor:>high IOP, resistance of optic nerve, impaired autoregulation
```

### 5. Output Format
- ALWAYS wrap final output in a single markdown code block (```)
- NO explanations, greetings, or follow-up questions outside the code block
- Preserve exact indentation (4 spaces per level)
- Keep line breaks for readability (one concept per line)

### General Template (General Medical concept or others)
- For general concepts, you do **not** need to strictly adhere to a rigid template. Check the content and dynamically create headings.
- You can freely adjust the indentations and hierarchical levels depending on the logic of the source material.

### Disease Template (Specific Disease)
- You **MUST** strictly adhere to the following list framework.
- If there is no information available for a specific heading, retain the heading but leave it blank (empty). Do not delete the heading.

- Overview
    - Presentation
    - Examination
    - Management
- Epidemiology
- Etiology
- Risk Factors
- General Pathology
- Pathophysiology
- History
- Physical examination
- Symptoms
- Signs
- Clinical diagnosis
- Diagnostic procedures
- Laboratory test
- Differential diagnosis
- General treatment
- Medical therapy
- Medical follow-up
- Surgery
- Complications
- Prognosis
