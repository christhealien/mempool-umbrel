#!/usr/bin/env python3
"""Apply this repo's overlay to a checkout of the upstream mempool fork (Horizon-btc/mempool).

  apply_overlay.py UPSTREAM_DIR [--check]

1. copies overlay/frontend/... into UPSTREAM_DIR/frontend/... (theme, script, pool logo)
2. patches frontend/src/index.mempool.html to load the theme and script        (required)
3. patches backend/src/tasks/pools-updater.ts to add overlay/extra-pools.json   (needed for the pool name)
Every patch is anchored on an exact line of upstream. A missing anchor is reported; the index patch is fatal,
the pool patch is fatal too unless --lenient is given (so an upstream refactor never ships a half-themed build
without anyone noticing). With --check nothing is written.
"""
import argparse, hashlib, json, os, shutil, sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

INDEX = "frontend/src/index.mempool.html"
INDEX_ANCHOR = "</body>"
INDEX_ADD = ('  <link rel="stylesheet" href="/resources/blake2b/theme.css?v=%s">\n'
             '  <script src="/resources/blake2b/bandit.js?v=%s" defer></script>\n')


def _stamp(name):
    """short content hash, so a browser never keeps showing an old theme after an update"""
    with open(os.path.join(HERE, "overlay/frontend/src/resources/blake2b", name), "rb") as f:
        return hashlib.sha1(f.read()).hexdigest()[:10]

POOLS = "backend/src/tasks/pools-updater.ts"
POOLS_ANCHOR = "poolsParser.setMiningPools(poolsJson);"
POOLS_CODE = """// blake2b overlay: pools of our own that the shared list does not know (see overlay/extra-pools.json)
      const blake2bExtraPools: any[] = %s;
      for (const extra of blake2bExtraPools) {
        if (Array.isArray(poolsJson) && !poolsJson.some((p: any) => p.id === extra.id || p.name === extra.name)) {
          poolsJson.push(extra);
        }
      }
      poolsParser.setMiningPools(poolsJson);"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("upstream")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--lenient", action="store_true")
    a = ap.parse_args()
    up = a.upstream
    bad = 0

    ip = os.path.join(up, INDEX)
    s = open(ip, encoding="utf-8").read() if os.path.exists(ip) else ""
    if s.count(INDEX_ANCHOR) != 1:
        print("FAIL  %s: expected exactly one %r" % (INDEX, INDEX_ANCHOR)); bad += 1
    pp = os.path.join(up, POOLS)
    t = open(pp, encoding="utf-8").read() if os.path.exists(pp) else ""
    pools_ok = t.count(POOLS_ANCHOR) == 1
    if not pools_ok:
        print("%s  %s: expected exactly one %r" % ("WARN" if a.lenient else "FAIL", POOLS, POOLS_ANCHOR))
        bad += 0 if a.lenient else 1
    logo_dir = os.path.join(up, "frontend/src/resources")
    if not os.path.isdir(logo_dir):
        print("FAIL  frontend/src/resources is missing"); bad += 1
    comp = os.path.join(up, "frontend/src/app/shared/components/mining-pool/mining-pool.component.ts")
    if os.path.exists(comp) and "/resources/mining-pools/" not in open(comp, encoding="utf-8").read():
        print("WARN  pool logos are no longer under /resources/mining-pools/: the Hash Bandit logo may not show")
    if bad:
        return 2
    if a.check:
        print("OK  overlay fits this upstream"); return 0

    shutil.copytree(os.path.join(HERE, "overlay/frontend"), os.path.join(up, "frontend"), dirs_exist_ok=True)
    if "blake2b/theme.css" not in s:
        s = s.replace(INDEX_ANCHOR, (INDEX_ADD % (_stamp("theme.css"), _stamp("bandit.js"))) + INDEX_ANCHOR)
        open(ip, "w", encoding="utf-8").write(s)
    if pools_ok and "blake2bExtraPools" not in t:
        extra = json.load(open(os.path.join(HERE, "overlay/extra-pools.json")))
        t = t.replace(POOLS_ANCHOR, POOLS_CODE % json.dumps(extra))
        open(pp, "w", encoding="utf-8").write(t)
    print("OK  overlay applied")
    return 0


if __name__ == "__main__":
    sys.exit(main())
