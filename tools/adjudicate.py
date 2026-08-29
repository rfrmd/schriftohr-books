#!/usr/bin/env python3
"""Put every doubtful reading beside the actual page, and let a person settle it.

Collation says where two witnesses disagree. It cannot say who is right — only
the printing can, and this is what makes asking it quick: for each disagreement
the line is cropped straight out of the page scan and set above the two readings,
so the work is looking at a picture and pressing a key rather than hunting for a
page and finding a line on it.

    adjudicate.py --collation DIR --scans DIR --vision DIR --out DIR

Writes `review.html`, self-contained, crops embedded. Decisions are kept in the
browser as you go and exported as TSV, which `apply_decisions.py` folds back in.

⚠️ The crop is of the HARPER scan — our base printing. The other witness is a
different copy, and showing its page here would invite settling our text from a
book we are not setting.
"""

import argparse
import base64
import html
import io
import json
import pathlib
import re
import sys
from collections import Counter

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from collate_witnesses import (read_vision, read_plain, tokens, canon_quotes,
                               trim_to_body, WORD)

try:
    from PIL import Image
except ImportError:
    sys.exit('adjudicate: needs Pillow (python3 -m pip install pillow)')

import difflib

DICT = pathlib.Path('/usr/share/dict/words')
SINGLE = {'a', 'i', 'o'}


def real_words():
    if DICT.exists():
        return {w.strip().lower() for w in DICT.open() if w.strip()}
    return set()


def is_english(phrase, vocab):
    ws = [w.strip("'") for w in re.findall(r"[A-Za-z']+", phrase.lower())]
    ws = [w for w in ws if w]
    if not ws:
        return False
    return all((w in SINGLE) if len(w) == 1 else (w in vocab) for w in ws)


def vision_stream(vision_dir):
    """Every Vision word in reading order, each knowing the line it came from."""
    read_vision(vision_dir)
    stream = []
    for line_no, (text, stem, top, bottom) in enumerate(read_vision.records):
        for w in WORD.findall(canon_quotes(text)):
            stream.append((w, line_no, stem, top, bottom))
    return stream


def crop(scans, stem, top, bottom, pad=0.006, width=1150):
    """The strip of page the line sits on, a little air above and below."""
    for ext in ('.tif', '.tiff', '.png', '.jpg', '.jpeg'):
        path = pathlib.Path(scans) / f'{stem}{ext}'
        if path.exists():
            break
    else:
        return None
    im = Image.open(path)
    W, H = im.size
    y0 = max(0, int((top - pad) * H))
    y1 = min(H, int((bottom + pad) * H))
    if y1 <= y0:
        return None
    strip = im.crop((0, y0, W, y1)).convert('L')
    if strip.width > width:
        strip = strip.resize((width, max(1, round(strip.height * width / strip.width))),
                             Image.LANCZOS)
    buf = io.BytesIO()
    strip.save(buf, 'PNG', optimize=True)
    return base64.b64encode(buf.getvalue()).decode()


PAGE_HEAD = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Adjudication — %(title)s</title>
<style>
 :root{--bg:#faf8f4;--ink:#1c1a17;--muted:#6b665e;--line:#e6e1d8;--accent:#f5910c;
       --card:#fff;--ok:#2e7d4f}
 @media (prefers-color-scheme:dark){:root{--bg:#171512;--ink:#ece8e1;--muted:#a39d92;
       --line:#35312a;--card:#211e1a}}
 *{margin:0;padding:0;box-sizing:border-box}
 body{background:var(--bg);color:var(--ink);font:16px/1.5 -apple-system,BlinkMacSystemFont,sans-serif}
 header{position:sticky;top:0;background:var(--bg);border-bottom:1px solid var(--line);
        padding:12px 20px;display:flex;gap:18px;align-items:center;z-index:5;flex-wrap:wrap}
 h1{font-size:17px;font-weight:600}
 .count{color:var(--muted);font-size:14px;font-variant-numeric:tabular-nums}
 button{font:inherit;padding:5px 12px;border:1px solid var(--line);border-radius:7px;
        background:var(--card);color:var(--ink);cursor:pointer}
 button:hover{border-color:var(--accent)}
 .wrap{max-width:1200px;margin:0 auto;padding:18px 20px 120px}
 .spot{border:1px solid var(--line);border-radius:10px;background:var(--card);
       padding:14px 16px;margin:0 0 16px;scroll-margin-top:70px}
 .spot.done{opacity:.5}
 .spot.here{border-color:var(--accent);box-shadow:0 0 0 2px color-mix(in srgb,var(--accent) 25%%,transparent)}
 .n{color:var(--muted);font-size:13px;font-variant-numeric:tabular-nums}
 .strip{margin:10px 0;background:#fff;border:1px solid var(--line);border-radius:6px;
        overflow-x:auto}
 .strip img{display:block;max-width:100%%;height:auto;image-rendering:-webkit-optimize-contrast}
 .ctx{color:var(--muted);font-size:14px;margin:8px 0 2px}
 .ctx b{color:var(--ink)}
 .opts{display:flex;gap:10px;flex-wrap:wrap;margin-top:10px;align-items:center}
 .opt{border:1px solid var(--line);border-radius:7px;padding:6px 12px;cursor:pointer;
      background:var(--bg);font-family:ui-monospace,Menlo,monospace}
 .opt:hover{border-color:var(--accent)}
 .opt.pick{border-color:var(--ok);background:color-mix(in srgb,var(--ok) 14%%,transparent)}
 .opt .who{font:11px/1 -apple-system,sans-serif;color:var(--muted);display:block;margin-bottom:3px}
 input.other{font:inherit;padding:6px 10px;border:1px solid var(--line);border-radius:7px;
             background:var(--bg);color:var(--ink);min-width:180px}
 footer{position:fixed;bottom:0;left:0;right:0;background:var(--bg);
        border-top:1px solid var(--line);padding:10px 20px;font-size:13px;color:var(--muted)}
 kbd{border:1px solid var(--line);border-radius:4px;padding:1px 5px;font:12px ui-monospace,monospace}
 textarea{width:100%%;height:180px;font:12px ui-monospace,monospace;margin-top:10px;
          border:1px solid var(--line);border-radius:8px;padding:10px;background:var(--card);
          color:var(--ink)}
</style></head><body>
<header>
 <h1>%(title)s</h1>
 <span class="count"><span id="done">0</span> / %(total)d settled</span>
 <button onclick="jumpNext()">Next unsettled &darr;</button>
 <button onclick="exportTSV()">Export decisions</button>
 <button onclick="if(confirm('Forget every decision on this page?')){localStorage.removeItem(KEY);location.reload()}">Reset</button>
</header>
<div class="wrap">
<p class="ctx">Each strip below is the line as it stands in the %(printing)s.
Pick the reading it actually shows. <kbd>1</kbd> takes the first, <kbd>2</kbd> the
second, <kbd>3</kbd> focuses the free-text box; <kbd>j</kbd> / <kbd>k</kbd> move.
Decisions are kept in this browser as you go — export when you are done.</p>
"""

PAGE_FOOT = """</div>
<footer>Nothing here is applied to the book until the exported decisions are folded
back in. Unsettled places keep both readings and stay in the ledger.</footer>
<script>
const KEY = %(key)s;
let picks = {};
try { picks = JSON.parse(localStorage.getItem(KEY) || '{}'); } catch (e) { picks = {}; }
let cur = 0;
const spots = [...document.querySelectorAll('.spot')];

function save(){ try{ localStorage.setItem(KEY, JSON.stringify(picks)); }catch(e){} paint(); }
function paint(){
  document.getElementById('done').textContent = Object.keys(picks).length;
  spots.forEach((s,i)=>{
    const id = s.dataset.id;
    s.classList.toggle('done', picks[id] !== undefined);
    s.classList.toggle('here', i === cur);
    s.querySelectorAll('.opt').forEach(o=>
      o.classList.toggle('pick', picks[id] === o.dataset.val));
  });
}
function choose(id, val){ if(val===null||val===undefined||val===''){delete picks[id];}else{picks[id]=val;} save(); }
function go(i){ cur = Math.max(0, Math.min(spots.length-1, i)); spots[cur].scrollIntoView({block:'center'}); paint(); }
function jumpNext(){
  for (let i = cur+1; i < spots.length; i++) if (picks[spots[i].dataset.id]===undefined) return go(i);
  for (let i = 0; i <= cur; i++) if (picks[spots[i].dataset.id]===undefined) return go(i);
}
document.addEventListener('click', e=>{
  const o = e.target.closest('.opt'); if(!o) return;
  const s = o.closest('.spot'); cur = spots.indexOf(s);
  choose(s.dataset.id, o.dataset.val); jumpNext();
});
document.addEventListener('keydown', e=>{
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
    if (e.key === 'Enter') { const s = e.target.closest('.spot');
      choose(s.dataset.id, e.target.value.trim()); e.target.blur(); jumpNext(); }
    return;
  }
  const s = spots[cur]; if(!s) return;
  const opts = [...s.querySelectorAll('.opt')];
  if (e.key === '1' && opts[0]) { choose(s.dataset.id, opts[0].dataset.val); jumpNext(); }
  else if (e.key === '2' && opts[1]) { choose(s.dataset.id, opts[1].dataset.val); jumpNext(); }
  else if (e.key === '3') { const i = s.querySelector('input.other'); if(i){ i.focus(); e.preventDefault(); } }
  else if (e.key === 'j') go(cur+1);
  else if (e.key === 'k') go(cur-1);
  else if (e.key === 'n') jumpNext();
});
function exportTSV(){
  let out = 'id\\tchosen\\n';
  spots.forEach(s=>{ const id = s.dataset.id;
    if (picks[id] !== undefined) out += id + '\\t' + picks[id] + '\\n'; });
  const ta = document.createElement('textarea');
  ta.value = out; document.querySelector('.wrap').prepend(ta); ta.select();
  alert(Object.keys(picks).length + ' decisions are in the box at the top — copy them into decisions.tsv');
}
paint(); if (spots.length) go(0);
</script></body></html>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--vision', required=True)
    ap.add_argument('--plain', required=True)
    ap.add_argument('--scans', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--title', default='The Adventures of Sherlock Holmes')
    ap.add_argument('--printing', default='Harper &amp; Brothers scan')
    ap.add_argument('--start', default='')
    ap.add_argument('--end', default='')
    ap.add_argument('--limit', type=int, default=0,
                    help='only the first N doubtful places (for a quick look)')
    ap.add_argument('--include-resolvable', action='store_true',
                    help='also show the ones a rule already settles')
    args = ap.parse_args()

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    vocab = real_words()

    stream = vision_stream(args.vision)
    A0 = [w for w, *_ in stream]
    A, offset = trim_to_body(A0, args.start, args.end)
    stream = stream[offset:offset + len(A)]
    p_lines, _ = read_plain(args.plain)
    B, _ = trim_to_body(tokens('\n'.join(p_lines)), args.start, args.end)

    sm = difflib.SequenceMatcher(None, [w.lower() for w in A],
                                 [w.lower() for w in B], autojunk=False)
    spots, auto = [], 0
    for tag, a1, a2, b1, b2 in sm.get_opcodes():
        if tag == 'equal':
            continue
        v = ' '.join(A[a1:a2])
        p = ' '.join(B[b1:b2])
        rv, rp = is_english(v, vocab), is_english(p, vocab)
        settled = (rv != rp) and v and p           # exactly one is English
        if settled and not args.include_resolvable:
            auto += 1
            continue
        # which line does this sit on? the first word's, or the previous word's
        # when the witness has nothing here.
        idx = a1 if a1 < len(stream) else len(stream) - 1
        if a1 >= a2:
            idx = max(0, a1 - 1)
        _, line_no, stem, top, bottom = stream[min(idx, len(stream) - 1)]
        spots.append({
            'id': f'{a1}', 'vision': v, 'plain': p, 'stem': stem,
            'top': top, 'bottom': bottom,
            'before': ' '.join(A[max(0, a1 - 7):a1]),
            'after': ' '.join(A[a2:a2 + 7]),
            'auto': settled, 'winner': (v if rv else p) if settled else None,
        })
        if args.limit and len(spots) >= args.limit:
            break

    print(f'{len(spots):,} places to look at'
          + (f'  ({auto:,} already settled by rule, not shown)' if not args.include_resolvable else ''))

    body = []
    missing = 0
    for i, s in enumerate(spots, 1):
        png = crop(args.scans, s['stem'], s['top'], s['bottom'])
        if png is None:
            missing += 1
        img = (f'<div class="strip"><img alt="" src="data:image/png;base64,{png}"></div>'
               if png else '<p class="ctx">(no page image for this line)</p>')
        opts = []
        for who, val in (('this scan', s['vision']), ('other witness', s['plain'])):
            label = html.escape(val) if val else '<i>(nothing)</i>'
            opts.append(f'<div class="opt" data-val="{html.escape(val)}">'
                        f'<span class="who">{who}</span>{label}</div>')
        body.append(
            f'<div class="spot" data-id="{s["id"]}">'
            f'<div class="n">{i} of {len(spots)} · {html.escape(s["stem"][-4:])}</div>'
            f'{img}'
            f'<div class="ctx">…{html.escape(s["before"])} '
            f'<b>[ ? ]</b> {html.escape(s["after"])}…</div>'
            f'<div class="opts">{"".join(opts)}'
            f'<input class="other" placeholder="or type what the page says…"></div>'
            f'</div>')
    if missing:
        print(f'⚠️ {missing} spots had no page image')

    key = json.dumps(f'adjudicate:{args.title}')
    page = (PAGE_HEAD % {'title': html.escape(args.title), 'total': len(spots),
                         'printing': args.printing}
            + '\n'.join(body) + PAGE_FOOT % {'key': key})
    target = out / 'review.html'
    target.write_text(page, encoding='utf-8')
    print(f'wrote {target}  ({target.stat().st_size/1e6:.1f} MB)')


if __name__ == '__main__':
    sys.exit(main())
