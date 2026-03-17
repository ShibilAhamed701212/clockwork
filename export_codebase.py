import os
from pathlib import Path

target_dir = Path(r"d:\var-codes\Clockworker\clockwork_project\clockwork-src\clockwork")
output_file = Path(r"d:\var-codes\Clockworker\clockwork_full_codebase.md")
ignore_dirs = {".git", "__pycache__", ".venv", "node_modules", ".clockwork", ".pytest_cache", "build", "dist"}
ignore_exts = {".pyc", ".pyo", ".pyd", ".so", ".dll", ".exe", ".png", ".jpg", ".zip", ".tar", ".gz"}

def generate_tree(dir_path, prefix=""):
    tree_str = ""
    try:
        items = sorted(os.listdir(dir_path))
    except PermissionError:
        return ""
        
    items = [item for item in items if item not in ignore_dirs and not item.startswith('.')]
    
    for i, item in enumerate(items):
        item_path = os.path.join(dir_path, item)
        is_last = (i == len(items) - 1)
        connector = "└── " if is_last else "├── "
        tree_str += f"{prefix}{connector}{item}\n"
        
        if os.path.isdir(item_path):
            extension = "    " if is_last else "│   "
            tree_str += generate_tree(item_path, prefix + extension)
            
    return tree_str

def main():
    markdown_content = "# Clockwork Full Codebase Export\n\n"
    markdown_content += "## Directory Tree\n```text\n"
    markdown_content += "clockwork/\n"
    markdown_content += generate_tree(target_dir)
    markdown_content += "```\n\n"
    markdown_content += "---\n\n## Source Code\n\n"
    
    for root, dirs, files in os.walk(target_dir):
        dirs[:] = [d for d in dirs if d not in ignore_dirs and not d.startswith('.')]
        
        for file in sorted(files):
            if any(file.endswith(ext) for ext in ignore_exts):
                continue
            
            file_path = os.path.join(root, file)
            ext = os.path.splitext(file)[1].lower()
            lang_map = {".py": "python", ".yaml": "yaml", ".yml": "yaml", ".json": "json", ".md": "markdown", ".txt": "text"}
            lang = lang_map.get(ext, "text")
            
            rel_path = os.path.relpath(file_path, target_dir).replace('\\', '/')
            
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    code = f.read()
                    
                markdown_content += f"### File: `clockwork/{rel_path}`\n\n"
                markdown_content += f"```{lang}\n{code}\n```\n\n"
            except Exception as e:
                markdown_content += f"### File: `clockwork/{rel_path}`\n\n"
                markdown_content += f"> *(Error reading file: {e})*\n\n"

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(markdown_content)
        
    print(f"Codebase exported successfully to {output_file}")

if __name__ == '__main__':
    main()
