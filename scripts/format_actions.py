import json
import re
from pathlib import Path

# Paths
PIPELINE_OUTPUT = Path("pipeline_output.json")
TMP_DIR = Path(".agents/tmp")
TMP_DIR.mkdir(parents=True, exist_ok=True)

def clean_citations(text: str) -> str:
    """Remove citation brackets like [1], [2], [1], [2], [3]."""
    text = re.sub(r'\s*\[\d+\](?:,\s*\[\d+\])*', '', text)
    return text

def format_ranges_and_numbers(text: str) -> str:
    """Replace range words with ~ and add clozes to key percentages/numbers."""
    # Convert "X to Y days/weeks/months/years" or "X to Y"
    text = re.sub(r'(\d+)\s+to\s+(\d+)', r'\1~\2', text)
    text = re.sub(r'(\d+)\s*-\s*(\d+)', r'\1~\2', text)
    
    # Convert "X years and older" -> "≥X years"
    text = re.sub(r'(\d+)\s+years\s+and\s+older', r'≥\1 years', text)
    
    # Cloze percentages - only once to avoid double wrapping
    text = re.sub(r'(\d+)\s*%', r'{{\1%}}', text)
    
    # Cloze hours
    text = re.sub(r'(\d+)\s*hours', r'{{\1}} hours', text)
    
    # Cloze specific cranial nerves
    text = re.sub(r'\b(CN\s+[IVX,\s+and]+)\b', r'{{\1}}', text)
    
    # Safety cleanup for any accidentally nested braces
    text = text.replace("{{{{", "{{").replace("}}}}", "}}")
    
    return text

def format_remnote_style(term: str, content: str) -> tuple[str, str]:
    """Format the title and body content into RemNote syntax."""
    # Strip markdown bold from title if it's bolded
    title = term.strip()
    match = re.match(r'^\*\*([^*]+)\*\*[:\-]?\s*(.*)', title)
    if match:
        title = match.group(1).strip()
        body = match.group(2).strip()
    else:
        body = content.strip()
        
    # Clean trailing colons and dashes from title
    title = re.sub(r'[:\-]+$', '', title).strip()
        
    title = clean_citations(title)
    body = clean_citations(body)
    
    body = format_ranges_and_numbers(body)
    
    # Format definition or concept
    if body:
        # Use :: for definitions
        formatted_content = f"{title}:: {body}"
    else:
        formatted_content = title
        
    return title, formatted_content

def main():
    if not PIPELINE_OUTPUT.exists():
        print(f"Error: {PIPELINE_OUTPUT} not found.")
        return

    data = json.loads(PIPELINE_OUTPUT.read_text(encoding="utf-8"))
    actions = data.get("detailed_output", {}).get("final_actions", [])
    
    print(f"Formatting {len(actions)} actions...")
    
    formatted_actions = []
    
    for idx, action in enumerate(actions):
        action_type = action.get("action")
        term = action.get("term")
        new_content = action.get("new_content", "")
        rem_id = action.get("rem_id")
        new_breadcrumb = action.get("new_breadcrumb", "")
        
        # Determine the raw content to format
        raw_body = ""
        # If the term contains a description, we split it in format_remnote_style
        title, formatted_content = format_remnote_style(term, raw_body)
        
        # Save to file
        prefix = "new" if action_type == "CREATE" else "delta"
        temp_file = TMP_DIR / f"{prefix}_{idx}.md"
        
        # Format as indented list item for RemNote import
        temp_file.write_text(f"- {formatted_content}", encoding="utf-8")
        
        formatted_actions.append({
            "idx": idx,
            "action": action_type,
            "term": term,
            "title": title,
            "rem_id": rem_id,
            "new_breadcrumb": new_breadcrumb,
            "formatted_content": formatted_content,
            "file_path": str(temp_file)
        })
        
    # Save formatted metadata
    Path("formatted_actions.json").write_text(
        json.dumps(formatted_actions, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print("Formatting complete! Metadata saved to formatted_actions.json.")

if __name__ == "__main__":
    main()
