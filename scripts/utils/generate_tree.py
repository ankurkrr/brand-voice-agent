"""
Generate codebase tree structure
"""
import os
from pathlib import Path

def create_tree(directory, prefix="", exclude_dirs=None, output_file=None):
    """Create tree structure of directory"""
    if exclude_dirs is None:
        exclude_dirs = {'.git', '__pycache__', 'node_modules', '.gemini', 'venv', '.idea', 'dist', 'build', '.egg-info', '.conda', '.config', '.pytest_cache', '.vscode', 'chroma_data', 'chroma_data_volume'}
    
    items = []
    try:
        entries = sorted(os.listdir(directory))
        dirs = [e for e in entries if os.path.isdir(os.path.join(directory, e)) and e not in exclude_dirs]
        files = [e for e in entries if os.path.isfile(os.path.join(directory, e))]
        
        # Process directories first
        for i, d in enumerate(dirs):
            is_last_dir = (i == len(dirs) - 1) and len(files) == 0
            connector = "└── " if is_last_dir else "├── "
            items.append(f"{prefix}{connector}{d}/")
            
            # Recursively process subdirectory
            extension = "    " if is_last_dir else "│   "
            sub_items = create_tree(
                os.path.join(directory, d),
                prefix=prefix + extension,
                exclude_dirs=exclude_dirs,
                output_file=output_file
            )
            items.extend(sub_items)
        
        # Process files
        for i, f in enumerate(files):
            is_last = i == len(files) - 1
            connector = "└── " if is_last else "├── "
            items.append(f"{prefix}{connector}{f}")
            
    except PermissionError:
        pass
    
    return items

if __name__ == "__main__":
    with open("tree_gen.log", "w") as log:
        try:
            log.write("STARTING TREE GENERATION\n")
            root_dir = "."
            output_file = os.path.join("docs", "reference", "codebase_tree.txt")
            
            log.write(f"Generating codebase tree from {os.path.abspath(root_dir)} to {os.path.abspath(output_file)}...\n")
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            # Create tree
            tree_lines = [os.path.basename(os.path.abspath(root_dir)) + "/"]
            tree_lines.extend(create_tree(root_dir))
            
            # Write to file
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("CODEBASE TREE STRUCTURE\n")
                f.write("=" * 70 + "\n\n")
                for line in tree_lines:
                    f.write(line + "\n")
                f.write("\n" + "=" * 70 + "\n")
                f.write(f"Total lines: {len(tree_lines)}\n")
            
            log.write(f"Tree structure exported to: {output_file}\n")
            log.write(f"   Total items: {len(tree_lines)}\n")
            log.write("SUCCESS\n")
            
        except Exception as e:
            log.write(f"ERROR: {str(e)}\n")
            import traceback
            traceback.print_exc(file=log)
