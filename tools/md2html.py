#!/usr/bin/env python3
import re, sys, html

md_path, css_path, out_path = sys.argv[1:4]
eyebrow = sys.argv[4] if len(sys.argv) > 4 else 'Deutsch für russischsprachige Erwachsene · Lehrplan · Entwurf 0.1'
md = open(md_path, encoding='utf-8').read().split('\n')
css = open(css_path, encoding='utf-8').read()

def esc(s):
    return html.escape(s, quote=False)

def slot(s):
    s = re.sub(r'\+ (Inf\.|Akk\.|Adj\.|Partizip|Nomen|Verb(?:-t)?)', r'<span class="slot">+ \1</span>', s)
    s = re.sub(r'\[(Zeit|Ort|Tag|Monat)\]', r'<span class="slot">[\1]</span>', s)
    s = s.replace('…', '<span class="slot">…</span>')
    return s

def inline(s):
    s = esc(s)
    s = s.replace('&lt;br&gt;', '<br>')
    s = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s)
    s = re.sub(r'`([^`]+)`', lambda m: '<code>' + slot(m.group(1)) + '</code>', s)
    return s

def chip(cell):
    c = cell.strip()
    m = re.match(r'^(П|Б|Д)(\d+)$', c)
    if m:
        cls = {'П': 'p', 'Б': 'b', 'Д': 'd'}[m.group(1)]
        return f'<span class="chip chip-{cls}">{c}</span>'
    if re.match(r'^A1\.\d$', c):
        return f'<span class="chip chip-l">{c}</span>'
    return inline(c)

def parse_table(rows):
    cells = [[c.strip() for c in r.strip().strip('|').split('|')] for r in rows]
    header, body = cells[0], cells[2:]
    cls, pat_col = 'tbl', None
    if 'Паттерн' in header:
        cls += ' patterns'; pat_col = header.index('Паттерн')
    elif 'Движок' in header:
        cls += ' engines'
    elif header[0] == 'Слой':
        cls += ' summary'
    elif 'Формулы' in header or 'Содержание' in header:
        cls += ' blocks'
    elif header[0] == 'Намерение':
        cls += ' growth'
    else:
        cls += ' plain'
    h = '<thead><tr>' + ''.join(f'<th>{esc(c)}</th>' for c in header) + '</tr></thead>'
    b = []
    for r in body:
        tds = []
        for j, c in enumerate(r):
            if j == 0 and cls != 'tbl plain' and 'growth' not in cls:
                tds.append(f'<td class="num">{chip(c)}</td>')
            elif j == pat_col:
                tds.append(f'<td class="pat">{slot(inline(c))}</td>')
            else:
                tds.append(f'<td>{inline(c)}</td>')
        b.append('<tr>' + ''.join(tds) + '</tr>')
    return f'<div class="table-wrap"><table class="{cls}">{h}<tbody>{"".join(b)}</tbody></table></div>'

intro, out = [], []
cur = intro
title, subtitle_done = '', False
sections = []
parts = []
in_section = False
current_h3 = ''
sec_count = 0
para = []

def flush():
    global para
    if para:
        text = ' '.join(para)
        cls = ' class="vocab"' if current_h3.startswith('Словарь') else ''
        cur.append(f'<p{cls}>{inline(text)}</p>')
        para = []

i = 0
while i < len(md):
    line = md[i]
    if line.startswith('```'):
        flush()
        j, block = i + 1, []
        while j < len(md) and not md[j].startswith('```'):
            block.append(md[j]); j += 1
        cur.append('<pre class="demo">' + esc('\n'.join(block)) + '</pre>')
        i = j + 1; continue
    if line.startswith('|'):
        flush()
        rows = []
        while i < len(md) and md[i].startswith('|'):
            rows.append(md[i]); i += 1
        cur.append(parse_table(rows)); continue
    if line.startswith('# '):
        flush()
        text = line[2:].strip()
        if not title:
            title = text; i += 1; continue
        if in_section:
            out.append('</section>'); in_section = False
        cur = out; current_h3 = ''
        parts.append((f'p{len(parts)+1}', text))
        out.append(f'<h1 class="part" id="p{len(parts)}">{esc(text)}</h1>')
        i += 1; continue
    if line.startswith('## '):
        flush()
        text = line[3:].strip()
        sec_count += 1; sid = f's{sec_count}'
        if in_section:
            out.append('</section>')
        cur = out; in_section = True; current_h3 = ''
        m = re.match(r'^(A1\.\d)\s+—\s+(.*)$', text)
        if m:
            out.append(f'<section class="layer" id="{sid}"><header class="layer-head"><span class="layer-code">{m.group(1)}</span><h2>{esc(m.group(2))}</h2></header>')
            sections.append((sid, m.group(1), True))
        else:
            out.append(f'<section id="{sid}"><h2>{esc(text)}</h2>')
            sections.append((sid, text, False))
        i += 1; continue
    if line.startswith('### '):
        flush(); current_h3 = line[4:].strip()
        cur.append(f'<h3>{esc(current_h3)}</h3>'); i += 1; continue
    if line.startswith('> '):
        flush(); text = line[2:].strip()
        if ' · ' in text:
            items = ''
            for it in text.split(' · '):
                if ': ' in it:
                    k, v = it.split(': ', 1)
                    items += f'<div class="stat"><span class="stat-k">{esc(k)}</span><span class="stat-v">{esc(v)}</span></div>'
                else:
                    items += f'<div class="stat"><span class="stat-v">{esc(it)}</span></div>'
            cur.append(f'<div class="stats">{items}</div>')
        else:
            cur.append(f'<aside class="note">{inline(text)}</aside>')
        i += 1; continue
    if re.match(r'^- ', line):
        flush(); items = []
        while i < len(md) and re.match(r'^- ', md[i]):
            items.append(md[i][2:]); i += 1
        cur.append('<ul>' + ''.join(f'<li>{inline(x)}</li>' for x in items) + '</ul>'); continue
    if re.match(r'^\d+\. ', line):
        flush(); items = []
        while i < len(md) and re.match(r'^\d+\. ', md[i]):
            items.append(re.sub(r'^\d+\. ', '', md[i])); i += 1
        cur.append('<ol>' + ''.join(f'<li>{inline(x)}</li>' for x in items) + '</ol>'); continue
    if line.strip() == '':
        flush(); i += 1; continue
    para.append(line.strip()); i += 1
flush()
if in_section:
    out.append('</section>')

if parts:
    nav = ''.join(f'<a href="#{pid}" class="nav-part">{esc(label)}</a>' for pid, label in parts)
else:
    nav = ''.join(
        f'<a href="#{sid}" class="{"nav-layer" if is_layer else "nav-plain"}">{esc(label)}</a>'
        for sid, label, is_layer in sections
    )

page = f'''<title>{esc(title)}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Golos+Text:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&family=Literata:wght@600;700&display=swap">
<style>
{css}
</style>
<nav class="nav"><div class="nav-inner"><span class="nav-brand">{esc(title)}</span>{nav}</div></nav>
<main class="page">
<header class="masthead">
<p class="eyebrow">{esc(eyebrow)}</p>
<h1>{esc(title)}</h1>
{''.join(intro)}
</header>
{''.join(out)}
</main>
'''
open(out_path, 'w', encoding='utf-8').write(page)
print('ok', len(page), 'bytes', len(sections), 'sections')
