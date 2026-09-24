#!/usr/bin/env python3
"""Reissue a finished SchriftOhr Edition (John, 2026-09-24).

"in trying to listen to this book I went through quite a bit to finally get to the
book I wanted" — the pages we add (About This Copy / Proofing Copy, About This
Edition, This Book Is Made to Be Heard) move to the BACK, listed in the Contents;
the author's own front matter stays where the author put it. The title page gains a
reissue line and a pointer to the back. A reissue is a new book — "their place in
the book would be lost, because it is a new book" — so it gets a new identifier.
Optionally the cover is lightened by photographic stops.

    tools/reissue.py BOOK.epub [--stops S] [--shelf-cover cover.jpg] [--dry-run]

Nothing but the spine, the Contents, the title page, the identifier, the modified
date and (with --stops) the cover image changes; every other document is checked
byte for byte against the original, and the book must pass epubcheck and
verify_epub.py before it replaces the original.
"""
import argparse, datetime, pathlib, re, shutil, subprocess, sys, tempfile, uuid, zipfile

OURS_FRONT = {"About This Edition", "This Book Is Made to Be Heard"}
OURS_NOTICE = {"About This Copy", "Proofing Copy", "A Proofing Copy"}
BACK_HOUSE = ["Sources and Acknowledgements", "A Note on the Text", "How These Books Are Made"]
TITLE_PAGE = "text/00-title.xhtml"
COVER = "images/cover.jpg"
REISSUED = "Reissued September 2026"
POINTER = "How this edition was made, and why, is told at the back of the book."
PROOF_LINE = "<strong>This edition is not finished.</strong> It is circulated for reading and correction."

def heading(doc):
    m = re.search(r"<h[1-3][^>]*>(.*?)</h[1-3]>", doc, re.S)
    return re.sub(r"<[^>]+>|\s+", " ", m.group(1)).strip() if m else ""

def stops_lut(s):
    k = 2 ** s   # exposure with a soft shoulder: shadows x2^s, highlights roll off
    return [round(255 * ((i / 255) * k / (1 + (i / 255) * (k - 1)))) for i in range(256)]

def lighten(path, s):
    from PIL import Image
    im = Image.open(path).convert("RGB")
    im.point(stops_lut(s) * 3).save(path, "JPEG", quality=92, optimize=True)

def toc_blocks(ol_inner):
    """The top-level <li> blocks of an <ol>, whole (nested lists included)."""
    blocks, depth, start = [], 0, None
    for m in re.finditer(r"<(/?)li\b[^>]*>", ol_inner):
        if not m.group(1):
            if depth == 0: start = m.start()
            depth += 1
        else:
            depth -= 1
            if depth == 0: blocks.append(ol_inner[start:m.end()])
    return blocks

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("epub"); ap.add_argument("--stops", type=float, default=0)
    ap.add_argument("--shelf-cover"); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    src = pathlib.Path(a.epub).resolve()
    tools = pathlib.Path(__file__).resolve().parent
    work = pathlib.Path(tempfile.mkdtemp(prefix="reissue-", dir=pathlib.Path.home() / "Library/Caches"))
    try:
        with zipfile.ZipFile(src) as z:
            z.extractall(work); original = {n: z.read(n) for n in z.namelist()}
        oebps = work / "OEBPS"
        opf_path = oebps / "content.opf"; opf = opf_path.read_text(encoding="utf-8")
        items = {}
        for tag in re.findall(r"<item\b[^>]*>", opf):
            i = re.search(r'\bid="([^"]+)"', tag); h = re.search(r'\bhref="([^"]+)"', tag)
            if i and h: items[i.group(1)] = h.group(1)
        spine_m = re.search(r"(<spine\b[^>]*>)(.*?)(</spine>)", opf, re.S)
        refs = re.findall(r"<itemref\b[^>]*/>", spine_m.group(2))
        href_of = lambda tag: items[re.search(r'idref="([^"]+)"', tag).group(1)]
        head_of = {r: heading((oebps / href_of(r)).read_text(encoding="utf-8")) for r in refs}

        front = [r for r in refs if head_of[r] in OURS_FRONT]
        notice = [r for r in refs if head_of[r] in OURS_NOTICE]
        keep = [r for r in refs if r not in front and r not in notice]
        closing = [r for r in keep[-1:] if "cover" in href_of(r)]
        body = keep[:len(keep) - len(closing)]
        house_at = next((k for k, r in enumerate(body) if head_of[r] in BACK_HOUSE), len(body))
        order = body[:house_at] + front + body[house_at:] + notice + closing
        assert sorted(order) == sorted(refs), "the spine lost or gained a page"
        moved = [head_of[r] for r in front + notice]

        # spine
        indent = re.search(r"\n(\s*)<itemref", spine_m.group(2))
        sep = "\n" + (indent.group(1) if indent else "    ")
        new_spine = sep + sep.join(order) + "\n  "
        opf = opf[:spine_m.start(2)] + new_spine + opf[spine_m.end(2):]
        # identity: a reissue is a new book
        new_id = f"urn:uuid:{uuid.uuid4()}"
        uid = re.search(r'unique-identifier="([^"]+)"', opf).group(1)
        opf, n = re.subn(rf'(<dc:identifier id="{re.escape(uid)}">)[^<]*(</dc:identifier>)', rf"\g<1>{new_id}\g<2>", opf)
        assert n == 1, f"no dc:identifier id={uid}"
        now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        opf, n = re.subn(r'(<meta property="dcterms:modified">)[^<]*(</meta>)', rf"\g<1>{now}\g<2>", opf)
        assert n == 1, "no dcterms:modified"
        opf_path.write_text(opf, encoding="utf-8")

        # Contents follows the reading order
        nav_path = oebps / "nav.xhtml"; nav = nav_path.read_text(encoding="utf-8")
        # non-greedy: the toc's own end, never a later nav's (landmarks)
        toc = re.search(r'(<nav\b[^>]*epub:type="toc"[^>]*>.*?<ol[^>]*>)(.*?)(</ol>\s*</nav>)', nav, re.S)
        blocks = toc_blocks(toc.group(2))
        # A page sent to the back must be findable there (John: "in the index to
        # be found"): one the Contents never listed gets an entry now.
        listed = {re.search(r'href="([^"#]+)', b).group(1) for b in blocks if 'href="' in b}
        for r in front + notice:
            if href_of(r) not in listed:
                blocks.append(f'<li><a href="{href_of(r)}">{head_of[r]}</a></li>')
        spine_hrefs = [href_of(r) for r in order]
        def pos(block):
            h = re.search(r'href="([^"#]+)', block).group(1)
            return spine_hrefs.index(h) if h in spine_hrefs else len(spine_hrefs)
        ordered = sorted(blocks, key=pos)
        ind = re.search(r"\n(\s*)<li", toc.group(2))
        lsep = "\n" + (ind.group(1) if ind else "      ")
        nav = nav[:toc.start(2)] + lsep + lsep.join(ordered) + "\n    " + nav[toc.end(2):]
        nav_path.write_text(nav, encoding="utf-8")

        # the title page: the reissue, and the way to the back
        tp_path = oebps / TITLE_PAGE; tp = tp_path.read_text(encoding="utf-8")
        assert 'class="reissue"' not in tp, "already reissued — a second run would say it twice"
        lines = [f'<p class="reissue">{REISSUED}</p>', f'<p class="to-the-back">{POINTER}</p>']
        if any(head_of[r] in {"Proofing Copy", "A Proofing Copy"} for r in notice):
            lines.insert(1, f'<p class="proofing-line">{PROOF_LINE}</p>')
        mark = tp.find('<p class="publisher-mark">')
        at = mark if mark >= 0 else tp.rfind("</section>") if "</section>" in tp else tp.rfind("</body>")
        tp = tp[:at] + "\n".join(lines) + "\n" + tp[at:]
        tp_path.write_text(tp, encoding="utf-8")

        if a.stops:
            lighten(oebps / COVER, a.stops)

        # nothing else moved
        changed = {"OEBPS/content.opf", "OEBPS/nav.xhtml", "OEBPS/" + TITLE_PAGE} | ({"OEBPS/" + COVER} if a.stops else set())
        for name, data in original.items():
            if name.endswith("/") or name in changed: continue
            assert (work / name).read_bytes() == data, f"{name} changed"

        tmp = work.parent / (work.name + ".epub")
        subprocess.run(["zip", "-qX0", str(tmp), "mimetype"], cwd=work, check=True)
        subprocess.run(["zip", "-qXr9", str(tmp), ".", "-x", "mimetype", "-x", ".DS_Store"], cwd=work, check=True)
        check = subprocess.run(["epubcheck", "-q", str(tmp)], capture_output=True, text=True)
        assert check.returncode == 0, "epubcheck:\n" + check.stdout[-2000:] + check.stderr[-2000:]
        # The verifier may already flag things in the original (a long s, a
        # doubled stem); the reissue must not add a single finding of its own.
        def findings(path):
            out = subprocess.run([sys.executable, str(tools / "verify_epub.py"), str(path)],
                                 capture_output=True, text=True).stdout
            return {l.strip() for l in out.splitlines() if l.strip()[:1] in ("✗", "⚠")}
        new = findings(tmp) - findings(src)
        assert not new, "verify_epub found what the original did not have:\n" + "\n".join(sorted(new))
        print(f"{src.name}: moved to the back: {', '.join(moved) or 'nothing'}; new id {new_id}"
              + (f"; cover +{a.stops:g} stops" if a.stops else ""))
        if not a.dry_run:
            shutil.copyfile(tmp, src)
            if a.stops and a.shelf_cover:
                lighten(pathlib.Path(a.shelf_cover), a.stops)
        tmp.unlink()
    finally:
        shutil.rmtree(work, ignore_errors=True)

if __name__ == "__main__":
    main()
