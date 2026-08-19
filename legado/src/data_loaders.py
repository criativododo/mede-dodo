import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
NAMES_SEED_PATH = DATA_DIR / "names_seed.json"
DDD_UF_PATH = DATA_DIR / "ddd_uf.json"


def load_names_db(path=NAMES_SEED_PATH):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_ddd_to_uf(path=DDD_UF_PATH):
    with open(path, encoding="utf-8") as f:
        return json.load(f)
