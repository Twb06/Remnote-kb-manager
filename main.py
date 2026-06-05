"""
main.py - NLI Pipeline v0.3 Entry Point

Usage:
    python main.py [options]

Options:
    --answer-file   Path to the answer/content markdown file
                    (default: .agents/tmp/answer.md)
    --kb-map        Path to the RemNote kb_map.json navigation file
                    (default: .github/skills/remnote-kb-navigation/kb_map.json)
    --output        Path to write pipeline_output.json
                    (default: pipeline_output.json)
    --dry-run       Print planned actions without writing output file
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

from src.pipeline.core import PipelineV6
from src.routers.nli_bart import RealNLIRouter


# ---------------------------------------------------------------------------
# Input parsing helpers
# ---------------------------------------------------------------------------

def _parse_answer_lines(answer_path: Path) -> List[str]:
    """Read answer.md and return non-empty lines (preserving indentation)."""
    text = answer_path.read_text(encoding="utf-8")
    lines = []
    for line in text.splitlines():
        # Skip top-level header markers but keep all content lines
        if line.strip().startswith("## "):
            continue
        lines.append(line)
    # Strip trailing blank lines
    while lines and not lines[-1].strip():
        lines.pop()
    return lines


def _flatten_kb_map(kb_map_data: dict) -> Dict[str, Optional[str]]:
    """
    Flatten the nested kb_map.json structure into {title: remId} dict.
    Entries without a remId are mapped to None.
    """
    flat: Dict[str, Optional[str]] = {}

    def _walk(node: dict) -> None:
        title = node.get("title")
        rem_id = node.get("remId") or node.get("id")
        if title:
            flat[title] = rem_id or None
        for child in node.get("children", []):
            _walk(child)

    root = kb_map_data.get("root", {})
    if root:
        _walk(root)
    for branch in kb_map_data.get("branches", []):
        _walk(branch)

    return flat


def _build_context_trees(kb_map_data: dict) -> dict:
    """
    Build context_trees expected by PipelineV6 from the kb_map.json branches.
    Each top-level branch becomes one tree keyed by its remId.
    """
    trees = {}
    for i, branch in enumerate(kb_map_data.get("branches", [])):
        key = branch.get("remId") or f"tree_{i}"
        trees[key] = {
            "id": branch.get("remId"),
            "title": branch.get("title", ""),
            "content": branch.get("summary", ""),
            "children": [
                {
                    "id": c.get("remId"),
                    "title": c.get("title", ""),
                    "content": c.get("summary", ""),
                    "children": []
                }
                for c in branch.get("children", [])
            ]
        }
    return trees


# ---------------------------------------------------------------------------
# Pipeline runner
# ---------------------------------------------------------------------------

def run_pipeline(
    answer_lines: List[str],
    kb_map: Dict[str, Optional[str]],
    context_trees: dict,
    dry_run: bool = False,
) -> dict:
    """Execute the full v0.3 pipeline and return the result dict."""
    print(f"\n[main] Input lines  : {len(answer_lines)}")
    print(f"[main] KB map entries: {len(kb_map)}")
    print(f"[main] Context trees : {len(context_trees)}")

    pipeline = PipelineV6()
    search_terms = list(kb_map.keys())

    knowledge_items = pipeline.execute_pipeline(
        answer_lines,
        search_terms,
        kb_map,
        context_trees,
    )

    router = RealNLIRouter()
    router_result = router.apply_nli_routing(knowledge_items)

    stats = router_result["statistics"]
    total = stats["created"] + stats["updated"] + stats["skipped"] + stats["requires_llm"]
    auto_rate = (total - stats["requires_llm"]) / total if total > 0 else 1.0

    result = {
        "pipeline_version": "v0.3",
        "execution_summary": {
            "total_knowledge_items": len(knowledge_items),
            "final_actions": len(router_result["final_actions"]),
            "llm_interventions": len(router_result["requires_llm_intervention"]),
        },
        "pipeline_statistics": pipeline.get_statistics(),
        "nli_statistics": stats,
        "auto_processing_rate": round(auto_rate, 4),
        "detailed_output": {
            "final_actions": [a.to_dict() for a in router_result["final_actions"]],
            "llm_interventions": [
                c.to_dict() for c in router_result["requires_llm_intervention"]
            ],
        },
    }

    # Console summary
    print(f"\n[main] --- Results ---")
    print(f"  Created         : {stats['created']}")
    print(f"  Updated         : {stats['updated']}")
    print(f"  Skipped         : {stats['skipped']}")
    print(f"  Requires LLM    : {stats['requires_llm']}")
    print(f"  Auto rate       : {auto_rate:.1%}")
    print(f"  Avg NLI conf.   : {stats['avg_nli_confidence']:.2%}")

    if router_result["requires_llm_intervention"]:
        print(f"\n[main] LLM intervention cases:")
        for case in router_result["requires_llm_intervention"]:
            print(f"  [{case.type}] {case.term} — {case.reason}")

    return result


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="NLI Pipeline v0.3 — NotebookLM → RemNote knowledge sync"
    )
    parser.add_argument(
        "--answer-file",
        type=Path,
        default=Path(".agents/tmp/answer.md"),
        help="Hierarchical markdown answer file from NotebookLM (default: .agents/tmp/answer.md)",
    )
    parser.add_argument(
        "--kb-map",
        type=Path,
        default=Path(".github/skills/remnote-kb-navigation/kb_map.json"),
        help="RemNote navigation kb_map.json (default: .github/skills/remnote-kb-navigation/kb_map.json)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("pipeline_output.json"),
        help="Output JSON file path (default: pipeline_output.json)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned actions without writing output file",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    # Validate inputs
    if not args.answer_file.exists():
        print(f"[main] ERROR: answer file not found: {args.answer_file}", file=sys.stderr)
        return 1

    if not args.kb_map.exists():
        print(f"[main] ERROR: kb_map file not found: {args.kb_map}", file=sys.stderr)
        return 1

    # Load inputs
    answer_lines = _parse_answer_lines(args.answer_file)
    kb_map_data = json.loads(args.kb_map.read_text(encoding="utf-8"))
    kb_map = _flatten_kb_map(kb_map_data)
    context_trees = _build_context_trees(kb_map_data)

    # Run pipeline
    result = run_pipeline(answer_lines, kb_map, context_trees, dry_run=args.dry_run)

    # Write output
    if not args.dry_run:
        args.output.write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"\n[main] Output written to: {args.output}")
    else:
        print("\n[main] Dry-run mode — output not written.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
