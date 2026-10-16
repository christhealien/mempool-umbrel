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

POOLRANK = "frontend/src/app/components/pool-ranking/pool-ranking.component.ts"
# (old, new) pairs, each anchored on exact upstream text. Cosmetic, so a miss only warns.
POOLRANK_EDITS = [
    ("""      const poolColor = poolsColor[pool.name.replace(/[^a-zA-Z0-9]/g, '').toLowerCase()]
        ?? PoolRankingComponent.SERIES_COLORS[paletteIndex++ % PoolRankingComponent.SERIES_COLORS.length];""",
     """      // blake2b overlay: monochrome pie. Greys alternate light/dark so neighbours always differ
      const poolColor = PoolRankingComponent.B2B_GREYS[sources.length % PoolRankingComponent.B2B_GREYS.length];"""),
    ("""  private static readonly BAND_LIGHTEST = 0.84;""",
     """  private static readonly B2B_GREYS = ['#f0f0f0', '#6e6e6e', '#cfcfcf', '#4c4c4c', '#e0e0e0', '#8a8a8a', '#b8b8b8', '#5a5a5a', '#d8d8d8', '#7c7c7c'];
  private static readonly BAND_LIGHTEST = 0.84;"""),
    ("""    const hex = color.replace('#', '');
    const [r, g, b] = [0, 2, 4].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255);""",
     """    // blake2b overlay: grey bands, shaded around the pool's own grey so each pool keeps its tone
    const base = parseInt(color.replace('#', '').slice(0, 2), 16) / 255;
    const grey = Math.max(0.16, Math.min(0.96, base + (lightness - 0.71) * 0.55));
    const gh = Math.round(grey * 255).toString(16).padStart(2, '0');
    if (gh) { return '#' + gh + gh + gh; }
    const hex = color.replace('#', '');
    const [r, g, b] = [0, 2, 4].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255);"""),
]

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
    rp = os.path.join(up, POOLRANK)
    if os.path.exists(rp):
        c = open(rp, encoding="utf-8").read()
        if "B2B_GREYS" not in c:
            if all(c.count(o) == 1 for o, _ in POOLRANK_EDITS):
                for o, n in POOLRANK_EDITS:
                    c = c.replace(o, n)
                open(rp, "w", encoding="utf-8").write(c)
            else:
                print("WARN  pool-ranking.component.ts changed upstream: pie stays in the pool colours")
    print("OK  overlay applied")
    return 0


if __name__ == "__main__":
    sys.exit(main())
