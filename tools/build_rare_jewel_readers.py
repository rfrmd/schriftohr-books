#!/usr/bin/env python3
"""Build the Readers Version of Burroughs's Rare Jewel as a SchriftOhr Edition (proofing copy).

    python3 tools/build_rare_jewel_readers.py [--out DIR]

Text: the policy stage in the private archive,
  schriftohr-editions-working/books/03-burroughs-rare-jewel/readers-version/policy/*.txt
  (format: policy/README.md there; order: policy/manifest.json).
House: the published Classic epub is the donor for the stylesheet, cover, publisher marks,
  closing cover and the pages that are the same for both versions (Made to Be Heard, Why We
  Make These Books, the closing cover). The title page, About This Edition, Sources and the
  Proofing page are written here for the Readers Version.

REVISION is bumped for every copy that goes to John and never reused (house rule, 2026-10-28).
"""
import sys, os, re, html, json, shutil, subprocess, uuid, zipfile, pathlib, datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from edition_parts import cover_xhtml, proofing_xhtml, heard_xhtml, closing_xhtml, PROOFING_CSS, SCRIPT_CSS

REVISION = 7
BUILD = "2026-11-06.7"
T = "The Rare Jewel of Christian Contentment"
AUTHOR = "Jeremiah Burroughs"
POLICY = pathlib.Path("/Volumes/data/Developer/schriftohr-editions-working/books/03-burroughs-rare-jewel/readers-version/policy")
PARA = POLICY.parent / "para"   # the paragraphed stage: same words, breaks and sub-heads added
OUTLINE = POLICY.parent / "outline"   # the numbering stage: his points numbered in the text; built from where it exists
MARK = re.compile(r"^(\d+\.|\(\d+\)|\([a-z]\)) ")
DONOR = pathlib.Path("/Volumes/data/Developer/schriftohr-books/books/rare-jewel-of-christian-contentment/Burroughs_Jeremiah-SchriftOhr_Edition-Rare_Jewel_of_Christian_Contentment.epub")
COVER = pathlib.Path("/Volumes/data/Developer/schriftohr-editions-working/books/03-burroughs-rare-jewel/artwork/covers-2026-11-05/cover-readers.jpg")
NAME = f"Burroughs_Jeremiah-SchriftOhr_Edition-Rare_Jewel_of_Christian_Contentment-Readers_Version-proof-r{REVISION}.epub"

E = lambda s: html.escape(s, quote=False)

GREEK = re.compile(r"[Ͱ-Ͽἀ-῿]+(?:[ Ͱ-Ͽἀ-῿]*[Ͱ-Ͽἀ-῿])?")
HEBREW = re.compile(r"[֐-׿]+(?:[ ֐-׿]*[֐-׿])?")
SOUND = re.compile(r"(</span>) (\([A-Za-z][A-Za-z\-' ]*\))")

def inline(s):
    """Escape, then mark the editor's brackets, Greek and Hebrew with their sounds."""
    s = E(s)
    s = GREEK.sub(lambda m: f'<span xml:lang="grc" lang="grc" class="gk">{m.group(0)}</span>', s)
    s = HEBREW.sub(lambda m: f'<span xml:lang="hbo" lang="hbo" dir="rtl" class="hb">{m.group(0)}</span>', s)
    s = SOUND.sub(r'\1 <span class="ph">\2</span>', s)
    s = re.sub(r"\[([^\]]+)\]", r'<span class="gloss">[\1]</span>', s)
    return s

HEAD_PAT = re.compile(r"^(The |A |An )?(First|Second|Third|Fourth|Fifth|Sixth|Seventh|Eighth|Ninth|Tenth|Eleventh|Twelfth|Thirteenth) (Consideration|Direction|Plea)$")
LABEL_PAT = re.compile(r"^(Doctrine \d\.|Reason \d\.|Use \d?\.?)$")

def render(text, verse_after_title=True):
    paras = [p.strip() for p in text.split("\n\n") if p.strip()]
    title = paras[0][2:]
    out = [f"<h2>{E(title)}</h2>"]
    mode = "body"
    list_open = False
    def close_list():
        nonlocal list_open
        if list_open:
            out.append("</ul>"); list_open = False
    for i, p in enumerate(paras[1:], 1):
        if p.startswith("## "):
            close_list()
            mode = "words" if p.startswith("## Words") else "notes"
            out.append(f'<h3 class="{mode}">{E(p[3:])}</h3>')
            out.append(f'<ul class="{mode}">'); list_open = True
            continue
        if p.startswith("### "):
            close_list(); mode = "body"
            out.append(f"<h3>{E(p[4:])}</h3>"); continue
        if p.startswith("# "):
            close_list(); mode = "body"
            out.append(f"<h3>{E(p[2:])}</h3>"); continue
        if mode == "words":
            m = re.match(r"^([^:]{2,60}): (.+)$", p, re.S)
            out.append(f"<li><b>{E(m.group(1))}</b>: {inline(m.group(2))}</li>" if m else f"<li>{inline(p)}</li>")
            continue
        if mode == "notes":
            m = re.match(r"^([^.]{2,60}\.) (.+)$", p, re.S)
            out.append(f"<li><b>{E(m.group(1))}</b> {inline(m.group(2))}</li>" if m else f"<li>{inline(p)}</li>")
            continue
        if p.startswith("A note on the time."):
            out.append(f'<p class="headnote"><i>{inline(p[len("A note on the time."):].strip())}</i></p>'); continue
        if i == 1 and verse_after_title and re.match(r"^[1-3]? ?[A-Z][a-z]+ \d+:\d+", p):
            out.append(f'<p class="verse">{inline(p)}</p>'); continue
        if HEAD_PAT.match(p) or LABEL_PAT.match(p):
            out.append(f"<h3>{E(p)}</h3>"); continue
        if p == "FINIS.":
            out.append('<p class="finis">FINIS.</p>'); continue
        if re.match(r"^[A-Z][a-z]{2,4}\. \d{1,2}, 16\d\d\.$", p):
            out.append(f'<p class="date">{E(p)}</p>'); continue
        lines = p.split("\n")
        if len(lines) > 1 and all(MARK.match(l) for l in lines):
            out.append('<ul class="plain">' + "".join(f"<li>{inline(l)}</li>" for l in lines) + "</ul>"); continue
        if re.match(r"^\d+\. ", p):
            out.append(f'<p class="point">{inline(p)}</p>'); continue
        if re.match(r"^\([0-9a-z]+\) ", p):
            out.append(f'<p class="sub">{inline(p)}</p>'); continue
        out.append(f"<p>{inline(p)}</p>")
    close_list()
    return title, "\n".join(out)

def page(title, et, cls, inner, bt="bodymatter"):
    return ('<?xml version="1.0" encoding="utf-8"?>\n<html xmlns="http://www.w3.org/1999/xhtml" '
            'xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="en-GB" lang="en-GB">\n'
            f'<head><title>{E(title)}</title><meta charset="utf-8"/>'
            '<link rel="stylesheet" type="text/css" href="../css/style.css"/></head>\n'
            f'<body epub:type="{bt}"><section epub:type="{et}" class="{cls}">\n{inner}\n</section></body></html>\n')

def main():
    out_dir = pathlib.Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else POLICY.parent / "proof"
    out_dir.mkdir(parents=True, exist_ok=True)
    build = out_dir / "build"
    shutil.rmtree(build, ignore_errors=True)
    for d in ("META-INF", "OEBPS/text", "OEBPS/css", "OEBPS/images"):
        (build / d).mkdir(parents=True)
    donor = zipfile.ZipFile(DONOR)
    for f in ("OEBPS/css/style.css", "OEBPS/images/cover.jpg", "OEBPS/images/closing-cover.jpg",
              "OEBPS/images/publisher-mark.png", "OEBPS/images/publisher-mark-dark.png",
              "OEBPS/text/99-closing-cover.xhtml",
              "OEBPS/text/cover.xhtml"):
        (build / f).write_bytes(donor.read(f))
    # the Readers' own cover (the label says Readers Version), and the house pages said true of this book
    (build / "OEBPS/images/cover.jpg").write_bytes(COVER.read_bytes())
    # the closing leaf in the house words for a modern-English text, coloured from the front cover
    sys.path.insert(0, "/Volumes/data/Developer/schriftohr-editions-working/tools")
    import make_closing_cover as mcc
    mcc.build(str(build / "OEBPS/images/closing-cover.jpg"), T, AUTHOR, mcc.palette_from(str(COVER)), paras=mcc.READERS_PARAS)
    (build / "OEBPS/text/02-heard.xhtml").write_text(heard_xhtml(greek=False, latin=True, refs=True, notes=False, scan=False), encoding="utf-8")
    (build / "OEBPS/text/98-why.xhtml").write_text(closing_xhtml(portions=(
        "We break a book only where the author does. Here each sermon is a chapter of its own, listed in the "
        "contents. Within a sermon his points are numbered in the text, so the voice reads straight on.")), encoding="utf-8")
    (build / "OEBPS/css/style.css").open("a", encoding="utf-8").write(
        "\n/* Readers Version */\n"
        ".headnote{text-indent:0;margin:0 0 1.4em;font-size:.95em;color:#444}\n"
        ".gloss{color:#444}\n"
        ".finis,.date{text-indent:0;text-align:center;margin-top:1.6em}\n"
        "h3.words,h3.notes{margin-top:2.4em}\n"
        "ul.words,ul.notes{list-style:none;padding:0;margin:0 0 1.5em;font-size:.93em}\n"
        "ul.words li,ul.notes li{margin:.35em 0;text-indent:0}\n"
        "p.point{text-indent:0;margin-top:1.2em}\n"
        "p.sub{text-indent:0;margin-left:1.2em}\n"
        "ul.plain{list-style:none;padding:0;margin:.6em 0 1em 1.2em}\n"
        "ul.plain li{text-indent:0;margin:.25em 0}\n")
    files = [("cover.xhtml", "Cover")]
    # the proofing page, with this book's own "deliberate" note
    deliberate = ("Two things are deliberate, and are not errors. Each sermon "
                  "opens with a note on the time it was preached and ends with a list of words Burroughs uses "
                  "in an older sense, explained, and the notes on the text; those are the editor's. And where Burroughs gives Scripture in his "
                  "own words, his words stand, with the reference beside them.")
    (build / "OEBPS/text/00-proofing.xhtml").write_text(
        proofing_xhtml(T, AUTHOR, build=f"Readers Version &#183; revision {REVISION} &#183; {BUILD}", deliberate=deliberate)
        .replace("build Readers Version &amp;#183; revision", "Readers Version &#183; revision").replace("&amp;#183;", "&#183;"), encoding="utf-8")
    files.append(("00-proofing.xhtml", "Proofing Copy"))
    (build / "OEBPS/text/00-title.xhtml").write_text(page(T, "titlepage", "titlepage",
        f"<h1>{T}</h1>\n<h2>Wherein is shown the Excellent Temper of a Christian</h2>\n"
        f"<p><strong>{AUTHOR}</strong></p>\n<p>The SchriftOhr Edition</p>\n<p>Readers Version</p>\n"
        "<p>Developed by RFRMD Word Labs LLC</p>\n"
        "<p>For the benefit of readers, prayerfully, to the glory of God.</p>\n"
        f'<p class="reissue">Proofing copy, revision {REVISION}</p>\n'
        '<p class="to-the-back">How this edition was made, and why, is told at the back of the book.</p>\n'
        '<p class="publisher-mark"><img src="../images/publisher-mark.png" alt="RFRMD Word Labs LLC"/></p>', "frontmatter"), encoding="utf-8")
    files.append(("00-title.xhtml", T))
    (build / "OEBPS/text/01-edition-note.xhtml").write_text(page("About This Edition", "preamble", "preamble",
        "<h2>About This Edition</h2>\n"
        f"<p>This is the SchriftOhr edition of <i>{T}</i>, the Readers Version, prepared by RFRMD Word Labs LLC. "
        "Burroughs’s sermons are given whole, every point, example and image in his order, but the language has been brought up to date with care: the older grammar is changed to its modern form, the long sentences of the pulpit are divided, and words no longer in use are given in plain English. Nothing is abridged, summarised or added to what he teaches.</p>\n"
        "<p>Where a word of his carries weight in the argument, or is a term the Reformed churches still use, it is kept as he wrote it, and explained at the end of the sermon under Words in this sermon.</p>\n"
        "<p>Where Burroughs quotes Scripture, the words of the King James Bible are given, with the reference. Where he gives a verse in his own words, or builds his argument on his own wording, his words stand, unquoted, with the reference beside them. Where his reference or attribution was mistaken it is put right, and every such correction is recorded under Notes on the text at the end of the sermon; nothing is corrected silently.</p>\n"
        "<p>Each sermon opens with a short note on the time it was preached, the autumn of 1645, in the civil war, and what the names in it meant then. His long paragraphs are divided at his own turns of thought, and his points are numbered in the text, 1, 2, 3 for the main points, (1), (2), (3) beneath them and (a), (b) beneath those, so that the outline of each sermon can be followed on the page and heard by the ear; there are no headings inside a sermon, so the voice reads straight on. The bare ordinal word goes where the numeral replaces it, and not a word of his is otherwise changed by it.</p>\n"
        "<p>The Greek and Hebrew words Burroughs quotes are given in Latin letters, so they can be read and heard by anyone.</p>\n"
        "<p>The volume of 1649 carried a second work after the Rare Jewel: a sermon on Exodus 14:13, <i>The Saints’ Duty in Times of Extremity</i>. It is kept here, where its printer put it, and given the same way.</p>\n"
        "<p>The Classic Version, Burroughs’s own words in modern spelling, is published beside this one for any reader who wants him unmediated.</p>", "frontmatter"), encoding="utf-8")
    files.append(("01-edition-note.xhtml", "About This Edition"))
    manifest = json.loads((POLICY / "manifest.json").read_text())
    for sec in manifest["sections"]:
        fn = sec["file"][:-4]
        src = OUTLINE / sec["file"]
        if not src.exists():
            src = PARA / sec["file"]
        text = src.read_text(encoding="utf-8")
        title, inner = render(text, verse_after_title=fn.startswith("S"))
        et, bt = ("preface", "frontmatter") if fn == "02-to-the-reader" else ("chapter", "bodymatter")
        (build / f"OEBPS/text/{fn}.xhtml").write_text(page(title, et, "chapter" if et == "chapter" else "preamble", inner, bt), encoding="utf-8")
        files.append((f"{fn}.xhtml", title))
    files.append(("02-heard.xhtml", "This Book Is Made to Be Heard"))
    (build / "OEBPS/text/97-sources.xhtml").write_text(page("Sources and Acknowledgements", "preamble", "preamble",
        "<h2>Sources and Acknowledgements</h2>\n"
        f"<p>Jeremiah Burroughs died in 1646; <i>{T}</i> was printed in 1649 for Peter Cole (Wing B6103; ESTC R32016), and his text has long been in the public domain.</p>\n"
        "<p>Our text descends from the <i>Early English Books Online Text Creation Partnership</i>, whose keyers typed it by hand from images of the 1649 pages. The Partnership has waived every right it holds in that work under the <i>CC0 1.0 Public Domain Dedication</i>. Freely given, and gratefully used. The Readers Version was made from our Classic Version of that text.</p>\n"
        "<p>Burroughs’s text is in the public domain and remains so; we claim nothing in it. The modernised wording, the notes on the time and on the text, the lists of words, the chapter titles and the front and back matter are © RFRMD Word Labs LLC, offered under Creative Commons Attribution–NonCommercial 4.0. The cover is all rights reserved.</p>\n"
        "<p><i>Soli Deo gloria.</i></p>", "backmatter"), encoding="utf-8")
    files.append(("97-sources.xhtml", "Sources and Acknowledgements"))
    files.append(("98-why.xhtml", "How These Books Are Made"))
    files.append(("99-closing-cover.xhtml", "Closing cover"))
    # contents: our pages at the back, listed; the cover and closing cover not listed
    order = ["00-title", "02-to-the-reader"] + [s["file"][:-4] for s in manifest["sections"] if s["file"] != "02-to-the-reader.txt"] + \
            ["02-heard", "01-edition-note", "97-sources", "98-why", "00-proofing"]
    titles = dict((f[:-6], t) for f, t in files)
    titles["00-proofing"] = "Proofing Copy"
    (build / "OEBPS/nav.xhtml").write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n<html xmlns="http://www.w3.org/1999/xhtml" '
        'xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="en-GB" lang="en-GB">\n<head><title>Contents</title>'
        '<meta charset="utf-8"/></head><body>\n<nav epub:type="toc" role="doc-toc" id="toc"><h1>Contents</h1><ol>\n'
        + "\n".join(f'      <li><a href="text/{f}.xhtml">{E(titles[f])}</a></li>' for f in order)
        + '\n    </ol></nav>\n<nav epub:type="landmarks" hidden="hidden"><ol><li><a epub:type="cover" href="text/cover.xhtml">Cover</a></li></ol></nav>\n</body></html>\n', encoding="utf-8")
    spine = ["cover"] + order + ["99-closing-cover"]
    man = ['    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>',
           '    <item id="css" href="css/style.css" media-type="text/css"/>',
           '    <item id="cover-img" href="images/cover.jpg" media-type="image/jpeg" properties="cover-image"/>',
           '    <item id="closing-img" href="images/closing-cover.jpg" media-type="image/jpeg"/>',
           '    <item id="pm" href="images/publisher-mark.png" media-type="image/png"/>',
           '    <item id="pmd" href="images/publisher-mark-dark.png" media-type="image/png"/>']
    for f in spine:
        props = ' properties="svg"' if f in ("cover", "99-closing-cover") and b"<svg" in (build / f"OEBPS/text/{f}.xhtml").read_bytes() else ""
        man.append(f'    <item id="x{f}" href="text/{f}.xhtml" media-type="application/xhtml+xml"{props}/>')
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    (build / "OEBPS/content.opf").write_text(f'''<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid" xml:lang="en-GB">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="uid">urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, "schriftohr:rare-jewel-readers")}</dc:identifier>
    <dc:title>{T}</dc:title>
    <dc:creator id="author">{AUTHOR}</dc:creator>
    <meta refines="#author" property="role" scheme="marc:relators">aut</meta>
    <dc:language>en-GB</dc:language>
    <dc:publisher>SchriftOhr / RFRMD Word Labs LLC</dc:publisher>
    <dc:description>The Readers Version: Burroughs’s sermons on contentment in modern English, whole and in his order, with his weighty words kept and explained; Scripture in the King James Version. Proofing copy, revision {REVISION}.</dc:description>
    <dc:source>EEBO-TCP A30598 (Wing B6103), the 1649 printing, CC0; our Classic Version of it</dc:source>
    <dc:rights>Burroughs’s text is in the public domain and remains so. We claim nothing in it. The modernised wording, the editor’s notes, the lists of words, the chapter titles and the front and back matter are © RFRMD Word Labs LLC, offered under Creative Commons Attribution–NonCommercial 4.0. The cover is all rights reserved. SchriftOhr and RFRMD Word Labs are our marks: this edition may be given away freely; it may not be sold, and it may not be sold under our name.</dc:rights>
    <dc:date>{BUILD[:10]}</dc:date>
    <meta property="dcterms:modified">{now}</meta>
    <meta name="cover" content="cover-img"/>
  </metadata>
  <manifest>
{chr(10).join(man)}
  </manifest>
  <spine>
{chr(10).join(f'    <itemref idref="x{f}"/>' for f in spine)}
  </spine>
</package>
''', encoding="utf-8")
    (build / "META-INF/container.xml").write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n<container version="1.0" '
        'xmlns="urn:oasis:names:tc:opendocument:xmlns:container">\n  <rootfiles>\n'
        '    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>\n'
        '  </rootfiles>\n</container>\n', encoding="utf-8")
    (build / "mimetype").write_text("application/epub+zip")
    ep = out_dir / NAME
    if ep.exists(): ep.unlink()
    subprocess.run(["zip", "-qX0", str(ep), "mimetype"], cwd=build, check=True)
    subprocess.run(["zip", "-qXr9", str(ep), "META-INF", "OEBPS"], cwd=build, check=True)
    shutil.rmtree(build)
    print(f"{ep}  {ep.stat().st_size // 1024} KB  revision {REVISION}  build {BUILD}")

if __name__ == "__main__":
    main()
