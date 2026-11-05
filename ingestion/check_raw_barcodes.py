# ingestion/check_raw_barcodes.py
from pathlib import Path
from ingredient_drift.barcode import normalise_barcode

def run_data_check():
    # Looks for data/raw relative to your workspace root
    raw_path = Path("data/raw/revisions")
    
    if not raw_path.exists() or not raw_path.is_dir():
        print(f"❌ Target folder '{raw_path.resolve()}' not found.")
        print("Please ensure you have run your downloads so that data/raw/<barcode> directories exist.")
        return

    print(f"🔍 Checking real data directories inside {raw_path}...")
    anomalies_found = False
    
    for d in sorted(p for p in raw_path.iterdir() if p.is_dir()):
        r = normalise_barcode(d.name)
        if r.status.value != "ok" or r.check_digit_valid is False:
            print(f"⚠️ {d.name} -> Normalised: {r.normalised_code} | Status: {r.status.value} | Valid Check Digit: {r.check_digit_valid}")
            anomalies_found = True
            
    if not anomalies_found:
        print("✅ Check complete. No unexpected raw barcode formats found!")

if __name__ == "__main__":
    run_data_check()
