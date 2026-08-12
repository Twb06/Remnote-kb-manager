"""
RemNote Client - Wrap remnote-cli with Dry Run Support
"""

import subprocess
import json
import re
from typing import Optional, Dict, Any, List

CLI_CMD = ["npx", "remnote-cli"]

class RemNoteClient:
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self._rem_id_titles = {}

    def set_rem_title(self, rem_id: str, title: str):
        if rem_id and title:
            self._rem_id_titles[rem_id] = title

    def _run_cmd(self, args: List[str], format: str = "json") -> Any:
        if format == "json":
            full_cmd = CLI_CMD + args + ["--json"]
        else:
            full_cmd = CLI_CMD + args + ["--text"]
            
        try:
            result = subprocess.run(
                full_cmd, capture_output=True, text=True,
                shell=True, encoding='utf-8', errors='replace'
            )
            if result.returncode != 0:
                if format == "json":
                    return {"error": result.stderr.strip() or f"CLI error code {result.returncode}"}
                else:
                    return ""
            output = result.stdout.strip()
            if format == "json":
                json_match = re.search(r'(\{.*\}|\[.*\])', output, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group(0))
                return {"error": "No JSON found in output", "raw": output}
            else:
                return output
        except Exception as e:
            if format == "json":
                return {"error": str(e)}
            else:
                return ""

    def read(self, rem_id: str, depth: int = 6) -> Any:
        return self._run_cmd(["read", rem_id, "--depth", str(depth), "--content-mode", "structured"])

    def read_markdown(self, rem_id: str, depth: int = 10) -> str:
        return self._run_cmd([
            "read", rem_id, 
            "--depth", str(depth), 
            "--content-mode", "markdown", 
            "--view", "full",
            "--child-limit", "500",
            "--max-content-length", "200000"
        ], format="text")

    def search(self, query: str, parent_id: Optional[str] = None) -> Any:
        args = ["search", query, "--limit", "50"]
        if parent_id:
            args.extend(["--parent-id", parent_id])
        return self._run_cmd(args)

    def create(self, content: str, parent_id: Optional[str] = None) -> Any:
        if self.dry_run:
            parent_title = self._rem_id_titles.get(parent_id, "Unknown Title") if parent_id else "Root"
            print(f"[DRY-RUN] Would CREATE rem under parent '{parent_id}' ({parent_title}): {content}")
            return {"status": "success", "remId": "dry-run-create-id", "dry_run": True}
            
        args = ["create", content]
        if parent_id:
            args.extend(["--parent-id", parent_id])
        return self._run_cmd(args)

    def update(self, rem_id: str, content: str) -> Any:
        if self.dry_run:
            rem_title = self._rem_id_titles.get(rem_id, "Unknown Title")
            print(f"[DRY-RUN] Would UPDATE rem '{rem_id}' ({rem_title}) to: {content}")
            return {"status": "success", "remId": rem_id, "dry_run": True}
            
        args = ["update", rem_id, "--content", content]
        return self._run_cmd(args)
