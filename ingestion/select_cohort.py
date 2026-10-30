"""Pick a reproducible, stratified cohort of products for the feasibility test."""
import argparse, csv, os
import duckdb

DEFAULT = "https://huggingface.co/datasets/openfoodfacts/product-database/resolve/main/food.parquet"
STRATA = {  # name: (column, tag substring)
    "chocolates": ("categories_tags", "en:chocolates"),
    "biscuits": ("categories_tags", "en:biscuits"),
    "breakfast_cereals": ("categories_tags", "en:breakfast-cereals"),
    "snacks": ("categories_tags", "en:snacks"),
    "instant_noodles": ("categories_tags", "en:instant-noodles"),
    "india": ("countries_tags", "en:india"),
}

ap = argparse.ArgumentParser()
ap.add_argument("--parquet", default=DEFAULT)
ap.add_argument("--describe", action="store_true")
ap.add_argument("--per-stratum", type=int, default=8)
args = ap.parse_args()

con = duckdb.connect()
con.execute("SET memory_limit='3GB'; SET threads=2;")
if args.parquet.startswith("http"):
    con.execute("INSTALL httpfs; LOAD httpfs;")
src = f"read_parquet('{args.parquet}')"

if args.describe:
    want = {"code", "rev", "product_name", "ingredients_text", "ingredients_tags",
            "allergens_tags", "categories_tags", "countries_tags", "last_modified_t"}
    for name, typ, *_ in con.execute(f"DESCRIBE SELECT * FROM {src}").fetchall():
        if name in want:
            print(f"{name:20} {typ}")
    raise SystemExit

print("Pre-filtering dataset matching criteria into an in-memory table...")
# This reads the remote parquet ONCE and brings only the required records into RAM
con.execute(f"""
    CREATE TABLE local_data AS 
    SELECT CAST(code AS VARCHAR) as code, rev, categories_tags, countries_tags, ingredients_text 
    FROM {src}
    WHERE regexp_matches(CAST(code AS VARCHAR), '^[0-9]{{8,13}}$')
      AND rev BETWEEN 8 AND 40
      AND length(CAST(ingredients_text AS VARCHAR)) > 20
""")

seen, rows = set(), []
print("Extracting strata groups from memory...")
for stratum, (col, tag) in STRATA.items():
    q = f"""
        SELECT code, rev FROM local_data
        WHERE CAST({col} AS VARCHAR) LIKE ?
        ORDER BY hash(code) LIMIT ?
    """
    got = con.execute(q, [f"%{tag}%", args.per_stratum]).fetchall()
    if len(got) < args.per_stratum:
        print(f"WARNING: stratum {stratum} gave only {len(got)} rows")
    for code, rev in got:
        if code not in seen:
            seen.add(code)
            rows.append((code, rev, stratum))

# Ensure directory exists inside container context safely
os.makedirs("config", exist_ok=True)

with open("config/monitored_products.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["code", "rev_snapshot", "stratum"])
    w.writerows(rows)
print(f"wrote {len(rows)} products to config/monitored_products.csv")
