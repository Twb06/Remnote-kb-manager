import json
import subprocess
import sys
import re
from pathlib import Path

# Paths
PIPELINE_OUTPUT = Path("pipeline_output.json")
KB_MAP_PATH = Path(".github/skills/remnote-kb-navigation/kb_map.json")
TMP_DIR = Path(".agents/tmp")
TMP_DIR.mkdir(parents=True, exist_ok=True)

ROOT_REM_ID = "Da8SsKWwuA9doqpsp"

def run_cli(command: list[str]) -> dict:
    """Run remnote-cli subprocess and return parsed JSON."""
    full_cmd = ["npx", "remnote-cli", "--json"] + command
    try:
        result = subprocess.run(
            full_cmd, capture_output=True, text=True,
            shell=True, encoding='utf-8', errors='replace'
        )
        if result.returncode != 0:
            return {"error": result.stderr.strip() or f"Exit code {result.returncode}"}
        output = result.stdout.strip()
        json_match = re.search(r'(\{.*\}|\[.*\])', output, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))
        return {"error": "No JSON found in output", "raw": output}
    except Exception as e:
        return {"error": str(e)}

def parse_term(term: str):
    """Split '**Title:** Description' into (Title, Description)."""
    match = re.match(r'^\*\*([^*]+)\*\*[:\-]?\s*(.*)', term)
    if match:
        title = match.group(1).strip()
        desc = match.group(2).strip()
        return title, desc
    return term, ""

def main():
    if not PIPELINE_OUTPUT.exists():
        print(f"Error: {PIPELINE_OUTPUT} not found.")
        sys.exit(1)

    print("Loading pipeline output...")
    data = json.loads(PIPELINE_OUTPUT.read_text(encoding="utf-8"))
    actions = data.get("detailed_output", {}).get("final_actions", [])
    
    # Flatten existing kb_map for initial resolutions
    print("Loading KB map...")
    kb_map_data = json.loads(KB_MAP_PATH.read_text(encoding="utf-8-sig"))
    
    term_to_id = {}
    
    def _walk(node: dict) -> None:
        title = node.get("title")
        rem_id = node.get("remId") or node.get("id")
        if title and rem_id:
            term_to_id[title] = rem_id
        for child in node.get("children", []):
            _walk(child)

    _walk(kb_map_data.get("root", {}))
    for branch in kb_map_data.get("branches", []):
        _walk(branch)

    # Add resolved rem_ids from pipeline output
    for action in actions:
        term = action.get("term")
        rem_id = action.get("rem_id")
        if term and rem_id:
            term_to_id[term] = rem_id
            
    print(f"Initially resolved Rem IDs: {len(term_to_id)}")

    created_count = 0
    updated_count = 0
    skipped_count = 0

    print("\nExecuting actions...")
    for idx, action in enumerate(actions):
        action_type = action.get("action")
        term = action.get("term")
        rem_id = action.get("rem_id")
        new_breadcrumb = action.get("new_breadcrumb", "")

        # Parse breadcrumb to find parent
        parent_rem_id = ROOT_REM_ID
        clean_bc = new_breadcrumb.strip("[]")
        if " > " in clean_bc:
            parts = [p.strip() for p in clean_bc.split(" > ")]
            if len(parts) > 1:
                # Parent is the second-to-last part
                parent_term = parts[-2]
                parent_rem_id = term_to_id.get(parent_term, ROOT_REM_ID)

        print(f"\n[{idx+1}/{len(actions)}] Processing {action_type} for term: '{term[:60]}...'")
        print(f"  Parent resolved: {parent_rem_id}")

        if action_type == "SKIP":
            print("  Skipped.")
            skipped_count += 1
            continue

        elif action_type == "UPDATE":
            title, desc = parse_term(term)
            if rem_id:
                # Update title if it has changed
                print(f"  Updating title of {rem_id} to '{title}'...")
                res = run_cli(["update", rem_id, "--title", title])
                if "error" in res:
                    print(f"  Warning: Title update failed: {res['error']}")
                
                # Append description/content if any
                if desc:
                    temp_file = TMP_DIR / f"delta_{idx}.md"
                    temp_file.write_text(f"- {desc}", encoding="utf-8")
                    print(f"  Appending description content to {rem_id}...")
                    res = run_cli(["update", rem_id, "--append-file", str(temp_file)])
                    if "error" in res:
                        print(f"  Error appending content: {res['error']}")
                    else:
                        updated_count += 1
                else:
                    updated_count += 1
            else:
                print("  Warning: UPDATE action has no rem_id!")

        elif action_type == "CREATE":
            title, desc = parse_term(term)
            
            # Format and save description content to file if it exists
            content_args = []
            if desc:
                # Clean references like [1], [2] or apply concept syntax ':>' if appropriate
                # In this case, we just save it as a clean list item
                temp_file = TMP_DIR / f"new_{idx}.md"
                # If there are sub-items under this term, we can write them.
                # Since we process flat, the children are separate CREATE actions, so we just write this node's direct description.
                temp_file.write_text(f"- {desc}", encoding="utf-8")
                content_args = ["--content-file", str(temp_file)]
            
            # Execute create command
            print(f"  Creating note '{title}' under parent {parent_rem_id}...")
            cmd = ["create", "--parent-id", parent_rem_id, "--title", title] + content_args
            res = run_cli(cmd)
            
            if "error" in res:
                print(f"  Error creating note: {res['error']}")
            else:
                new_id = res.get("remId") or res.get("id") or res.get("_id")
                if new_id:
                    print(f"  Successfully created! New ID: {new_id}")
                    # Cache the new ID
                    term_to_id[term] = new_id
                    created_count += 1
                else:
                    print(f"  Warning: Create command succeeded but no ID in response: {res}")
                    created_count += 1

    print("\n" + "="*40)
    print("Execution complete.")
    print(f"  Created: {created_count}")
    print(f"  Updated: {updated_count}")
    print(f"  Skipped: {skipped_count}")
    print("="*40)

if __name__ == "__main__":
    main()
