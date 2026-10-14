#!/usr/bin/env python3
"""Follow upstream releases of the mempool fork.

  sync_upstream.py [--repo-dir .] [--check-only] [--force-tag TAG]
  sync_upstream.py --bump "what changed"     # new app version for a UI/packaging change, no upstream change

Upstream names its releases v3.4-dev, v3.4-beta5, v3.4-beta6 ...: plain version sorting gets that wrong, so the
newest release is the tag that was created last. A new tag is test-applied (tools/apply_overlay.py --check);
if the overlay no longer fits, exit 2 and change nothing. Otherwise the patch version is bumped.
"""
import argparse, os, re, subprocess, sys, tempfile


def run(*a, **k):
    return subprocess.run(a, check=True, text=True, capture_output=True, **k).stdout


def repo_url(d):
    name = open(os.path.join(d, "UPSTREAM_REPO")).read().strip()
    return "https://github.com/%s.git" % name


def latest(url):
    with tempfile.TemporaryDirectory() as t:
        run("git", "clone", "-q", "--bare", "--filter=blob:none", url, t)
        out = run("git", "-C", t, "for-each-ref", "--sort=-creatordate", "--format=%(refname:short)", "refs/tags")
    tags = [x for x in out.split() if x.startswith("v")]
    if not tags:
        raise SystemExit("no release tags found at " + url)
    return tags[0]


def bump(d, note, stored, new):
    app = os.path.join(d, "blake2b-mempool")
    mp, cp = os.path.join(app, "umbrel-app.yml"), os.path.join(app, "docker-compose.yml")
    m = open(mp).read()
    old = re.search(r'^version: "([\d.]+)"', m, re.M).group(1)
    x, y, z = old.split(".")
    nv = "%s.%s.%d" % (x, y, int(z) + 1)
    m = m.replace('version: "%s"' % old, 'version: "%s"' % nv).replace("?v=" + old, "?v=" + nv)
    line = note if note else "Built on upstream mempool %s (was %s)." % (new, stored)
    notes = "releaseNotes: |-\n  **%s**\n\n  - %s\n\n  " % (nv, line)
    m = re.sub(r"releaseNotes: \|-\n  ", lambda _: notes, m, count=1)
    open(mp, "w").write(m)
    c = open(cp).read()
    open(cp, "w").write(re.sub(r"(blake2b-mempool-(?:frontend|backend):)" + re.escape(old), r"\g<1>" + nv, c))
    open(os.path.join(d, "UPSTREAM_TAG"), "w").write(new + "\n")
    print("NEW_VERSION=%s" % nv)
    print("UPSTREAM_TAG=%s" % new)
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-dir", default=".")
    ap.add_argument("--check-only", action="store_true")
    ap.add_argument("--force-tag")
    ap.add_argument("--bump", metavar="NOTE")
    a = ap.parse_args()
    d = a.repo_dir
    stored = open(os.path.join(d, "UPSTREAM_TAG")).read().strip()
    if a.bump:
        return bump(d, a.bump, stored, stored)
    url = repo_url(d)
    new = a.force_tag or latest(url)
    if new == stored:
        print("NOTHING_TO_DO (upstream %s)" % new)
        return 0
    print("upstream: %s -> %s" % (stored, new))
    with tempfile.TemporaryDirectory() as t:
        src = os.path.join(t, "up")
        run("git", "clone", "-q", "--depth", "1", "--branch", new, url, src)
        v = subprocess.run([sys.executable, "-I", os.path.join(d, "tools/apply_overlay.py"), src, "--check"],
                           text=True, capture_output=True)
        print(v.stdout + v.stderr)
        if v.returncode:
            print("INCOMPATIBLE: upstream %s changed something the overlay depends on" % new)
            return 2
    if a.check_only:
        print("COMPATIBLE")
        return 0
    return bump(d, "", stored, new)


if __name__ == "__main__":
    sys.exit(main())
