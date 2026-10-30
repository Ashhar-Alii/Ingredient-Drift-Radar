"""Compare canonical ingredient TAGS (language-independent) for each pair in data/pairs.csv."""
import csv, json
from collections import Counter
from pathlib import Path

RAW = Path("data/raw/revisions")


def en_tags(code, rev):
    data = json.loads((RAW / code / f"{rev}.json").read_text())
    p = data.get("product", data)
    return frozenset(t for t in (p.get("ingredients_tags") or []) if t.startswith("en:"))


rows = list(csv.DictReader(open("data/pairs.csv")))
for r in rows:
    ta, tb = en_tags(r["code"], r["rev_a"]), en_tags(r["code"], r["rev_b"])
    if not ta and not tb: r["tag_class"] = "both_empty"
    elif not ta: r["tag_class"] = "completion"
    elif not tb: r["tag_class"] = "became_empty"
    elif ta == tb: r["tag_class"] = "no_change"
    else: r["tag_class"] = "tag_change"
    r["tags_added"] = "|".join(sorted(tb - ta))
    r["tags_removed"] = "|".join(sorted(ta - tb))

with open("data/pairs_tags.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]))
    w.writeheader(); w.writerows(rows)

n = len({r["code"] for r in rows})
print("tag classes:", dict(Counter(r["tag_class"] for r in rows)))
print("text class x tag class (text said set_change/formatting_only):")
for k, v in sorted(Counter((r["ingredient_class"], r["tag_class"]) for r in rows
                           if r["ingredient_class"] in ("set_change", "formatting_only")).items()):
    print("  ", k, v)


def material(r):
    return r["tag_class"] == "tag_change" or r["allergen_class"] in ("added", "removed", "modified")


prods = {r["code"] for r in rows if material(r)}
print(f"products with >=1 material candidate (tags): {len(prods)}/{n}")
print("\n--- review list ---")
for r in rows:
    if material(r):
        print(r["code"], f"rev {r['rev_a']}->{r['rev_b']}", r["tag_class"], r["allergen_class"],
              "+", r["tags_added"][:150], "-", r["tags_removed"][:150],
              "| allergens +", r["allergens_added"], "-", r["allergens_removed"])