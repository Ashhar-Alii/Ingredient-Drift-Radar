"""Crude feasibility metrics over cached revisions. Throwaway: not the real pipeline logic."""
import csv, json, re
from collections import Counter
from pathlib import Path

RAW = Path("data/raw/revisions")


def norm_set(text):
    if not text:
        return None
    parts = (re.sub(r"[\s\.\*_:]+", " ", p).strip() for p in re.split(r"[,;]", text.lower()))
    return frozenset(p for p in parts if p)


def tag_set(p):
    t = p.get("allergens_tags")
    return frozenset(t) if isinstance(t, list) else None


rows, field_avail = [], Counter()
n_hist = 0
for d in sorted(RAW.iterdir()):
    if not d.is_dir():
        continue
    honoured, requested, missing = {}, 0, 0
    for f in d.iterdir():
        if f.suffix == ".missing":
            requested += 1; missing += 1
        elif f.suffix == ".json" and f.stem != "current":
            requested += 1
            try:
                data = json.loads(f.read_text())
            except ValueError:
                continue
            p = data.get("product", data)
            if isinstance(p, dict) and str(p.get("rev")) == f.stem:
                honoured[int(f.stem)] = p
    for p in honoured.values():
        n_hist += 1
        for k in ("ingredients_text", "ingredients_tags", "allergens", "allergens_tags"):
            field_avail[k] += bool(p.get(k))
    revs = sorted(honoured)
    c = Counter()
    for a, b in zip(revs, revs[1:]):
        pa, pb = honoured[a], honoured[b]
        ia, ib = norm_set(pa.get("ingredients_text")), norm_set(pb.get("ingredients_text"))
        if ia is None and ib is None: c["both_missing"] += 1
        elif ia is None: c["completion"] += 1
        elif ib is None: c["became_missing"] += 1
        elif ia != ib: c["set_change"] += 1
        elif pa.get("ingredients_text") != pb.get("ingredients_text"): c["formatting_only"] += 1
        else: c["no_change"] += 1
        sa, sb = tag_set(pa), tag_set(pb)
        if sa is not None and sb is not None and sa != sb: c["allergen_change"] += 1
    with_text = sum(1 for p in honoured.values() if p.get("ingredients_text"))
    rows.append({"code": d.name, "requested": requested, "missing": missing,
                 "honoured": len(revs), "with_ingredient_text": with_text, **c})

keys = ["code", "requested", "missing", "honoured", "with_ingredient_text", "set_change",
        "formatting_only", "completion", "became_missing", "allergen_change", "no_change", "both_missing"]
with open("data/feasibility_by_product.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=keys, restval=0, extrasaction="ignore")
    w.writeheader(); w.writerows(rows)

n = len(rows) or 1
req = sum(r["requested"] for r in rows) or 1
usable = sum(r["honoured"] >= 2 for r in rows)
texty = sum(r["with_ingredient_text"] >= 2 for r in rows)
changed = sum(r.get("set_change", 0) > 0 for r in rows)
allergen = sum(r.get("allergen_change", 0) for r in rows)
miss = sum(r["missing"] for r in rows) / req

print(f"products analysed: {len(rows)}")
print(f"A  products with >=2 honoured revisions : {usable}/{n} = {usable/n:.0%}   (want >= 70%)")
print(f"B  products with ingredient text in >=2 : {texty}/{n} = {texty/n:.0%}   (want >= 60%)")
print(f"C  products with >=1 ingredient-set change: {changed}/{n} = {changed/n:.0%}   (want >= 25% and >= 8 products)")
print(f"D  allergen changes found (all pairs)   : {allergen}   (want >= 3, soft)")
print(f"E  share of revision requests missing   : {miss:.0%}   (want <= 20%)")
print("field availability in historical revs:", {k: f"{v}/{n_hist}" for k, v in field_avail.items()})
print("pair totals:", {k: sum(r.get(k, 0) for r in rows) for k in keys[5:]})