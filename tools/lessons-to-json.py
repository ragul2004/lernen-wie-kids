#!/usr/bin/env python3
"""Превращает уроки lessons/<слой>/urok-NN.md в карточки lessons/<слой>/json/urok-NN.json.
Использование: python3 tools/lessons-to-json.py lessons/A1.0
Проверяет, что у каждого задания есть подсказка и ответ, и что карусели сходятся по числу."""
import json, os, re, sys

root = sys.argv[1]
outdir = os.path.join(root, 'json')
os.makedirs(outdir, exist_ok=True)
errors = []

MODE_KEYS = [('Пропуск', 'cloze'), ('Целиком', 'task'), ('Карусель', 'carousel'), ('Трансформац', 'transform'),
             ('С опорой', 'transform'), ('Смешанно', 'task'), ('Без опоры', 'task'), ('Обратно', 'reverse'),
             ('Задания по ситуации', 'task'), ('Ситуации', 'task'), ('Разогрев', 'task'), ('Скрещивание', 'task'),
             ('Паттерны', 'task'), ('Вопросы и отрицания', 'task'), ('Формулы', 'task'),
             ('Слова', 'word_task'), ('Показ', 'show')]
TASK_TYPES = ('cloze', 'task', 'carousel', 'transform', 'word_task')

def mode_from(text, current):
    for k, m in MODE_KEYS:
        if k in text:
            return m
    return current

def split_items(s):
    return [x.strip() for x in s.strip().split(' · ') if x.strip()]

def after_colon(line):
    i = line.find(':')
    return line[i + 1:].strip() if i >= 0 else ''

def parse_table(rows):
    cells = [[c.strip() for c in r.strip().strip('|').split('|')] for r in rows]
    header = cells[0]
    body = [r for r in cells[1:] if not all(set(c) <= set('-: ') for c in r)]
    return header, body

def parse_scene_line(line):
    i = line.find(':')
    if i < 0:
        return None
    speaker = line[:i].strip()
    rest = line[i + 1:].strip()
    if speaker.startswith('Учени'):
        cue, answer = '', rest
        if rest.startswith('('):
            j = rest.find(')')
            cue = rest[1:j].strip()
            answer = rest[j + 1:].strip()
        return {'type': 'scene_turn', 'prompt': cue, 'answer': answer}
    return {'type': 'scene_line', 'speaker': speaker, 'text': rest}

def convert(path):
    lines = open(path, encoding='utf-8').read().split('\n')
    lesson = {'lesson': None, 'title': '', 'intro': '', 'blocks': []}
    block = None
    mode = 'task'
    pending = None       # (mode, prompts) для карусели
    scene_block = False
    summary_block = False
    i = 0
    def add(card):
        nonlocal block
        if block is None:
            block = {'title': 'Вступление', 'cards': []}
            lesson['blocks'].append(block)
        block['cards'].append(card)
    def answer_card(kind, r):
        return {'type': kind, 'prompt': r[1], 'answer': r[2]}
    while i < len(lines):
        line = lines[i]
        s = line.strip()
        if line.startswith('# '):
            m = re.match(r'# Урок (\d+)\. (.*)', line)
            lesson['lesson'] = int(m.group(1)); lesson['title'] = m.group(2).strip()
            i += 1; continue
        if line.startswith('## '):
            title = line[3:].strip()
            block = {'title': title, 'cards': []}
            lesson['blocks'].append(block)
            mode = mode_from(title, 'task')
            scene_block = ('Сцена' in title) or ('Диалог' in title)
            summary_block = 'Итог' in title
            pending = None
            i += 1; continue
        if line.startswith('### '):
            text = line[4:].strip()
            add({'type': 'heading', 'text': text})
            mode = mode_from(text, mode)
            pending = None
            i += 1; continue
        if line.startswith('```'):
            j = i + 1; body = []
            while j < len(lines) and not lines[j].startswith('```'):
                body.append(lines[j]); j += 1
            text = '\n'.join(x.rstrip() for x in body).strip()
            if scene_block:
                for b in body:
                    if not b.strip(): continue
                    card = parse_scene_line(b)
                    if card: add(card)
                    else: add({'type': 'note', 'text': b.strip()})
            else:
                add({'type': 'summary' if summary_block else 'note', 'text': text})
            i = j + 1; continue
        if line.startswith('|'):
            rows = []
            while i < len(lines) and lines[i].startswith('|'):
                rows.append(lines[i]); i += 1
            header, body = parse_table(rows)
            h = [c.lower() for c in header]
            if h[:3] == ['слово', 'значение', 'пример']:
                for r in body: add({'type': 'word', 'de': r[0], 'ru': r[1], 'example': r[2]})
            elif h[:2] == ['формула', 'когда']:
                for r in body: add({'type': 'formula', 'de': r[0], 'when': r[1]})
            elif h[:2] == ['немецкий', 'смысл']:
                for r in body: add({'type': 'show', 'de': r[0], 'ru': r[1]})
            elif h[:2] == ['было', 'стало']:
                for r in body: add({'type': 'show_pair', 'from': r[0], 'to': r[1]})
            elif len(h) == 2 and h[1] == 'немецкий':
                for r in body: add({'type': 'show', 'de': r[1], 'ru': r[0]})
            elif h[:3] == ['№', 'подсказка', 'ответ']:
                for r in body: add(answer_card(mode if mode in TASK_TYPES else 'task', r))
            elif h[:3] == ['№', 'предложение и инструкция', 'ответ']:
                for r in body: add(answer_card('transform', r))
            elif h[0] == '№' and h[1].startswith('вопрос') and h[2] == 'ответ':
                for r in body: add(answer_card('answer_question', r))
            elif h[:3] == ['№', 'по-русски', 'по-немецки']:
                for r in body: add({'type': 'word_task', 'prompt': r[1], 'answer': r[2]})
            elif h[0] == 'инфинитив':
                add({'type': 'note', 'tutorOnly': True, 'text': 'Формы: ' + '; '.join(r[0] + ': ' + ', '.join(f'{header[k]} {r[k]}' for k in range(1, len(r))) for r in body)})
            elif h[:2] == ['результат', 'что дальше']:
                add({'type': 'note', 'text': '\n'.join(f'{r[0]}: {r[1]}' for r in body)})
            else:
                errors.append(f'{os.path.basename(path)}: неизвестная таблица {header}')
            continue
        if s == '':
            i += 1; continue
        # paragraph lines
        if s.startswith('Карусель'):
            mode = 'carousel'
            items = split_items(after_colon(s))
            if items and items[-1].endswith('.') and not items[-1].endswith('...'):
                items[-1] = items[-1][:-1]
            pending = ('carousel', items) if items else None
            i += 1; continue
        if s.startswith('Ответы'):
            answers = split_items(after_colon(s))
            if not pending:
                errors.append(f'{os.path.basename(path)}: «Ответы» без подсказок: {s[:50]}')
            else:
                kind, prompts = pending
                if len(prompts) != len(answers):
                    errors.append(f'{os.path.basename(path)}: карусель {len(prompts)} подсказок и {len(answers)} ответов: {s[:50]}')
                for pr, an in zip(prompts, answers):
                    add({'type': kind, 'prompt': pr, 'answer': an})
                pending = None
            i += 1; continue
        if s.startswith('Обратно') or (mode == 'reverse' and ' · ' in s):
            items = split_items(after_colon(s)) if ':' in s else []
            for it in items: add({'type': 'reverse', 'de': it})
            if not items: mode = 'reverse'
            i += 1; continue
        if s.startswith('Эхо'):
            add({'type': 'echo', 'text': s}); i += 1; continue
        if ' · ' in s and not s.startswith('Ответы') and i + 2 < len(lines) and lines[i + 2].strip().startswith('Ответы'):
            pending = ('word_task' if mode == 'word_task' else 'carousel', split_items(s))
            i += 1; continue
        if s.startswith('Пропуск'): mode = 'cloze'
        elif s.startswith('Целиком'): mode = 'task'
        elif s.startswith('Трансформац'): mode = 'transform'
        elif s.startswith('Задания по ситуации'): mode = 'task'
        elif s.startswith('Ситуации'): mode = 'task'
        elif s.startswith('Без опоры'): mode = 'task'
        elif s.startswith('С опорой'): mode = 'transform'
        elif s.startswith('Показ'): mode = 'show'
        if s.endswith(':') and len(s) < 60:
            add({'type': 'label', 'text': s.rstrip(':')})
        else:
            add({'type': 'note', 'text': s})
        i += 1
    return lesson

total = 0
for name in sorted(os.listdir(root)):
    if not re.match(r'urok-\d+\.md$', name): continue
    lesson = convert(os.path.join(root, name))
    n_ans = 0
    for b in lesson['blocks']:
        for c in b['cards']:
            if 'answer' in c:
                n_ans += 1
                if not c['answer'].strip(): errors.append(f'{name}: пустой ответ у «{c.get("prompt","")}»')
                if c['type'] != 'scene_turn' and not c.get('prompt', '').strip(): errors.append(f'{name}: пустая подсказка у «{c["answer"][:40]}»')
    total += n_ans
    out = os.path.join(outdir, name.replace('.md', '.json'))
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(lesson, f, ensure_ascii=False, indent=1)
    print(f'{name}: блоков {len(lesson["blocks"])}, карточек {sum(len(b["cards"]) for b in lesson["blocks"])}, с ответом {n_ans}')
print(f'всего заданий с ответом: {total}; ошибок: {len(errors)}')
for e in errors: print('ОШИБКА', e)
sys.exit(1 if errors else 0)
