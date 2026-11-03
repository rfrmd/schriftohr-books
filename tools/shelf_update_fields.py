#!/usr/bin/env python3
"""Write the Edition-update fields into shelf.json (docs/edition-updates-standard.md, section 1, in the schriftohr repo).

For every book on the shelf: `build` (the stamp on its About This Copy page), `sha256` (the file as it is in the
repo), and `identifiers` (every dc:identifier its EPUB has carried in this repo's history, current first). `update`
is set only for the ids named after --offer; a book not named keeps whatever `update` it had.

    tools/shelf_update_fields.py FINGERPRINTS.json [--offer ID ...]

FINGERPRINTS.json is the published list from schriftohr.com (audio/editions/fingerprints.json). A book offered whose
file is not in it stops the run: no reader may be offered a copy the site cannot read aloud (section 5).
"""
import hashlib, json, pathlib, re, subprocess, sys, zipfile, io

ROOT = pathlib.Path(__file__).resolve().parent.parent
SHELF = ROOT / 'shelf.json'
PREFIX = 'https://rfrmd.github.io/schriftohr-books/'


def ident(data):
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        opf_path = re.search(r'full-path="([^"]+)"', z.read('META-INF/container.xml').decode()).group(1)
        opf = z.read(opf_path).decode('utf-8')
        uid = re.search(r'unique-identifier="([^"]+)"', opf).group(1)
        return re.search(r'<dc:identifier[^>]*id="%s"[^>]*>([^<]+)<' % re.escape(uid), opf).group(1).strip()


def build_of(data):
    """The build on the About This Copy stamp. A book names its build in that one place: a second build anywhere in
    it (11-03: About This Edition still said "This copy (build 2026-11-02.1)" after the reissue) stops the shelf."""
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        found = {}
        for n in z.namelist():
            if n.endswith('.xhtml'):
                for m in re.findall(r'build (\d{4}-\d\d-\d\d\.\d+)', z.read(n).decode('utf-8', 'replace')):
                    found.setdefault(m, []).append(n.rsplit('/', 1)[-1])
    if len(found) > 1:
        sys.exit(f'the book names {len(found)} builds: ' + '; '.join(f'{b} in {", ".join(f)}' for b, f in sorted(found.items())))
    return next(iter(found), None)


def history(rel):
    """Every identifier the EPUBs in this book's folder have carried, newest first."""
    folder = str(pathlib.PurePosixPath(rel).parent)
    seen = []
    commits = subprocess.run(['git', 'log', '--format=%H', '--', folder], cwd=ROOT, capture_output=True, text=True).stdout.split()
    for c in commits:
        names = subprocess.run(['git', 'ls-tree', '-r', '--name-only', c, folder], cwd=ROOT, capture_output=True, text=True).stdout.split('\n')
        for n in names:
            if n.endswith('.epub'):
                blob = subprocess.run(['git', 'show', f'{c}:{n}'], cwd=ROOT, capture_output=True).stdout
                try:
                    i = ident(blob)
                except Exception:
                    continue
                if i not in seen:
                    seen.append(i)
    return seen


def main():
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    published = set(json.loads(pathlib.Path(args[0]).read_text())['fingerprints'])
    offer = set(args[args.index('--offer') + 1:]) if '--offer' in args else set()
    shelf = json.loads(SHELF.read_text(encoding='utf-8'))
    ids = {b['id'] for b in shelf['books']}
    if offer - ids:
        sys.exit(f'!! not on the shelf: {sorted(offer - ids)}')
    for b in shelf['books']:
        rel = b['epub'][len(PREFIX):]
        data = (ROOT / rel).read_bytes()
        sha = hashlib.sha256(data).hexdigest()
        current = ident(data)
        ids_all = [current] + [i for i in history(rel) if i != current]
        if sha not in published:
            # the shelf names a fingerprint only once the site knows it (section 1)
            if b['id'] in offer:
                sys.exit(f'!! {b["id"]}: {sha[:12]} is not in the published fingerprints; nothing written')
            print(f'{b["id"]:45} not published yet ({sha[:12]}): left as it is')
            continue
        build = build_of(data)
        if build:
            b['build'] = build
        b['sha256'] = sha
        b['identifiers'] = ids_all
        if b['id'] in offer:
            b['update'] = {'offer': True}
        print(f'{b["id"]:45} {build or "-":14} {sha[:12]}  ids {len(ids_all)}  {"OFFER" if b.get("update", {}).get("offer") else ""}')
    SHELF.write_text(json.dumps(shelf, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
