---
name: paragraph-to-claim
description: LLM skill to convert raw paragraphs into structured, atomic English claims suitable for KB deduplication. Outputs ClaimItem-compatible JSON with text, breadcrumb, entities, subject, predicate, object, numbers, negation, and claim_type.
---

# Paragraph-to-Claim Extraction Skill

Converts raw NotebookLM paragraphs into structured, atomic English claims ready for claim-level KB deduplication.

**Activation Criteria**: Called by `src/parsers/claim_extractor.py` during the claim-level sync pipeline (v0.4.0). Also invoked manually when a user says "extract claims from this paragraph" or "convert to claims".

---

## How to Use

This skill is invoked as an agent calling step. The agent performs claim extraction directly using the system prompt and rules below — no external LLM API call required.

### Activation
Invoke when:
- A user provides a paragraph and asks to "extract claims"
- `src/parsers/claim_extractor.py` delegates extraction to the agent
- The claim-level sync pipeline (v0.4.0) triggers Step 0 (paragraph-to-claim)

### Execution Steps

1. Receive the paragraph text and its breadcrumb context.
2. Apply the extraction rules below to decompose the paragraph into atomic claims.
3. Output a JSON array of `ClaimItem` objects.
4. Validate output against the quality rules before returning.

---

## Input Format

A paragraph with its current breadcrumb context:

```json
{
  "paragraph": "Selective laser trabeculoplasty (SLT) is a first-line treatment option for open-angle glaucoma. It reduces IOP by approximately 20~30%. It is repeatable and has a low complication rate compared to ALT.",
  "breadcrumb": "[Ophthalmology > Glaucoma > Treatment]",
  "breadcrumb_parts": ["Ophthalmology", "Glaucoma", "Treatment"]
}
```

---

## Extraction Rules

Apply these rules directly when performing claim extraction:

1. Each claim must express exactly **one** fact, relationship, or assertion.
2. Claims must be in **English only**, even if the source is in another language.
3. Preserve numeric values exactly (do not round or omit).
4. If a sentence is negated, set `negation: true`.
5. **Atomicity**: Split any sentence containing conjunctions ("and", "as well as") that bundle unrelated facts.
6. **Completeness**: `entities` must not be empty. If unclear, use the last item in `breadcrumb_parts` as the fallback entity.
7. **Numeric preservation**: If the source contains a number, it must appear in both `text` and `numbers` list.
8. **No inference**: Do not generate claims beyond what is stated.
9. **Breadcrumb injection**: Always carry the paragraph's breadcrumb into each claim — it disambiguates claims about similar concepts from different domains.
10. **Coreference resolution**: Resolve pronouns (e.g., "It reduces IOP" → "SLT reduces IOP") using context from the same paragraph.

Extract the following fields for each claim:
- `text`: Normalized claim as a complete English sentence.
- `text_original`: Exact source sentence from the paragraph (before normalization).
- `entities`: Top-level domain concept(s) — knowledge slot subjects (e.g., disease name, system name). Primary KB search keys.
- `subject`: Specific sub-item or procedure/concept under the entity. Fallback search key + lexical filter.
- `predicate`: Main verb or relational phrase.
- `object`: Value, outcome, or target of the predicate.
- `numbers`: All numeric values extracted (list of floats).
- `negation`: true if negated, false otherwise.
- `time_scope`: Temporal scope if present (e.g., "within 5 years"), or null.
- `claim_type`: One of: `definition`, `disease`, `capability`, `constraint`, `general`.

## Agent Prompt Template

When performing extraction, apply the rules above and output a JSON array of `ClaimItem` objects only. No explanation outside the JSON.

```
Paragraph: {paragraph}
Breadcrumb context: {breadcrumb}

Extract all atomic claims from this paragraph. Apply the extraction rules. Output a JSON array of ClaimItem objects only.
```

---

## Expected Output (ClaimItem JSON)

Incoming claims always have `rem_id: null`. The `rem_id` is only populated for KB candidate claims retrieved from RemNote.

```json
[
  {
    "claim_id": "inc_001",
    "rem_id": null,
    "text": "Selective laser trabeculoplasty is a first-line treatment option for open-angle glaucoma.",
    "text_original": "Selective laser trabeculoplasty (SLT) is a first-line treatment option for open-angle glaucoma.",
    "breadcrumb": "[Ophthalmology > Glaucoma > Treatment]",
    "breadcrumb_parts": ["Ophthalmology", "Glaucoma", "Treatment"],
    "entities": ["Glaucoma"],
    "subject": "Selective laser trabeculoplasty",
    "predicate": "is a first-line treatment option for",
    "object": "open-angle glaucoma",
    "numbers": [],
    "negation": false,
    "time_scope": null,
    "claim_type": "disease"
  },
  {
    "claim_id": "inc_002",
    "rem_id": null,
    "text": "Selective laser trabeculoplasty reduces IOP by approximately 20~30%.",
    "text_original": "It reduces IOP by approximately 20~30%.",
    "breadcrumb": "[Ophthalmology > Glaucoma > Treatment]",
    "breadcrumb_parts": ["Ophthalmology", "Glaucoma", "Treatment"],
    "entities": ["Glaucoma"],
    "subject": "Selective laser trabeculoplasty",
    "predicate": "reduces IOP by",
    "object": "approximately 20~30%",
    "numbers": [20, 30],
    "negation": false,
    "time_scope": null,
    "claim_type": "disease"
  },
  {
    "claim_id": "inc_003",
    "rem_id": null,
    "text": "Selective laser trabeculoplasty has a lower complication rate compared to ALT.",
    "text_original": "It is repeatable and has a low complication rate compared to ALT.",
    "breadcrumb": "[Ophthalmology > Glaucoma > Treatment]",
    "breadcrumb_parts": ["Ophthalmology", "Glaucoma", "Treatment"],
    "entities": ["Glaucoma"],
    "subject": "Selective laser trabeculoplasty",
    "predicate": "has lower complication rate compared to",
    "object": "ALT",
    "numbers": [],
    "negation": false,
    "time_scope": null,
    "claim_type": "disease"
  }
]
```

---

## Field Semantics Reference

| Field | Semantics |
|---|---|
| `claim_id` | Unique ID for this claim. Prefix `inc_` for incoming claims. |
| `rem_id` | Always `null` for incoming claims. Populated only when retrieving KB candidates from RemNote. |
| `text` | Normalized claim text. Used as NLI hypothesis/premise. |
| `text_original` | Raw source sentence. Preserved for traceability and debugging. |
| `breadcrumb` | Hierarchy path from `ast_parser.BreadcrumbIndex`. Format: `[Level1 > Level2 > Level3]`. Injected into NLI context prefix. |
| `breadcrumb_parts` | Parsed list of path parts. |
| `entities` | **Primary KB search key.** Top-level domain concept (disease name, system, component). Multiple entities allowed if claim spans domains. |
| `subject` | **Fallback search key + lexical filter.** The specific procedure, test, drug, or sub-concept. More specific than entities. |
| `predicate` | Action or relation expressed in the claim. Normalized to lowercase. |
| `object` | The value, outcome, or target of the predicate. |
| `numbers` | All numeric values extracted (list of floats). Used for slot comparison in disease claims. |
| `negation` | Whether the claim is negated. Critical for avoiding false-positive SKIP decisions. |
| `claim_type` | Semantic category. Determines whether slot-based comparison applies (see below). |

---

## Claim Types and Slot Eligibility

Slot-based comparison (in `src/routers/slot_matcher.py`) only applies to **disease** claims, which correspond to Specific Disease template slots in `remnote_style_transformation`:

| `claim_type` | Slot-based comparison | Notes |
|---|---|---|
| `definition` | No | Term definitions, abbreviations |
| `disease` | **Yes** | All Specific Disease knowledge: risk factors, signs, diagnosis thresholds, treatment outcomes, pathophysiology, epidemiology |
| `capability` | No | System or tool features |
| `constraint` | No | Limits, rules, permissions |
| `general` | No | Default / unclassified |

**Why `disease` is a single type**: All sub-categories (risk_factor, sign_symptom, diagnosis, treatment_outcome) share the same template slot structure from `remnote_style_transformation`. Slot-level differentiation is handled inside `slot_matcher.py` using the disease template headers, not claim_type.

---

## Quality Rules for LLM Output

Validate extracted claims before processing:

1. **Atomicity**: Reject claims with conjunctions ("and") that bundle multiple facts. Re-split them.
2. **Completeness**: `entities` must not be empty. If unclear, use the last item in `breadcrumb_parts` as fallback entity.
3. **Numeric preservation**: If the source contains a number, it must appear in the claim `text` and `numbers` list.
4. **No inference**: Do not generate claims beyond what is stated. No inferred negations or implied conditions.
5. **Breadcrumb injection**: Always inject breadcrumb into the LLM context — it disambiguates claims about similar concepts in different domains.

---

## Integration Notes

- **Called by**: `src/parsers/claim_extractor.py` — `extract_claims(paragraph, breadcrumb) -> List[ClaimItem]`
- **Output consumed by**: `src/pipeline/claim_retrieval.py` — uses `entities` for primary search, `subject` for lexical filter
- **Schema defined in**: `src/models/claim_models.py` — `ClaimItem` Pydantic model
- **Follows**: `ast_parser.py` breadcrumb generation (same format as `KnowledgeItem.new_breadcrumb`)

---

## Related Documents

- `docs/design/claim-level-knowledge-deduplication.md` — Full pipeline engineering spec
- `.github/skills/remnote_style_transformation/SKILL.md` — Disease template slots that define slot-eligible claim types
- `src/routers/nli_types.py` — NLIResult and FinalAction type definitions
- `src/pipeline/core.py` — KnowledgeItem and ActionType (downstream consumer)
