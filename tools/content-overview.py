#!/usr/bin/env python3
"""Собирает OVERVIEW.md для чтения из JSON контента. Использование: python3 tools/content-overview.py content/a1.0"""
import json, os, sys
root = sys.argv[1]
def load(n):
    with open(os.path.join(root, n + '.json'), encoding='utf-8') as f:
        return json.load(f)
words = load('words'); fillers = load('fillers'); patterns = load('patterns'); engines = load('engines')
cells = load('cells'); blocks = load('blocks'); modules = load('modules'); situations = load('situations')
chapters = load('chapters'); numbers = load('numbers'); facts = load('facts')
W = {w['id']: w for w in words}; F = {f['id']: f for f in fillers}; P = {p['id']: p for p in patterns}
E = {e['id']: e for e in engines}; S = {s['id']: s for s in situations}; CH = {c['id']: c for c in chapters}
formulas = {f['id']: f for b in blocks for f in b['formulas']}
def fde(fid):
    return W[fid]['de'] if fid in W else F[fid]['de'] if fid in F else fid
out = []
o = out.append
o('# Контент A1.0')
o('')
items = [w for w in words if w.get('item', True)]
o(f'Обзор машинного контента слоя A1.0, собран из JSON скриптом. Паттернов {len(patterns)}, вариантов {sum(len(p["variants"]) for p in patterns)}, фиксированных предложений {sum(len(p.get("fixed", [])) for p in patterns)}, клеток {sum(len(c["templates"]) for c in cells)}, формул {len(formulas)}, учебных слов {len(items)}, заполнителей {len(fillers)}, сцен {len(situations)}, глав {len(chapters)}. Значок ★ отмечает сюжетные подсказки.')
o('')
def cue_str(cues):
    return ' · '.join(('★ ' if c['voice'] == 'story' else '') + c['text'] for c in cues)
for m in sorted(modules, key=lambda x: x['order']):
    ch = CH.get(m.get('chapterId'))
    o(f'## {m["id"]} · Занятие {m["session"]} · Глава {ch["session"] if ch else ""} «{m["titleRu"]}»')
    o('')
    if ch:
        o(f'> Занятие: {ch["openingRu"]}')
        o('')
        o(f'**Цель главы.** {ch["goalRu"]}')
        o('')
        o(f'**В конце умеет.** {ch["canDoRu"]}')
        o('')
        if ch.get('receptiveWords'):
            o('**На понимание.** ' + ', '.join(f'{r["de"]} ({r["ru"]})' for r in ch['receptiveWords']))
            o('')
    if m.get('noteRu'):
        o(m['noteRu'] + '.')
        o('')
    if m.get('sweepRu'):
        o('**Сплошной веер.** ' + m['sweepRu'] + '.')
        o('')
    if m.get('gateRu'):
        o('**Ворота.** ' + m['gateRu'] + '.')
        o('')
    for pid in m.get('patternIds', []):
        p = P[pid]
        o(f'### {p["id"]} · {p["functionRu"]}')
        o('')
        if p['variants']:
            o('| Вариант | Шаблон | Заполнители | Подсказки |')
            o('|---|---|---|---|')
            for v in p['variants']:
                fl = v.get('fillerIds', []) or [x['id'] for x in v.get('fillers', [])]
                sample = ', '.join(fde(x) for x in fl[:5]) + (' …' if len(fl) > 5 else '')
                o(f'| {v["id"]} | {v["templateDe"]} | {len(fl)}: {sample} | {cue_str(v["cues"])} |')
            o('')
        if p.get('fixed'):
            o('Фиксированные предложения:')
            o('')
            for f in p['fixed']:
                o(f'- {f["de"]} — {cue_str(f["cues"])}')
            o('')
        o('Примеры: ' + ' · '.join(f'{e["de"]} ({e["ru"]})' for e in p.get('examples', [])))
        o('')
        if p.get('alternatives'):
            o('Альтернативы: ' + ' · '.join(f'{a["de"]} [{a["grade"]}: {a["when"]}]' for a in p['alternatives']))
            o('')
        if p.get('notes'):
            o(p['notes'])
            o('')
    for eid in m.get('engineIds', []):
        e = E[eid]
        if e.get('implicit'):
            o(f'### {e["id"]} · {e["nameRu"]}')
            o('')
            o(e['descriptionRu'])
            o('')
            continue
        o(f'### {e["id"]} · {e["nameRu"]}')
        o('')
        o(e['descriptionRu'])
        o('')
        o('| Клетка | Шаблон | Подсказка |')
        o('|---|---|---|')
        for cell in cells:
            if cell['engine'] != eid: continue
            for t in cell['templates']:
                o(f'| {cell["engine"]} × {cell["pattern"]} | {t["de"]} | {t["cueRu"]} |')
        o('')
    if m.get('formulaIds'):
        o('### Формулы')
        o('')
        o('| Формула | Значение | Подсказки |')
        o('|---|---|---|')
        for fid in m['formulaIds']:
            f = formulas[fid]
            o(f'| {f["de"]} | {f["ru"]} | {cue_str(f["cues"])} |')
        o('')
    if m.get('coreWordIds'):
        o('### Слова ядра')
        o('')
        o('| Слово | Значение | Формы |')
        o('|---|---|---|')
        for wid in m['coreWordIds']:
            w = W[wid]
            forms = ''
            if w['pos'] == 'verb':
                forms = ', '.join(f'{k} {v}' for k, v in (w.get('forms') or {}).items())
            elif w['pos'] == 'noun':
                forms = ', '.join(v for v in (w.get('forms') or {}).values() if v)
            elif w['pos'] == 'adj' and w.get('ruState'):
                forms = 'я ' + w['ruState']
            o(f'| {w["de"]} | {w["ru"]} | {forms} |')
        o('')
    if m.get('passiveWordIds'):
        o('На понимание: ' + ', '.join(f'{W[x]["de"]} ({W[x]["ru"]})' for x in m['passiveWordIds']))
        o('')
    if m.get('fillerIds'):
        o('Заполнители: ' + ', '.join(f'{F[x]["de"]} ({F[x]["ru"]})' for x in m['fillerIds']))
        o('')
    if m.get('numbers'):
        o('Числа: ' + ', '.join(f'{n["n"]} {n["de"]}' for n in numbers['items']))
        o('')
    sids = ([m['situationId']] if m.get('situationId') else []) + m.get('situationIds', [])
    for sid in sids:
        s = S[sid]
        o(f'### Сцена {s["id"]} · {s["titleRu"]}')
        o('')
        roles = ', '.join(s['roles']['tutor'])
        o(f'Место: {s["placeRu"]}. Тьютор: {roles}. {s.get("notesRu", "")}')
        o('')
        if s.get('lines'):
            o('```')
            for l in s['lines']:
                if 'expectedDe' in l:
                    o(f'Мила:   ({l["cueRu"]})')
                    o(f'        {l["expectedDe"]}')
                else:
                    note = f'   [{l["noteRu"]}]' if l.get('noteRu') else ''
                    o(f'{l["speaker"]}: {l["de"]}{note}')
            o('```')
            o('')
        if s.get('freeRunRu'):
            o('Свободный прогон: ' + s['freeRunRu'])
            o('')
    if m.get('exitFromRole'):
        x = facts['exitFromRole']
        o('### Выход из роли')
        o('')
        o(x['cueRu'] + '.')
        o('')
        o('```')
        for t in x['templateDe']: o(t)
        o('```')
        o('')
o('## Служебные слова')
o('')
o(', '.join(f'{w["de"]} ({w["ru"]})' for w in words if not w.get('item', True)))
o('')
with open(os.path.join(root, 'OVERVIEW.md'), 'w', encoding='utf-8') as f:
    f.write('\n'.join(out))
print('OVERVIEW.md записан:', len(out), 'строк')
