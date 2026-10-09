import os
import sys
from pathlib import Path

# Ensure project root is in sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from backend.app import create_app
from backend.app.config import Config

app = create_app()

if __name__ == "__main__":
    host = os.getenv("HOST", Config.HOST)
    port = int(os.getenv("PORT", Config.PORT))
    debug = Config.DEBUG
    print(f"Starting CorpusAI Backend on http://{host}:{port} (debug={debug})...")
    app.run(host=host, port=port, debug=debug)
