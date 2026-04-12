---
agent: 'agent'
description: 'Automatically check NotebookLM login status and select a notebook for the current session.'
---

# NotebookLM Initialization Workflow

This workflow ensures the user is securely logged into Google NotebookLM and helps them select an active notebook for the current session.

// turbo
1. Run the initialization bash script.
```bash
bash scripts/notebooklm_init.sh
```

2. Wait for auth response from shell or terminal for 10 secs, evaluate the output.
- If it returns **SUCCESS**, there was no need to open browser for login.
- If it returns **ERROR** or exit code 1, prompt the user to login manually using `notebooklm login`.

3. Wait for notebookLM response with notebook list with json format, which included titles and the ids of all of the user''s notebook.
Present the list of Notebooks to the user in the chat interface and gracefully ask: **"Which notebook would you like to open for this session?"**
After the user provides the title or id of the notebook, find the id of the notebook based on returned result and set it as the active context:
```bash
./antigravitytest-env/Scripts/notebooklm use <NOTEBOOK_ID>
```

4. You can now proceed to ask questions, use english only:
```bash
./antigravitytest-env/Scripts/notebooklm ask "user question"
```

5. If error or timeout with notebooklm response, try again with
```bash
./antigravitytest-env/Scripts/notebooklm ask "user question"
```
