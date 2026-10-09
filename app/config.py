import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = json.loads((ROOT / 'project.json').read_text(encoding='utf-8'))

def state_dir():
    path = Path(os.getenv('STATE_DIR', str(ROOT / 'state')))
    path.mkdir(parents=True, exist_ok=True)
    return path
