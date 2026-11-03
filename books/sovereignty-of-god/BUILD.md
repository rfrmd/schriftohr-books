Build order from the 2026-10-31 proofing copy (git show 2974d3e~:books/sovereignty-of-god/*.epub):
1. tools/apply_ledger.py page-reading.tsv   (the four readers of the 1918 page images)
2. tools/apply_ledger.py pre-notes.tsv
3. tools/set_footnotes.py notes.tsv
4. tools/modernise_spelling.py spelling-map.tsv --files '/(0[2-9]|1\d|20)-[^/]*\.xhtml$'
5. tools/apply_ledger.py slips.tsv, then modern-pages.tsv, then final-read.tsv --skip
6. tools/publish_proof.py BOOK.epub 2026-11-03.1
