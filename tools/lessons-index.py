#!/usr/bin/env python3
"""Собирает lessons/index.json: слои, уроки, число карточек. Плеер читает его при старте.
Использование: python3 tools/lessons-index.py"""
import json, os, re, glob

LAYERS = {
    'A1.0': 'Минимальный рабочий язык',
    'A1.1': 'Я, моя жизнь, мой день',
    'A1.2': 'Прошлое, планы, места, здоровье, покупки',
    'A1.3': 'Связная речь, мост к A2',
}
ANSWER_TYPES = {'cloze', 'task', 'carousel', 'transform', 'word_task', 'answer_question', 'scene_turn', 'write'}

layers = []
for d in sorted(glob.glob('lessons/*/json')):
    layer = d.split(os.sep)[1]
    lessons = []
    for f in sorted(glob.glob(os.path.join(d, 'urok-*.json'))):
        data = json.load(open(f, encoding='utf-8'))
        cards = [c for b in data['blocks'] for c in b['cards']]
        lessons.append({
            'n': data['lesson'],
            'file': 'lessons/%s/json/%s' % (layer, os.path.basename(f)),
            'title': data['title'],
            'cards': len(cards),
            'answers': sum(1 for c in cards if c['type'] in ANSWER_TYPES),
        })
    lessons.sort(key=lambda x: x['n'])
    layers.append({'id': layer, 'title': LAYERS.get(layer, layer), 'lessons': lessons})

with open('lessons/index.json', 'w', encoding='utf-8') as f:
    json.dump({'layers': layers}, f, ensure_ascii=False, indent=1)
for l in layers:
    print(l['id'], l['title'], 'уроков:', len(l['lessons']), 'карточек:', sum(x['cards'] for x in l['lessons']), 'с ответом:', sum(x['answers'] for x in l['lessons']))
