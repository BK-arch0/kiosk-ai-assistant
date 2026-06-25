from pathlib import Path

_CLASSES_FILE = Path(__file__).resolve().parent.parent / "dataset" / "classes.txt"

def load_classes(path=_CLASSES_FILE):
    return Path(path).read_text(encoding="utf-8").strip().splitlines()

CLASS_NAMES = load_classes()
CLASS_SET   = set(CLASS_NAMES)