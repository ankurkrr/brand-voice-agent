import os
import ast
import sys
from collections import defaultdict
from typing import List, Dict, Set

# Base directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Layer Definitions
LAYERS = {
    "domain": {"allowed": set()},  # Pure domain models
    "lib": {"allowed": set()},     # Generic utilities (no business logic)
    "data": {"allowed": {"domain", "lib"}}, # Repositories
    "core": {"allowed": {"domain", "lib", "data"}}, # Business Logic
    "adapters": {"allowed": {"core", "domain", "data", "lib"}}, # API / UI
}

# Directories to ignore
IGNORE_DIRS = {
    "venv", ".git", ".idea", ".vscode", "__pycache__", "tests", "scripts", 
    "services_legacy", "api/services_legacy", "services", "infra", "alembic"
}

# Files to ignore
IGNORE_FILES = {
    "verify_architecture.py", "conftest.py", "setup.py"
}

def get_module_layer(path: str) -> str:
    """Determine which layer a file belongs to based on its path."""
    rel_path = os.path.relpath(path, BASE_DIR)
    parts = rel_path.split(os.sep)
    
    if parts[0] in LAYERS:
        return parts[0]
    return None

def get_imported_modules(file_path: str) -> List[str]:
    """Parse a file and extract all imported top-level modules."""
    with open(file_path, "r", encoding="utf-8") as f:
        try:
            tree = ast.parse(f.read(), filename=file_path)
        except SyntaxError:
            return []

    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name.split('.')[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module.split('.')[0])
    return imports

def verify_architecture():
    violations = defaultdict(list)
    checked_files = 0

    print(f"Scanning codebase at {BASE_DIR}...")
    print("-" * 50)

    for root, dirs, files in os.walk(BASE_DIR):
        # Filter exclusions
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        
        for file in files:
            if not file.endswith(".py") or file in IGNORE_FILES:
                continue

            file_path = os.path.join(root, file)
            current_layer = get_module_layer(file_path)

            if not current_layer:
                continue
            
            checked_files += 1
            imports = get_imported_modules(file_path)
            
            allowed_layers = LAYERS[current_layer]["allowed"]
            
            for imp in imports:
                # Check if import is one of our internal modules
                if imp in LAYERS:
                    # Self-import is always allowed (within same layer)
                    if imp == current_layer:
                        continue
                        
                    # Check against allowed dependencies
                    if imp not in allowed_layers:
                        rel_path = os.path.relpath(file_path, BASE_DIR)
                        violations[current_layer].append(
                            f"{rel_path} imports '{imp}' (Allowed: {allowed_layers})"
                        )

    print(f"Checked {checked_files} files.")
    print("-" * 50)
    
    if violations:
        print("❌ ARCHITECTURE VIOLATIONS FOUND:")
        for layer, issues in violations.items():
            print(f"\nLayer [{layer}]:")
            for issue in issues:
                print(f"  - {issue}")
        sys.exit(1)
    else:
        print("✅ Architecture Verified: No boundary violations found.")
        sys.exit(0)

if __name__ == "__main__":
    verify_architecture()
