import requests, json, time, pathlib

OUT = pathlib.Path("data/raw/mempool")
OUT.mkdir(parents=True, exist_ok=True)

def main():
    snap = {
        "fees": requests.get("https://mempool.space/api/v1/fees/recommended", timeout=20).json(),
        "mempool": requests.get("https://mempool.space/api/mempool", timeout=20).json()
    }
    ts = time.strftime("%Y%m%d_%H%M")
    fp = OUT / f"snapshot_{ts}.json"
    fp.write_text(json.dumps(snap))
    print(f"wrote {fp}")

if __name__ == "__main__":
    main()
