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
1. **Title Case**: All hierarchical section titles must be Capitalized Title Case.
2. **Flatten Hierarchy**: Remove all Markdown headers (`#`, `##`, `###`). Use indented unordered lists (`- `) exclusively. Top level has no indent, children get 4 spaces per depth level.
3. **Tags Cleaning**: Strictly remove any HTML/XML like `<cite>` tags or similar tracking attributes.
4. **Flashcard syntax**:
    *   Basic Q&A: `>>` or `==`.
    *   Cloze deletion: `{{text}}` or with hint `{{text}{({hint})}}`.
    *   Multi-line card: Use `>>>` on the parent, its indented children form the back.
    *   Concept/Descriptor: Concept `:>`; Descriptor `;-`.
5. **No Filler Text**: Under NO circumstances append conclusions, greetings, or post-generation questions. ONLY output the formatted plaintext inside a SINGLE `CODE BLOCK`.

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
