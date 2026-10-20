#!/usr/bin/env python3
"""Проверка контента слоя: уникальность id, ссылки, подсказки, пассив, последовательность введения слов.
Использование: python3 tools/validate-content.py content/a1.0
Код возврата 1, если есть ошибки."""
import json, os, re, sys

root = sys.argv[1]
def load(name):
    with open(os.path.join(root, name + '.json'), encoding='utf-8') as f:
        return json.load(f)

words = load('words'); fillers = load('fillers'); patterns = load('patterns'); engines = load('engines')
cells = load('cells'); blocks = load('blocks'); modules = load('modules'); situations = load('situations')
chapters = load('chapters'); numbers = load('numbers')
errors, warnings = [], []

W = {w['id']: w for w in words}; F = {f['id']: f for f in fillers}; P = {p['id']: p for p in patterns}
E = {e['id']: e for e in engines}; M = {m['id']: m for m in modules}; S = {s['id']: s for s in situations}
CH = {c['id']: c for c in chapters}
formulas = {f['id']: f for b in blocks for f in b['formulas']}

for name, coll in [('words', words), ('fillers', fillers), ('patterns', patterns), ('engines', engines),
                   ('modules', modules), ('situations', situations), ('chapters', chapters)]:
    ids = [x['id'] for x in coll]
    dups = {i for i in ids if ids.count(i) > 1}
    if dups:
        errors.append(f'{name}: повторяющиеся id {sorted(dups)}')

ids_all = set(W) | set(F) | set(P) | set(E) | set(M) | set(S) | set(CH) | set(formulas)
order = {m['id']: m['order'] for m in modules}
def mod_order(mid):
    return order.get(mid, 99)

PH = re.compile(r'\{[A-Za-z]+\}')
PUNCT = re.compile(r'[„“"«»,.!?:;()…\-–—]')
def toks(s):
    return [t for t in PUNCT.sub(' ', PH.sub(' ', s or '')).lower().split() if t]

def word_tokens(w):
    out = set(toks(w['de']))
    if w['pos'] == 'verb':
        out.update(toks(' '.join(v for v in (w.get('forms') or {}).values() if v)))
    if w['pos'] == 'noun':
        out.update(toks(w.get('lemma', '')))
        if w.get('plural'):
            out.update(toks(w['plural']))
        for v in (w.get('forms') or {}).values():
            if v:
                out.update(toks(v))
    return out

tok_module = {}
def allow(tok, mo):
    if tok not in tok_module or mo < tok_module[tok]:
        tok_module[tok] = mo
for w in words:
    for t in word_tokens(w):
        allow(t, mod_order(w['module']))
for f in fillers:
    for t in toks(f['de']):
        allow(t, mod_order(f['module']))
for f in formulas.values():
    for t in toks(f['de']):
        allow(t, mod_order(f['module']))
for n in numbers['items']:
    allow(n['de'].lower(), mod_order(numbers['module']))
    if n.get('beforeNoun'):
        allow(n['beforeNoun'], mod_order(numbers['module']))

def check_text(text, mo, where, extra=()):
    for t in toks(text):
        if t in extra:
            continue
        if t not in tok_module:
            errors.append(f'{where}: слова «{t}» нет в контенте: {text}')
        elif tok_module[t] > mo:
            errors.append(f'{where}: слово «{t}» вводится в модуле с порядком {tok_module[t]}, а используется при {mo}: {text}')

def ref(x, kind, where):
    if x == 'numbers':
        return
    if x not in ids_all:
        errors.append(f'{where}: ссылка на несуществующий {kind} {x}')

for m in modules:
    for pid in m.get('patternIds', []): ref(pid, 'паттерн', m['id'])
    for eid in m.get('engineIds', []): ref(eid, 'движок', m['id'])
    for fid in m.get('formulaIds', []): ref(fid, 'формулу', m['id'])
    for wid in m.get('coreWordIds', []) + m.get('passiveWordIds', []): ref(wid, 'слово', m['id'])
    for fid in m.get('fillerIds', []): ref(fid, 'заполнитель', m['id'])
    if m.get('situationId'): ref(m['situationId'], 'сцену', m['id'])
    for sid in m.get('situationIds', []): ref(sid, 'сцену', m['id'])
    if m.get('chapterId'): ref(m['chapterId'], 'главу', m['id'])
    for pre in m.get('prerequisites', []): ref(pre, 'модуль', m['id'])
    for wid in m.get('coreWordIds', []) + m.get('passiveWordIds', []):
        if wid in W and W[wid]['module'] != m['id']:
            errors.append(f'{m["id"]}: слово {wid} числится в модуле {W[wid]["module"]}')
    for fid in m.get('fillerIds', []):
        if fid in F and F[fid]['module'] != m['id']:
            errors.append(f'{m["id"]}: заполнитель {fid} числится в модуле {F[fid]["module"]}')
    if m['type'] in ('pattern', 'engine'):
        if not m.get('situationId'): errors.append(f'{m["id"]}: нет сцены')
        if not m.get('chapterId'): errors.append(f'{m["id"]}: нет главы')
        core = len(m.get('coreWordIds', []))
        if core > 14: warnings.append(f'{m["id"]}: слов ядра {core}, порог 8–12')
listed_words = {wid for m in modules for wid in m.get('coreWordIds', []) + m.get('passiveWordIds', [])}
for w in words:
    if w.get('item', True) and w['id'] not in listed_words:
        errors.append(f'{w["id"]}: учебное слово не входит ни в один модуль')
listed_fillers = {fid for m in modules for fid in m.get('fillerIds', [])}
for f in fillers:
    if f['id'] not in listed_fillers:
        errors.append(f'{f["id"]}: заполнитель не входит ни в один модуль')

receptive = {}
for c in chapters:
    ref(c['module'], 'модуль', c['id'])
    if c.get('situationId'): ref(c['situationId'], 'сцену', c['id'])
    for wid in c.get('borrowedWordIds', []): ref(wid, 'слово', c['id'])
    n = len(c['openingRu'].split())
    if n > 120: warnings.append(f'{c["id"]}: открытие длиннее 120 слов ({n})')
    receptive[c['id']] = set()
    for r in c.get('receptiveWords', []):
        receptive[c['id']].update(toks(r['de']))

used = set()
for p in patterns:
    mo = mod_order(p['module'])
    for eid in p.get('engines', []): ref(eid, 'движок', p['id'])
    for v in p['variants']:
        cues = v.get('cues', [])
        if len(cues) < 3: errors.append(f'{v["id"]}: меньше трёх подсказок')
        if not any(c['voice'] == 'story' for c in cues): errors.append(f'{v["id"]}: нет сюжетной подсказки')
        fl = v.get('fillerIds', []) + [x['id'] for x in v.get('fillers', [])]
        if not fl: errors.append(f'{v["id"]}: нет заполнителей')
        for fid in fl: ref(fid, 'заполнитель', v['id'])
        used.update(fl)
        for c in cues:
            if c.get('fillerId'): ref(c['fillerId'], 'заполнитель', v['id'])
        check_text(v['templateDe'], mod_order(v.get('module', p['module'])), v['id'])
    for f in p.get('fixed', []):
        if len(f.get('cues', [])) < 2: warnings.append(f'{f["id"]}: меньше двух подсказок')
        check_text(f['de'], mod_order(f.get('module', p['module'])), f['id'])
    for ex in p.get('examples', []):
        check_text(ex['de'], mo, p['id'] + ' пример')

for cell in cells:
    where = f'клетка {cell["engine"]}×{cell["pattern"]}'
    ref(cell['engine'], 'движок', where); ref(cell['pattern'], 'паттерн', where)
    mo = max(mod_order(E[cell['engine']]['module']) if cell['engine'] in E else 0,
             mod_order(P[cell['pattern']]['module']) if cell['pattern'] in P else 0)
    if cell['engine'] in E and cell['pattern'] not in E[cell['engine']].get('applicablePatterns', []):
        errors.append(f'{where}: паттерн не числится в applicablePatterns движка')
    for t in cell['templates']:
        fl = t.get('fillerIds', []) + [x['id'] for x in t.get('fillers', [])]
        for fid in fl: ref(fid, 'заполнитель', t['id'])
        used.update(fl)
        check_text(t['de'], mo, t['id'])

for s in situations:
    mo = mod_order(s['module']); extra = receptive.get(s.get('chapterId'), set())
    ref(s['module'], 'модуль', s['id'])
    if s.get('chapterId'): ref(s['chapterId'], 'главу', s['id'])
    for i, l in enumerate(s.get('lines', [])):
        if 'expectedDe' in l:
            check_text(l['expectedDe'], mo, f'{s["id"]} реплика {i + 1}', extra)
            for pid in l.get('patternIds', []):
                if pid not in ids_all and pid not in ('Б1', 'Б2'):
                    errors.append(f'{s["id"]}: реплика {i + 1} ссылается на {pid}')

produced = {}
def note_tokens(text, mid):
    produced.setdefault(mid, set()).update(toks(text))
for s in situations:
    for l in s.get('lines', []):
        if 'expectedDe' in l: note_tokens(l['expectedDe'], s['module'])
for p in patterns:
    for ex in p.get('examples', []): note_tokens(ex['de'], p['module'])
    for v in p['variants']: note_tokens(v['templateDe'], p['module'])
    for f in p.get('fixed', []): note_tokens(f['de'], p['module'])
for cell in cells:
    for t in cell['templates']: note_tokens(t['de'], '*')
for f in formulas.values(): note_tokens(f['de'], f['module'])
all_produced = set().union(*produced.values()) if produced else set()
for m in modules:
    for wid in m.get('coreWordIds', []):
        w = W.get(wid)
        if not w or wid in used: continue
        if word_tokens(w) & all_produced: continue
        warnings.append(f'{m["id"]}: слово ядра {wid} ({w["de"]}) нигде не используется')
for w in words:
    if w.get('passive') and w['id'] in used:
        errors.append(f'{w["id"]}: пассивное слово используется как заполнитель')

print(f'ошибок: {len(errors)}, предупреждений: {len(warnings)}')
for e in errors: print('ОШИБКА', e)
for w in warnings: print('внимание', w)
sys.exit(1 if errors else 0)
