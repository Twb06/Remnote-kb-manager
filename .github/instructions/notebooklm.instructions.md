---
description: 'Guidelines for interacting with NotebookLM in this project.'
applyTo: '**'
---

# NotebookLM Guide

## Rules
- when interact with notebookLM in this project, check if notebooklm_init has loaded
- during ask, wait for NotebookLM response, it may take 30secs to 2 min for a response
- When interacting with NotebookLM using the CLI, prevent the agent from starting a new conversation unnecessarily. Instead, continue from the existing conversation.
