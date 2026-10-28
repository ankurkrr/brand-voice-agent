import os
import sys

def generate_tree(start_path, output_file):
    # Expanded exclude list
    exclude_dirs = {
        '.git', '__pycache__', 'venv', '.idea', '.vscode', 'node_modules', 
        'dist', 'build', '.gemini', 'chroma_data', 'chroma_data_volume',
        'site-packages', 'coverage'
    }
    exclude_files = {'.DS_Store', 'db_init.log', 'db_init_v2.log'}
    
    print(f"Starting tree generation for {start_path}")
    print(f"Writing to {output_file}")
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            for root, dirs, files in os.walk(start_path):
                # Modify dirs in-place to exclude unwanted directories
                dirs[:] = [d for d in dirs if d not in exclude_dirs]
                
                level = root.replace(start_path, '').count(os.sep)
                indent = ' ' * 4 * (level)
                f.write(f'{indent}{os.path.basename(root)}/\n')
                subindent = ' ' * 4 * (level + 1)
                for file in files:
                    if file not in exclude_files:
                        f.write(f'{subindent}{file}\n')
        print(f"Tree generated at {output_file}")
    except Exception as e:
        print(f"Error generating tree: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        start_path = sys.argv[1]
    else:
        start_path = os.getcwd()
        
    # If start_path is relative, make it absolute
    if not os.path.isabs(start_path):
        start_path = os.path.abspath(start_path)
        
    output_path = os.path.join(os.getcwd(), 'codebase_tree.txt')
    generate_tree(start_path, output_path)
