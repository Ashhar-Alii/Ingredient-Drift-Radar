"""Show which top-level fields differ between two cached revisions of one product."""
import json, sys
from pathlib import Path

code, a, b = sys.argv[1:4]


def load(rev):
    d = json.loads(Path(f"data/raw/revisions/{code}/{rev}.json").read_text())
    return d.get("product", d)


pa, pb = load(a), load(b)
for k in sorted(set(pa) | set(pb)):
    if pa.get(k) != pb.get(k):
        print(f"{k}: {str(pa.get(k, '<absent>'))[:90]!r} -> {str(pb.get(k, '<absent>'))[:90]!r}")