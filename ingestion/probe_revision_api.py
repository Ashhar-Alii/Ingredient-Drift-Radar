"""Probe how Open Food Facts serves historical revisions for ONE product."""
import json, os, time
from pathlib import Path
import requests

UA = os.environ.get("OFF_USER_AGENT", "")
if not UA or "your-real-email" in UA:
    raise SystemExit("Set a real OFF_USER_AGENT in .env")
HEADERS = {"User-Agent": UA}
DELAY = 4.2  # ~14 requests/minute, under the documented 15/min limit
CODE = os.environ.get("PROBE_CODE", "3017620422003")
OUT = Path("data/raw/probe"); OUT.mkdir(parents=True, exist_ok=True)


def get(url, params=None):
    time.sleep(DELAY)
    return requests.get(url, headers=HEADERS, params=params, timeout=30)


def static_path(code):
    if len(code) <= 8:
        return code
    c = code.zfill(13)
    return f"{c[0:3]}/{c[3:6]}/{c[6:9]}/{c[9:]}"


def summarise(label, rev_asked, r):
    info = {"approach": label, "rev_asked": rev_asked, "status": r.status_code}
    (OUT / f"{label}_{rev_asked}.txt").write_text(r.text)
    try:
        data = r.json()
        p = data.get("product", data)
        info.update(
            rev_returned=p.get("rev"),
            honoured=str(p.get("rev")) == str(rev_asked),
            has_ingredients_text=bool(p.get("ingredients_text")),
            has_ingredients_tags="ingredients_tags" in p,
            has_allergens_tags="allergens_tags" in p,
            has_allergens="allergens" in p,
            snippet=(p.get("ingredients_text") or "")[:70],
        )
    except ValueError:
        info["note"] = "non-JSON response"
    return info


base = f"https://world.openfoodfacts.org/api/v2/product/{CODE}.json"
cur = get(base)
cur_rev = int(cur.json()["product"]["rev"])
print(f"current rev for {CODE}: {cur_rev}")

results = []
for k in sorted({1, cur_rev // 2, cur_rev - 1} - {0, cur_rev}):
    results.append(summarise("A_api_rev_param", k, get(base, params={"rev": k})))
    url = f"https://static.openfoodfacts.org/images/products/{static_path(CODE)}/{k}.json"
    results.append(summarise("B_static_file", k, get(url)))

for row in results:
    print(json.dumps(row))