import alembic.config
import sys
import os
import socket
from dotenv import load_dotenv

# Ensure the current directory is in sys.path so env.py can find the app
sys.path.append(os.getcwd())

def main():
    load_dotenv()
    
    db_host = os.getenv("DB_HOST", "localhost")
    try:
        socket.gethostbyname(db_host)
    except socket.gaierror:
        print(f"Warning: DB_HOST='{db_host}' could not be resolved. Falling back to 'localhost' for local execution.")
        os.environ["DB_HOST"] = "localhost"

    print(f"Running Alembic with arguments: {sys.argv[1:]}")
    alembic.config.main(argv=sys.argv[1:])

if __name__ == "__main__":
    main()
