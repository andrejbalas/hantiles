#!/usr/bin/env python3
"""Builds HanTiles/Resources/Dictionaries/search_index.json

Usage: build_index.py makemeahanzi/dictionary.txt complete-hsk-vocabulary/complete.json cedict_ts.u8 out.json

Sources
  - makemeahanzi dictionary.txt: every character that has stroke data (LGPL)
  - complete-hsk-vocabulary complete.json: HSK 2.0 + 3.0 words with frequency
    ranks (MIT; meanings from CC-CEDICT)
  - CC-CEDICT: extra 2-4 character words not in HSK (CC BY-SA 4.0)

Output (short keys keep the file small), plus "s2t" / "t2s" character maps:
  {"c": [{"h": 字, "p": "zì", "r": ["zi4", ...], "g": [glosses], "f": rank}],
   "w": [{"h": 汉字, "t": 漢字, "p": "hàn zì", "n": "han4 zi4", "g": [...], "f": rank}]}
Gloss tiers: plain = exact meaning; "^" = meaning followed by a usage note, e.g.
"you (informal)"; "~" = qualified or secondary meaning, e.g. "(coll.) what".
"""
import json, math, re, sys, unicodedata
from collections import defaultdict

MMAH, HSK, CEDICT, OUT = sys.argv[1:5]

TONE_MARKS = {
    'ā': ('a', 1), 'á': ('a', 2), 'ǎ': ('a', 3), 'à': ('a', 4),
    'ē': ('e', 1), 'é': ('e', 2), 'ě': ('e', 3), 'è': ('e', 4),
    'ī': ('i', 1), 'í': ('i', 2), 'ǐ': ('i', 3), 'ì': ('i', 4),
    'ō': ('o', 1), 'ó': ('o', 2), 'ǒ': ('o', 3), 'ò': ('o', 4),
    'ū': ('u', 1), 'ú': ('u', 2), 'ǔ': ('u', 3), 'ù': ('u', 4),
    'ǖ': ('v', 1), 'ǘ': ('v', 2), 'ǚ': ('v', 3), 'ǜ': ('v', 4), 'ü': ('v', 0),
    'ń': ('n', 2), 'ň': ('n', 3), 'ǹ': ('n', 4), 'ḿ': ('m', 2),
}
SYL_RE = re.compile(r'^[a-z]+[1-5]$')
MARK_VOWELS = {'a': 'āáǎà', 'e': 'ēéěè', 'i': 'īíǐì', 'o': 'ōóǒò', 'u': 'ūúǔù', 'v': 'ǖǘǚǜ'}


def marks_to_numeric(syl):
    syl = unicodedata.normalize('NFC', syl.lower().strip())
    tone, out = 5, []
    for ch in syl:
        if ch in TONE_MARKS:
            base, t = TONE_MARKS[ch]
            out.append(base)
            if t:
                tone = t
        else:
            out.append(ch)
    s = ''.join(out)
    return s + str(tone) if re.fullmatch(r'[a-z]+', s) else None


def numeric_to_marks(syl):
    base, tone = syl[:-1], int(syl[-1])
    if tone == 5:
        return base.replace('v', 'ü')
    # standard placement rules
    if 'a' in base:
        idx = base.index('a')
    elif 'e' in base:
        idx = base.index('e')
    elif 'ou' in base:
        idx = base.index('o')
    else:
        idx = max(i for i, c in enumerate(base) if c in 'aeiouv') if any(c in 'aeiouv' for c in base) else -1
    if idx < 0:
        return base
    marked = base[:idx] + MARK_VOWELS[base[idx]][tone - 1] + base[idx + 1:]
    return marked.replace('v', 'ü')


def norm_numeric(syl):
    s = syl.lower().replace('ü', 'v').replace('u:', 'v')
    return s if SYL_RE.match(s) else None


BAD_MEANING = re.compile(r'(variant of|^surname|used in |archaic|^see |abbr\. for|old name for|japanese|taiwan pr\.|^cl:|^pr\.)', re.I)


REGISTER = re.compile(r'^\((coll|slang|dialect|old|literary|archaic|Cantonese|onom|euphemism)[^)]*\)', re.I)


def clean_meanings(meanings):
    return [m for m in meanings if not BAD_MEANING.search(m.strip())]


ABBREVIATION = re.compile(r'(?:[^\W\d_]{1,2}\.){2,}')   # e.g.  q.e.d.  ph.d.  a.m.


def clean_word(word):
    """Keeps the dots of abbreviations such as "e.g." and drops other stray dots."""
    dotted = word if word.endswith('.') else word + '.'
    return dotted if ABBREVIATION.fullmatch(dotted) else word.strip('.')


def is_cjk(ch):
    return '⺀' <= ch <= '鿿' or '豈' <= ch <= '﫿' or ch >= '\U00020000'


def clean_gloss(piece):
    """One English meaning, lowercased, with punctuation and Chinese characters
    removed. Letters with accents ("hán tự", "café"), abbreviations ("q.e.d.") and
    decimals ("0.01") are kept intact."""
    g = unicodedata.normalize('NFC', piece.lower().strip())
    g = re.sub(r'\.{2,}', ' ', g)
    g = ''.join(ch if (ch.isalpha() and not is_cjk(ch)) or ch.isdigit() or ch in "' -." else ' '
                for ch in g)
    g = ' '.join(w for w in (clean_word(w) for w in g.split()) if w)
    g = re.sub(r'\b(sth|sb|sb\'s|one\'s|oneself|etc)\b', ' ', g)
    g = re.sub(r'\s+', ' ', g).strip()
    return re.sub(r'^(to|a|an|the) ', '', g).strip()


def glosses(meanings, limit=None):
    out, seen = [], set()
    for m in meanings:
        for part in m.split(';'):
            if BAD_MEANING.search(part.strip()):
                continue
            stripped = part.strip()
            marker = '~' if stripped.startswith(('(', '[')) else ('^' if ('(' in part or '[' in part) else '')
            part = re.sub(r'\([^)]*\)', ' ', part)
            part = re.sub(r'\[[^\]]*\]', ' ', part)
            for piece in re.split(r'[,/]', part):
                g = clean_gloss(piece)
                if not g or len(g.split()) > 5 or g in seen:
                    continue
                seen.add(g)
                out.append(marker + g)
    return out[:limit] if limit else out


# ---------- characters with stroke data ----------
chars, order = {}, []
for line in open(MMAH, encoding='utf-8'):
    e = json.loads(line)
    c = e['character']
    chars[c] = {
        'mm': [r for r in (marks_to_numeric(p) for p in e.get('pinyin', [])) if r],
        'def': glosses([e['definition']]) if e.get('definition') else [],
        'rank': None,
        'forms': [],                       # single-character HSK forms
        'weights': defaultdict(float),     # reading -> usage weight
    }
    order.append(c)

# ---------- HSK words ----------
words, seen_words = [], set()
for e in json.load(open(HSK, encoding='utf-8')):
    w, rank = e['simplified'], e['frequency']
    clean_forms = []
    for form in e['forms']:
        tr = form['transcriptions']
        numeric = [norm_numeric(s) for s in tr['numeric'].split()]
        proper = tr['pinyin'][:1].isupper()
        marks = tr['pinyin'].lower().split()
        if len(numeric) != len(w) or None in numeric or len(marks) != len(w):
            continue
        meanings = clean_meanings(form['meanings'])
        if proper and len(w) == 1:
            meanings = []                  # 中 Zhōng "China", surnames: proper-noun senses of single characters
        if len(w) == 1 and w in chars:
            chars[w]['forms'].append({'n': numeric[0], 'p': marks[0], 'm': meanings})
        if meanings:
            clean_forms.append((numeric, marks, meanings, form.get('traditional')))
    for k, (numeric, marks, meanings, trad) in enumerate(clean_forms):
        entry = {'h': w, 'p': ' '.join(marks), 'n': ' '.join(numeric), 'g': glosses(meanings), 'f': rank}
        if trad and trad != w:
            entry['t'] = trad
        words.append(entry)
        seen_words.add((w, entry['n']))
        weight = (1.0 / rank) if k == 0 else 0.0
        for i, c in enumerate(w):
            if c not in chars:
                continue
            chars[c]['rank'] = rank if chars[c]['rank'] is None else min(chars[c]['rank'], rank)
            r = numeric[i]
            if len(w) > 1:
                # max per word, neutral tones in compounds count half
                chars[c]['weights'][r] += weight * (0.5 if r.endswith('5') else 1.0)

char_rank = {c: (d['rank'] if d['rank'] is not None else 60000 + i) for i, (c, d) in enumerate((c, chars[c]) for c in order)}

# ---------- CC-CEDICT extra words ----------
line_re = re.compile(r'^(\S+) (\S+) \[([^\]]+)\] /(.*)/\s*$')
extra = 0
for line in open(CEDICT, encoding='utf-8'):
    if line.startswith('#'):
        continue
    m = line_re.match(line)
    if not m:
        continue
    trad, simp, pinyin, defs = m.groups()
    if not (2 <= len(simp) <= 4) or any(c not in chars or char_rank[c] >= 60000 for c in simp):
        continue
    if pinyin[:1].isupper():
        continue                           # proper nouns
    numeric = [norm_numeric(s) for s in pinyin.split()]
    if len(numeric) != len(simp) or None in numeric:
        continue
    key = (simp, ' '.join(numeric))
    if key in seen_words:
        continue
    meanings = clean_meanings(defs.split('/'))
    if not meanings:
        continue
    g = glosses(meanings, limit=4)
    if not g:
        continue
    ranks = [char_rank[c] for c in simp]
    est = 25000 + int(math.exp(sum(math.log(r) for r in ranks) / len(ranks)))
    entry = {'h': simp, 'p': ' '.join(numeric_to_marks(s) for s in numeric), 'n': key[1], 'g': g, 'f': est}
    if trad != simp:
        entry['t'] = trad
    words.append(entry)
    seen_words.add(key)
    extra += 1

# Most common polyphonic characters: the reading a learner expects to see on a tile.
OVERRIDES = {
    '长': 'cháng', '行': 'xíng', '着': 'zhe', '为': 'wèi', '重': 'zhòng', '觉': 'jué', '吧': 'ba',
    '啊': 'a', '得': 'de', '地': 'dì', '了': 'le', '吗': 'ma', '么': 'me', '呢': 'ne', '只': 'zhǐ',
    '数': 'shù', '便': 'biàn', '还': 'hái', '和': 'hé', '都': 'dōu', '乐': 'lè', '中': 'zhōng',
    '少': 'shǎo', '好': 'hǎo', '种': 'zhǒng', '分': 'fēn', '当': 'dāng', '相': 'xiāng', '看': 'kàn',
    '教': 'jiāo', '差': 'chà', '干': 'gàn', '空': 'kōng', '要': 'yào', '正': 'zhèng', '量': 'liàng',
    '调': 'diào', '处': 'chù', '传': 'chuán', '难': 'nán', '假': 'jià', '解': 'jiě', '参': 'cān',
    '朝': 'cháo', '降': 'jiàng', '弹': 'dàn', '没': 'méi', '给': 'gěi', '发': 'fā', '什': 'shén',
    '的': 'de', '一': 'yī', '不': 'bù', '会': 'huì', '东': 'dōng', '西': 'xī', '乐': 'lè', '大': 'dà',
    '睡': 'shuì', '应': 'yīng', '更': 'gèng', '思': 'sī', '哪': 'nǎ', '那': 'nà', '还': 'hái',
    '与': 'yǔ', '似': 'sì', '供': 'gōng', '号': 'hào', '名': 'míng', '奇': 'qí', '期': 'qī',
    '藏': 'cáng', '血': 'xuè', '薄': 'báo', '省': 'shěng', '冲': 'chōng', '转': 'zhuǎn', '背': 'bèi',
    '尽': 'jìn', '曾': 'céng', '仔': 'zǐ', '铺': 'pù', '答': 'dá', '系': 'xì', '片': 'piàn', '兴': 'xìng',
}


def single_forms(d):
    return [f for f in d['forms'] if f['m']]


# ---------- finalise characters ----------
out_chars = []
for c in order:
    d = chars[c]
    clean_forms = [f for f in d['forms'] if f['m']]
    marks_for = {f['n']: f['p'] for f in d['forms']}

    scores = defaultdict(float, d['weights'])
    for f in single_forms(d):
        rank = char_rank[c]
        scores[f['n']] += (0.3 if all(REGISTER.match(m.strip()) for m in f['m']) else 1.0) / rank
    if d['mm'] and d['mm'][0] in scores:
        scores[d['mm'][0]] *= 1.5
    primary = None
    if c in OVERRIDES:
        primary = marks_to_numeric(OVERRIDES[c])
    elif scores:
        primary = max(scores.items(), key=lambda kv: kv[1])[0]
    elif d['mm']:
        primary = d['mm'][0]
    elif d['forms']:
        primary = d['forms'][0]['n']
    clean_forms = single_forms(d)

    readings = []
    ranked = sorted(d['weights'].items(), key=lambda kv: -kv[1])
    for r in [primary] + [r for r, _ in ranked] + [f['n'] for f in clean_forms] + d['mm'] + [f['n'] for f in d['forms']]:
        if r and r not in readings:
            readings.append(r)

    g = []
    for f in clean_forms:
        for x in glosses(f['m']):
            if x.lstrip('~^') not in [y.lstrip('~^') for y in g]:
                g.append(x)
    have = {y.lstrip('~^') for y in g}
    for x in d['def']:
        bare = x.lstrip('~^')
        if bare not in have:
            # makemeahanzi definitions are loose comma lists: secondary when HSK meanings exist
            g.append(('~' + bare) if clean_forms else x)
            have.add(bare)

    marks = marks_for.get(primary) or (numeric_to_marks(primary) if primary else '')
    out_chars.append({'h': c, 'p': marks, 'r': readings, 'g': g, 'f': char_rank[c]})

# single-character words: HSK gives every reading the character's frequency;
# demote readings other than the main one (那 nuó "beautiful", 啊 á "what")
primary_of = {c['h']: marks_to_numeric(c['p']) if c['p'] else None for c in out_chars}
for w in words:
    if len(w['h']) == 1 and primary_of.get(w['h']) and w['n'] != primary_of[w['h']] and w['f'] < 25000:
        w['f'] = w['f'] * 10 + 3000

# ---------- simplified <-> traditional character maps ----------
# Inside words the app uses each word's own traditional form; these maps cover
# single characters. Where a simplified character has several traditional forms
# (发 -> 發/髮) the one used most in HSK words wins, else CC-CEDICT's first.
s2t_votes = defaultdict(lambda: defaultdict(float))
for e in json.load(open(HSK, encoding='utf-8')):
    simp, rank = e['simplified'], e['frequency']
    for form in e['forms']:
        trad = form.get('traditional') or simp
        if len(trad) != len(simp):
            continue
        for sc, tc in zip(simp, trad):
            s2t_votes[sc][tc] += 1.0 / rank

cedict_s2t, cedict_t2s = {}, {}
for line in open(CEDICT, encoding='utf-8'):
    if line.startswith('#'):
        continue
    parts = line.split(' ', 2)
    if len(parts) < 2:
        continue
    trad, simp = parts[0], parts[1]
    if len(trad) == 1 and len(simp) == 1 and trad != simp:
        cedict_s2t.setdefault(simp, trad)
        cedict_t2s.setdefault(trad, simp)

s2t, t2s = {}, {}
for c in order:
    votes = {t: v for t, v in s2t_votes.get(c, {}).items() if t in chars}
    best = max(votes.items(), key=lambda kv: kv[1])[0] if votes else cedict_s2t.get(c)
    if best and best != c and best in chars:
        s2t[c] = best
for c in order:
    simp = cedict_t2s.get(c)
    if simp and simp != c and simp in chars:
        t2s[c] = simp
# A character that is its own simplified form must not map away.
for c in list(t2s):
    if c in s2t_votes and c in s2t_votes[c]:
        del t2s[c]

json.dump({'s2t': s2t, 't2s': t2s, 'c': out_chars, 'w': words}, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print('chars', len(out_chars), 'without pinyin', sum(1 for c in out_chars if not c['p']),
      'words', len(words), '(cedict extra', extra, ')', 's2t', len(s2t), 't2s', len(t2s))
