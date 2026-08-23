#!/usr/bin/env python3
"""How a Greek or Hebrew word sounds, written for an English reader.

The house manner (John, 2026-08-23): every word in a non-Latin script is
followed by its sound in brackets — θανατοῦτε (thah-nah-TOO-teh) — so a
reader who does not read the script still has the word, and so the app's
voice has something to say.

Greek uses the Erasmian values an English-speaking student is taught. The
stress is not guessed: the accents the printer set say where it falls, and
that syllable is capitalised. Hebrew follows the pointing where it is
there, and the consonants where it is not; Hebrew stress is final far more
often than not, so the last syllable takes it unless a metheg says otherwise.
"""
import re, unicodedata

# --- Greek -----------------------------------------------------------------
DIGRAPHS = [('ου','oo'), ('ΟΥ','oo'), ('ει','ay'), ('ΕΙ','ay'), ('αι','eye'),
            ('ΑΙ','eye'), ('οι','oy'), ('ΟΙ','oy'), ('υι','wee'), ('ευ','yoo'),
            ('ΕΥ','yoo'), ('ηυ','ay-oo'), ('αυ','ow'), ('ΑΥ','ow'),
            ('γγ','ng'), ('γκ','nk'), ('γχ','nkh'), ('γξ','nx')]
SINGLE = {'α':'ah','β':'b','γ':'g','δ':'d','ε':'eh','ζ':'dz','η':'ay','θ':'th',
          'ι':'ee','κ':'k','λ':'l','μ':'m','ν':'n','ξ':'x','ο':'oh','π':'p',
          'ρ':'r','σ':'s','ς':'ss','τ':'t','υ':'oo','φ':'f','χ':'kh','ψ':'ps',
          'ω':'oh'}
VOWELS = set('αεηιουω')

def _strip(ch):
    """The bare letter, and whether it carried an accent or a rough breathing."""
    d = unicodedata.normalize('NFD', ch)
    base = d[0]
    marks = d[1:]
    accent  = any(m in '́̀͂' for m in marks)   # acute, grave, circumflex
    rough   = '̔' in marks                               # rough breathing = an h
    iota    = 'ͅ' in marks
    return base.lower(), accent, rough, iota

# A Greek syllable is open: a single consonant between two vowels belongs to
# the SECOND. Two consonants split unless they make a cluster Greek can begin a
# word with — στ, πρ, θρ and their like — which is why καταργηθήσεται divides
# kah-tar-gay-THAY-seh-tie and not kaht-ahrg-ayth-AYS-eht-eye.
ONSETS = {'pr','br','tr','dr','kr','gr','fr','thr','khr','pl','bl','kl','gl',
          'fl','thl','khl','kn','gn','pn','mn','sp','st','sk','sf','sth','skh',
          'sm','sn','ps','ks','dz','tm','pt','kt','khth','fth'}

def greek_sound(word):
    """One Greek word, respelled. Returns '' for anything not Greek."""
    letters = [_strip(c) for c in word
               if unicodedata.normalize('NFD', c)[0].isalpha()]
    if not letters:
        return ''
    # 1. units: vowel groups (with their accent) and consonants
    units, i = [], 0
    while i < len(letters):
        base, acc, rough, _ = letters[i]
        pair = base + (letters[i+1][0] if i+1 < len(letters) else '')
        hit = next((v for k, v in DIGRAPHS if k == pair), None)
        if hit and base in VOWELS:
            units.append(('V', ('h' if rough else '') + hit,
                          acc or letters[i+1][1])); i += 2
        elif hit:
            units.append(('C', hit, False)); i += 2
        elif base in VOWELS:
            units.append(('V', ('h' if rough else '') + SINGLE.get(base, base), acc)); i += 1
        else:
            units.append(('C', SINGLE.get(base, base), False)); i += 1
    # 2. syllables, dividing before the nucleus
    sylls, pend, stressed = [], [], None
    for kind, txt, acc in units:
        if kind == 'C':
            pend.append(txt); continue
        onset = ''
        if len(pend) == 1:
            onset = pend[0]
        elif len(pend) > 1:
            two = pend[-2] + pend[-1]
            if two in ONSETS:
                onset = two; pend = pend[:-2]
            else:
                onset = pend[-1]; pend = pend[:-1]
            if sylls: sylls[-1] += ''.join(pend)
        if len(pend) == 1 and onset == pend[0]:
            pend = []
        if acc: stressed = len(sylls)
        sylls.append(onset + txt)
        pend = []
    if pend:                                   # a word ending in consonants
        if sylls: sylls[-1] += ''.join(pend)
        else: sylls = [''.join(pend)]
    sylls = [_readable(x) for x in sylls if x]
    if not sylls: return ''
    if len(sylls) == 1:
        return sylls[0]                        # nothing to contrast: no stress mark
    if stressed is None or stressed >= len(sylls):
        stressed = max(0, len(sylls) - 2)      # unaccented: the penult, the common case
    sylls[stressed] = sylls[stressed].upper()
    return '-'.join(sylls)


def _readable(s):
    """Small mercies for an English eye: 'ar' not 'ahr', 'tie' not 'teye'."""
    s = re.sub(r'ah(?=[rl]$)', 'a', s)
    if len(s) > 3 and s.endswith('eye'):
        s = s[:-3] + 'ie'
    return s

# --- Hebrew ----------------------------------------------------------------
HB_CONS = {'א':'','ב':'v','ג':'g','ד':'d','ה':'h','ו':'v','ז':'z','ח':'kh','ט':'t',
           'י':'y','כ':'kh','ך':'kh','ל':'l','מ':'m','ם':'m','נ':'n','ן':'n','ס':'s',
           'ע':'','פ':'f','ף':'f','צ':'ts','ץ':'ts','ק':'k','ר':'r','ש':'sh','ת':'t'}
HB_VOW = {'ְ':'e','ֱ':'e','ֲ':'a','ֳ':'o','ִ':'i','ֵ':'ay',
          'ֶ':'eh','ַ':'ah','ָ':'ah','ֹ':'oh','ֻ':'u','ּ':''}
DAGESH_HARD = {'ב':'b','כ':'k','ך':'k','פ':'p','ף':'p','ג':'g','ד':'d','ת':'t'}

def hebrew_sound(word):
    out, i = [], 0
    chars = list(word)
    while i < len(chars):
        c = chars[i]
        if c in HB_CONS:
            marks = ''
            j = i + 1
            while j < len(chars) and unicodedata.category(chars[j]) == 'Mn':
                marks += chars[j]; j += 1
            cons = DAGESH_HARD.get(c, HB_CONS[c]) if 'ּ' in marks else HB_CONS[c]
            out.append(cons)
            for m in marks:
                if m in HB_VOW and HB_VOW[m]:
                    out.append(HB_VOW[m] + '·')
            i = j
            continue
        i += 1
    s = ''.join(out)
    sylls = [x for x in s.split('·') if x]
    if not sylls: return ''
    sylls[-1] = sylls[-1].upper()                 # Hebrew stress is usually final
    return '-'.join(sylls)

def sound(word, script='grc'):
    return hebrew_sound(word) if script == 'hbo' else greek_sound(word)

def gloss(text, script='grc'):
    """A whole quoted phrase, word by word."""
    parts = [sound(w, script) for w in re.split(r'[\s·]+', text.strip()) if w]
    return ' '.join(p for p in parts if p)

if __name__ == '__main__':
    for w, want in [('θανατοῦτε','thah-nah-TOO-teh'), ('πράξεις','PRAX-ayss'),
                    ('φρόνημα','FRO-nay-mah'), ('ἐκ μέρους','ek MEH-rooss'),
                    ('καταργηθήσεται','kah-tar-gay-THAY-seh-tie'),
                    ('συνεσταυρώθη','soo-neh-stow-ROH-thay'),
                    ('ἁμαρτίας','hah-mar-TEE-ass'), ('μυστήριον','moo-STAY-ree-on'),
                    ('הִתְיַצְּבוּ','heet-yahts-tseh-VOO')]:
        script = 'hbo' if any('֐' <= c <= '׿' for c in w) else 'grc'
        print(f'{w:20} → {gloss(w, script):32} (by hand: {want})')
