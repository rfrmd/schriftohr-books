"""Step three of the Rare Jewel's modernising (John, 2026-11-02): references and abbreviations spelled out, so the
voice reads them as a person would. Joh. 1.16. is John 1:16, vers. 12. is verse 12, Doct. is Doctrine, &c. is etc.,
& is and, and the 17. of Ecclesiastes is the 17th of Ecclesiastes. Imported by rare_jewel_modern_forms.py, which
lists every change it makes."""
import re

BOOKS = {
    'Gen': 'Genesis', 'Exod': 'Exodus', 'Exo': 'Exodus', 'Ex': 'Exodus', 'Levit': 'Leviticus', 'Lev': 'Leviticus',
    'Numb': 'Numbers', 'Num': 'Numbers', 'Deut': 'Deuteronomy', 'Josh': 'Joshua', 'Judg': 'Judges', 'Sam': 'Samuel',
    'King': 'Kings', 'Kings': 'Kings', 'Kin': 'Kings', 'Chron': 'Chronicles', 'Chr': 'Chronicles', 'Chro': 'Chronicles',
    'Neh': 'Nehemiah', 'Esth': 'Esther', 'Psal': 'Psalm', 'Psalm': 'Psalm', 'Ps': 'Psalm', 'Prov': 'Proverbs',
    'Pro': 'Proverbs', 'Eccles': 'Ecclesiastes', 'Eccl': 'Ecclesiastes', 'Cant': 'Song of Songs', 'Isa': 'Isaiah',
    'Esa': 'Isaiah', 'Jer': 'Jeremiah', 'Lam': 'Lamentations', 'Ezek': 'Ezekiel', 'Dan': 'Daniel', 'Hos': 'Hosea',
    'Mic': 'Micah', 'Hab': 'Habakkuk', 'Hag': 'Haggai', 'Zech': 'Zechariah', 'Mal': 'Malachi', 'Mat': 'Matthew',
    'Matth': 'Matthew', 'Matt': 'Matthew', 'Mar': 'Mark', 'Luk': 'Luke', 'Joh': 'John', 'Act': 'Acts', 'Acts': 'Acts',
    'Rom': 'Romans', 'Cor': 'Corinthians', 'Gal': 'Galatians', 'Ephes': 'Ephesians', 'Ephe': 'Ephesians',
    'Eph': 'Ephesians', 'Phil': 'Philippians', 'Col': 'Colossians', 'Thes': 'Thessalonians', 'Thess': 'Thessalonians',
    'Tim': 'Timothy', 'Tit': 'Titus', 'Heb': 'Hebrews', 'Jam': 'James', 'Pet': 'Peter', 'Jud': 'Jude',
    'Rev': 'Revelation', 'Revel': 'Revelation',
}
WORDS = [(r'\bvers\.(?= ?\d)', 'verse'), (r'\bver\.(?= ?\d)', 'verse'), (r'\bv\.(?= ?\d)', 'verse'),
         (r'\bvers\.', 'verse'), (r'\bver\.', 'verse'), (r'\b[Cc]hap\.', None),
         (r'\bDoct\.', 'Doctrine.'), (r'\bAnsw\.', 'Answer.'), (r'\bAns\.', 'Answer.'), (r'\bReas\.', 'Reason.'),
         (r'\bRea\.', 'Reason.'), (r'\bQuest\.', 'Question.'), (r'\bObj\.', 'Objection.'), (r'\bObject\.', 'Objection.'), (r'&c\.', 'etc.'),
         (r' & ', ' and ')]


def ordinal(n):
    n = int(n)
    return f'{n}' + ('th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th'))


def refs(text, log):
    ab = '|'.join(sorted(map(re.escape, BOOKS), key=len, reverse=True))
    pat = re.compile(r'\b(?:([1-3]) )?(' + ab + r')\.\s?(\d+)\.\s?(\d+)((?:\s?(?:,|&|\.|-|\u2013)\s?\d+)*)(\.?)(?=(\s+\S)?)')

    def one(m):
        n, b, ch, v, rest, dot, nxt = m.groups()
        rest = re.sub(r'\s?&\s?', ' and ', rest)
        rest = re.sub(r'\s?[.,]\s?', ', ', rest)
        rest = re.sub(r'\s?[-\u2013]\s?', '\u2013', rest)
        s = (f'{n} ' if n else '') + f'{BOOKS[b]} {ch}:{v}{rest}'
        after = text[m.end():m.end() + 3]
        keep = dot and re.match(r'\s+[A-Z\u201c\u2018(]', after or '')
        s += '.' if keep else ''
        log.append((m.group(0), s))
        return s
    text = pat.sub(one, text)
    # 'the 17. of Ecclesiastes', 'the 14. vers.', 'the 2. Chapter'
    def ordn(m):
        s = f'the {ordinal(m.group(1))} '
        log.append((m.group(0), s)); return s
    text = re.sub(r'\bthe (\d+)\. (?=(?:of|vers|verse|ver|[Cc]hap|[Cc]hapter|Psalm|v)\b)', ordn, text)

    def num_verse(m):
        s = f'verse {m.group(1)}'
        log.append((m.group(0), s)); return s
    text = re.sub(r'\b(\d+)\. vers\.', num_verse, text)
    # 'I but now this does not come off freely': the 1649 spelling of Ay. Only after a stop or comma, before but or
    # that, where I (the pronoun) cannot stand
    def ay(m):
        s = m.group(1) + 'Ay, ' + m.group(3)
        log.append((m.group(0), s)); return s
    text = re.sub(r'([.?!:;,] )I(,? )(but|that is somewhat)\b', ay, text)
    for p, r in WORDS:
        def w(m, r=r):
            s = r if r else ('Chapter' if m.group(0)[0] == 'C' else 'chapter')
            log.append((m.group(0), s)); return s
        text = re.sub(p, w, text)
    return text


PROTECT = {'God', 'Lord', 'Christ', 'Jesus', 'Father', 'Son', 'Ghost', 'Holy', 'Scripture', 'Scriptures', 'Gospel',
           'Saviour', 'Redeemer', 'Almighty', 'Creator', 'Jehovah', 'Messiah', 'King', 'Kings', 'Sabbath', 'Bible',
           'Word', 'I', 'Ay', 'O', 'Oh', 'Amen', 'Parliament', 'English', 'Latin', 'Greek', 'Hebrew', 'Popish',
           'Christian', 'Christians', 'Christianity', 'Apostle', 'Prophet', 'Psalmist', 'Testament', 'Covenant'}


def caps(text, log):
    """A common noun the 1649 page capitalised mid-sentence (Contentment, Soul, Mystery) set in lower case, as we set
    them now. Only where the word follows a word, never after a stop, colon, comma or quotation mark (Burroughs
    begins a quotation with a capital after a comma). Only words the book also uses in lower case, so names stay."""
    lower_seen = set(re.findall(r"\b[a-z][a-z’']+\b", text))
    def one(m):
        w = m.group(2)
        if w in PROTECT or w.lower() not in lower_seen or (w.isupper() and len(w) > 1):
            return m.group(0)
        if w == 'Spirit' and re.search(r'(Holy|the)\s+$', text[max(0, m.start() - 8):m.start() + len(m.group(1))]):
            return m.group(0)
        log.append((w, w.lower()))
        return m.group(1) + w.lower()
    return re.sub(r"(\b[a-z’']+ )([A-Z][a-z’']+)\b", one, text)
