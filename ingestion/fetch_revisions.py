"""Rate-limited, cached revision fetcher for the feasibility cohort."""
import argparse, csv, json, os, time
from pathlib import Path
import requests

UA = os.environ.get("OFF_USER_AGENT", "")
if not UA or "your-real-email" in UA:
    raise SystemExit("Set a real OFF_USER_AGENT in .env")
HEADERS = {"User-Agent": UA}
DELAY = 4.2
RAW = Path("data/raw/revisions")
API = "https://world.openfoodfacts.org/api/v2/product/{code}.json"
STATIC = "https://static.openfoodfacts.org/images/products/{path}/{rev}.json"


def static_path(code):
    if len(code) <= 8:
        return code
    c = code.zfill(13)
    return f"{c[0:3]}/{c[3:6]}/{c[6:9]}/{c[9:]}"


def fetch(url, params=None, tries=4):
    for attempt in range(tries):
        time.sleep(DELAY)
        try:
            r = requests.get(url, headers=HEADERS, params=params, timeout=30)
        except requests.RequestException as e:
            print("  network error:", e); time.sleep(30 * (attempt + 1)); continue
        if r.status_code in (200, 404):
            return r.status_code, r.text
        if r.status_code == 429:
            print("  rate limited, backing off"); time.sleep(60 * (attempt + 1)); continue
        time.sleep(10 * (attempt + 1))
    return None, None


def sample_revs(cur, k):
    if cur <= k:
        return list(range(1, cur + 1))
    step = (cur - 1) / (k - 1)
    return sorted({round(1 + i * step) for i in range(k)} | {cur - 1})


ap = argparse.ArgumentParser()
ap.add_argument("--mode", choices=["api", "static"], required=True)
ap.add_argument("--limit", type=int, default=None)
ap.add_argument("--revs-per-product", type=int, default=10)
args = ap.parse_args()

with open("config/monitored_products.csv") as f:
    codes = [r["code"] for r in csv.DictReader(f)][: args.limit]

log = open(RAW.parent / "fetch_log.jsonl", "a") if RAW.parent.exists() else None
for i, code in enumerate(codes, 1):
    d = RAW / code; d.mkdir(parents=True, exist_ok=True)
    cur_file = d / "current.json"
    if not cur_file.exists():
        status, text = fetch(API.format(code=code))
        if status != 200:
            print(f"[{i}/{len(codes)}] {code}: cannot fetch current ({status})"); continue
        cur_file.write_text(text)
    cur = int(json.loads(cur_file.read_text())["product"]["rev"])
    (d / f"{cur}.json").write_text(cur_file.read_text())
    revs = [r for r in sample_revs(cur, args.revs_per_product) if r != cur]
    print(f"[{i}/{len(codes)}] {code}: current rev {cur}, fetching {len(revs)} revisions")
    for rev in revs:
        if (d / f"{rev}.json").exists() or (d / f"{rev}.missing").exists():
            continue  # cached -> idempotent re-run
        if args.mode == "api":
            status, text = fetch(API.format(code=code), params={"rev": rev})
        else:
            status, text = fetch(STATIC.format(path=static_path(code), rev=rev))
        if status == 200:
            (d / f"{rev}.json").write_text(text)
        else:
            (d / f"{rev}.missing").write_text(str(status))
        if log:
            log.write(json.dumps({"code": code, "rev": rev, "status": status, "ts": time.time()}) + "\n")