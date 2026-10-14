# mempool for Umbrel (blake2b)

An Umbrel app that runs the mempool fork [Horizon-btc/mempool](https://github.com/Horizon-btc/mempool)
(mempool.guide) against your own node, wrapped in the same monochrome theme as Blake2b ASIC Control and
DATUM Gateway, with your pool **Blockchain Bandit** recognised and its blocks shown in gold.

Not pinned to a release: `UPSTREAM_TAG` holds the newest upstream release; the weekly `upstream-sync`
workflow looks for a newer one, checks the overlay still fits, bumps the version and tags it, and the tag
builds the images and updates the store.

## Layout

| Path | What it is |
|---|---|
| `blake2b-mempool/` | the Umbrel app folder (manifest, compose, icon) |
| `overlay/frontend/src/resources/blake2b/` | `theme.css` (look + gold) and `bandit.js` (light/dark switch, gold marking) |
| `overlay/frontend/src/resources/mining-pools/blockchainbandit.svg` | the pool's logo |
| `overlay/extra-pools.json` | pools of our own added to the shared pool list (Blockchain Bandit, id 9000) |
| `tools/apply_overlay.py` | copies the overlay over an upstream checkout and applies the two anchored patches |
| `tools/sync_upstream.py` | finds the newest upstream release, test-applies the overlay, bumps the version |
| `.github/workflows/image.yml` | tag `mempool-vX.Y.Z` builds frontend + backend (amd64, arm64) to ghcr.io and updates the store |

## How a build works

1. Check out upstream at `UPSTREAM_TAG`.
2. `tools/apply_overlay.py` adds the theme, the script and the logo, links them from `index.mempool.html`, and adds
   `extra-pools.json` to the pool list the backend imports (`pools-updater.ts`).
3. Upstream's own `docker/init.sh` and Dockerfiles build the images, so upstream's build recipe is followed as it changes.

## Pool and ID

`overlay/extra-pools.json` registers the pool. The tag it looks for is `Blockchain Bandit` in the block's
coinbase text, so set that as the DATUM Gateway **Coinbase tag** (Config page). The `id` (9000) is the pool's
unique number in mempool's database; it is far above the shared list (which ends at 478) so it cannot clash.
The pool is flagged as a DATUM pool, which also makes the explorer check it before every other pool.
