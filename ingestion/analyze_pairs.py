"""One row per consecutive honoured revision pair, classified."""
import csv, json, re
from collections import Counter
from pathlib import Path

RAW = Path("data/raw/revisions")


def norm_set(text):
    if not text:
        return None
    parts = (re.sub(r"[\s\.\*_:]+", " ", p).strip() for p in re.split(r"[,;]", text.lower()))
    return frozenset(p for p in parts if p)


def allergen_state(p):
    tags = p.get("allergens_tags")
    if tags is None:
        return "absent", frozenset()
    tags = frozenset(tags)
    return ("populated" if tags else "empty"), tags


def classify_ingredients(pa, pb):
    ia, ib = norm_set(pa.get("ingredients_text")), norm_set(pb.get("ingredients_text"))
    if ia is None and ib is None: return "both_missing", set(), set()
    if ia is None: return "completion", set(ib), set()
    if ib is None: return "became_missing", set(), set(ia)
    if ia != ib: return "set_change", set(ib - ia), set(ia - ib)
    if pa.get("ingredients_text") != pb.get("ingredients_text"): return "formatting_only", set(), set()
    return "no_change", set(), set()


def classify_allergens(pa, pb):
    sa, ta = allergen_state(pa); sb, tb = allergen_state(pb)
    if sa == "absent" or sb == "absent": return "not_comparable", set(), set()
    if ta == tb: return "same", set(), set()
    if sa == "empty": return "from_empty", set(tb), set()
    if sb == "empty": return "to_empty", set(), set(ta)
    add, rem = tb - ta, ta - tb
    return ("added" if add and not rem else "removed" if rem and not add else "modified"), set(add), set(rem)


rows = []
for d in sorted(RAW.iterdir()):
    if not d.is_dir():
        continue
    honoured = {}
    for f in d.glob("*.json"):
        if f.stem == "current":
            continue
        try:
            data = json.loads(f.read_text())
        except ValueError:
            continue
        p = data.get("product", data)
        if isinstance(p, dict) and str(p.get("rev")) == f.stem:
            honoured[int(f.stem)] = p
    revs = sorted(honoured)
    for a, b in zip(revs, revs[1:]):
        pa, pb = honoured[a], honoured[b]
        ic, iadd, irem = classify_ingredients(pa, pb)
        ac, aadd, arem = classify_allergens(pa, pb)
        rows.append({
            "code": d.name, "rev_a": a, "rev_b": b,
            "gap": b - a, "ts_a": pa.get("last_modified_t"), "ts_b": pb.get("last_modified_t"),
            "ingredient_class": ic, "ingr_added": "|".join(sorted(iadd)), "ingr_removed": "|".join(sorted(irem)),
            "allergen_class": ac, "allergens_added": "|".join(sorted(aadd)), "allergens_removed": "|".join(sorted(arem)),
            "text_a": (pa.get("ingredients_text") or "")[:120], "text_b": (pb.get("ingredients_text") or "")[:120],
        })

with open("data/pairs.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]))
    w.writeheader(); w.writerows(rows)

n_prod = len({r["code"] for r in rows})
print(f"products: {n_prod}, consecutive pairs: {len(rows)}, pairs with gap>1: {sum(r['gap'] > 1 for r in rows)}")
print("ingredient classes:", dict(Counter(r["ingredient_class"] for r in rows)))
print("allergen classes  :", dict(Counter(r["allergen_class"] for r in rows)))
print("allergen change x ingredient class:")
cross = Counter((r["allergen_class"], r["ingredient_class"]) for r in rows if r["allergen_class"] not in ("same", "not_comparable"))
for k, v in sorted(cross.items(), key=lambda x: -x[1]):
    print("  ", k, v)

material = {r["code"] for r in rows
            if r["ingredient_class"] == "set_change" or r["allergen_class"] in ("added", "removed", "modified")}
print(f"products with >=1 material candidate: {len(material)}/{n_prod} = {len(material)/n_prod:.0%}")

print("\n--- pairs to review by eye ---")
for r in rows:
    if r["ingredient_class"] in ("set_change", "formatting_only") or r["allergen_class"] in ("added", "removed", "modified"):
        print(r["code"], f"rev {r['rev_a']}->{r['rev_b']}", r["ingredient_class"], r["allergen_class"],
              "+", r["ingr_added"], "-", r["ingr_removed"], "| allergens +", r["allergens_added"], "-", r["allergens_removed"])