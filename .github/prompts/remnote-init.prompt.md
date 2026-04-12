---
agent: 'agent'
description: 'Ensure the RemNote MCP Server is running and successfully bridged to the browser plugin.'
---

# RemNote CLI Initialization Workflow

This workflow ensures your agent can communicate with RemNote through the `remnote-cli` and the Automation Bridge plugin.

// turbo
1. Run the initialization bash script.
```bash
bash scripts/remnote_init.sh
```

2. Evaluate the output.
- If it returns **SUCCESS**, the CLI is ready for use.
- If it returns **ERROR**, prompt the user to:
    - Open their RemNote browser tab.
    - Ensure the **Automation Bridge** plugin is installed and running.
    - Manually run `npx remnote-cli daemon start`.

3. Decision Gate:
- If write access is not granted, explain to the user how to enable it in the **Automation Bridge** plugin settings within the RemNote tab.
