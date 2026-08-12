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



class RealNLIRouter:
    """Lazy loading proxy for RealNLIRouter to avoid heavy PyTorch/Transformers imports at startup."""
    def __new__(cls, *args, **kwargs):
        from src.routers.nli_bart import RealNLIRouter as ActualRealNLIRouter
        return ActualRealNLIRouter(*args, **kwargs)


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
            print(f"  [{case.action}] {case.term} - {case.nli_reason}")

    return result


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="NLI Pipeline v0.3 — NotebookLM → RemNote knowledge sync"
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="legacy",
        choices=["legacy", "rag-sync", "export-kb"],
        help="Execution mode: 'legacy', 'rag-sync' or 'export-kb'",
    )
    parser.add_argument(
        "--topic",
        type=str,
        default="",
        help="Topic for RAG sync mode",
    )
    parser.add_argument(
        "--folder-id",
        type=str,
        default="",
        help="Target RemNote folder ID for RAG sync mode",
    )
    parser.add_argument(
        "--is-disease",
        action="store_true",
        help="Whether the topic is a disease (enables slot matching in RAG mode)",
    )
    parser.add_argument(
        "--source-notebook",
        type=str,
        default="",
        help="Source NotebookLM ID to extract knowledge from",
    )
    parser.add_argument(
        "--remnote-notebook",
        type=str,
        default="",
        help="RemNote NotebookLM ID containing the RemNote KB",
    )
    parser.add_argument(
        "--query",
        type=str,
        default="",
        help="Query to ask the source notebook",
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
        default=None,
        help="Output file path (default: pipeline_output.json for sync, remnote_export_{topic}.md for export)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned actions without writing output file",
    )
    parser.add_argument(
        "--gaps-file",
        type=str,
        default=None,
        help="Path to a local markdown file containing gaps/updates tree to bypass NotebookLM query",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    if args.mode == "export-kb":
        from src.pipeline.remnote_client import RemNoteClient
        if not args.folder_id:
            print("[main] ERROR: --folder-id is required for export-kb mode", file=sys.stderr)
            return 1
        output_file = args.output
        if not output_file:
            if args.topic:
                output_file = Path(f"remnote_export_{args.topic}.md")
            else:
                output_file = Path("remnote_export.md")
        client = RemNoteClient(dry_run=args.dry_run)
        print(f"Exporting RemNote folder {args.folder_id}...")
        kb_markdown = client.read_markdown(args.folder_id)
        if kb_markdown:
            output_file.write_text(kb_markdown, encoding="utf-8")
            print(f"Successfully exported to {output_file}")
            return 0
        else:
            print("ERROR: Failed to export RemNote folder", file=sys.stderr)
            return 1

    if args.mode == "rag-sync":
        from src.pipeline.rag_pipeline import RAGPipeline
        if not args.topic or not args.folder_id:
            print("[main] ERROR: --topic and --folder-id are required for rag-sync mode", file=sys.stderr)
            return 1
        
        import asyncio
        pipeline = RAGPipeline(dry_run=args.dry_run, is_disease=args.is_disease)
        asyncio.run(pipeline.execute(
            target_folder_id=args.folder_id, 
            topic=args.topic,
            source_notebook_id=args.source_notebook,
            remnote_notebook_id=args.remnote_notebook,
            query=args.query,
            gaps_file=args.gaps_file
        ))
        return 0

    # Validate inputs
    if not args.answer_file.exists():
        print(f"[main] ERROR: answer file not found: {args.answer_file}", file=sys.stderr)
        return 1

    if not args.kb_map.exists():
        print(f"[main] ERROR: kb_map file not found: {args.kb_map}", file=sys.stderr)
        return 1

    # Load inputs
    answer_lines = _parse_answer_lines(args.answer_file)
    kb_map_data = json.loads(args.kb_map.read_text(encoding="utf-8-sig"))
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
