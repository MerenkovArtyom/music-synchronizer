import json
from pathlib import Path

from music_synchronizer.backend_contracts import generated_backend_schemas


SCHEMA_DIR = Path(__file__).resolve().parents[1] / "electron" / "src" / "shared" / "backend-schemas"


def test_generated_backend_schemas_match_checked_in_files() -> None:
    generated = generated_backend_schemas()
    checked_in = {
        path.name: json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(SCHEMA_DIR.glob("*.schema.json"))
    }

    assert checked_in == generated
