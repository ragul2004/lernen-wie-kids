/* Lernen wie Kids · плеер уроков.
   Один экран, без сборки, без библиотек, без сети.
   Задание: HANDOFF.md. Схема карточек: lessons/A1.0/json/README.md. */
(() => {
'use strict';

const INDEX_URL = 'lessons/index.json';
const FACTS_KEY = 'lwk.facts';
const PROGRESS_KEY = 'lwk.progress';

const FACTS = [
  { key: 'имя',         label: 'Имя',                    hint: 'Anna',                       note: 'после «Ich heiße» и «Ich bin»' },
  { key: 'имя фамилия', label: 'Имя и фамилия',          hint: 'Anna Petrova',               note: 'на воротах: «Ich heiße …»' },
  { key: 'город',       label: 'Город, где живёт',       hint: 'Berlin',                     note: 'после «Ich wohne in»' },
  { key: 'страна',      label: 'Страна, откуда приехала', hint: 'Russland',                  note: 'после «Ich komme aus»' },
  { key: 'откуда',      label: 'Город, откуда приехала', hint: 'Moskau',                     note: 'после «aus»' },
  { key: 'языки',       label: 'Языки',                  hint: 'Russisch und Englisch',      note: 'после «Ich spreche»' },
  { key: 'семья',       label: 'Семья',                  hint: 'einen Mann und eine Tochter', note: 'после «Ich habe»' },
  { key: 'профессия',   label: 'Профессия',              hint: 'Entwicklerin',               note: 'с урока 10, после «Ich arbeite als»' },
  { key: 'возраст',     label: 'Возраст словом',         hint: 'vierundvierzig',             note: 'с урока 10, перед «Jahre alt»' },
  { key: 'адрес',       label: 'Улица и номер дома',     hint: 'Goethestraße 5',             note: 'с урока 22, после «Ich wohne in der»' },
];

const ANSWER_TYPES = new Set(['cloze', 'task', 'carousel', 'transform', 'word_task', 'answer_question', 'scene_turn']);
const TTS_PROMPT_TYPES = new Set(['cloze', 'transform', 'answer_question']);
const TYPE_LABEL = {
  cloze: 'Пропуск', task: 'Целиком', carousel: 'Карусель', transform: 'Трансформация',
  word_task: 'Слово', answer_question: 'Вопрос', scene_turn: 'Сцена', reverse: 'Обратно',
  word: 'Слово', formula: 'Формула', show: 'Показ', show_pair: 'Было и стало',
  scene_line: 'Сцена', echo: 'Эхо', summary: 'Итог', note: '', label: '', heading: '',
};

const state = { index: null, list: [], lessons: {}, facts: loadFacts(), progress: loadProgress(), screen: 'list', listIndex: 0, digits: '', player: null, error: null };
let digitTimer = null;

/* ---------- утилиты ---------- */

const el = (tag, cls, text) => {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text != null) e.textContent = text;
  return e;
};
const app = () => document.getElementById('app');

function loadFacts() {
  try {
    const raw = localStorage.getItem(FACTS_KEY);
    const o = raw ? JSON.parse(raw) : {};
    return o && typeof o === 'object' ? o : {};
  } catch (e) { return {}; }
}
function saveFacts() {
  try { localStorage.setItem(FACTS_KEY, JSON.stringify(state.facts)); } catch (e) { /* без localStorage факты живут до перезагрузки */ }
}
function factsFilled() { return FACTS.filter(f => (state.facts[f.key] || '').trim()).length; }

/* Прогресс: { "10": { done: "2026-09-17", times: 2, left: 3, reached: 40, of: 153 } } по номеру урока.
   done ставится, когда урок дошёл до конца, или вручную клавишей D в списке; reached это самая дальняя
   карточка незаконченного урока. Хранится в localStorage рядом с фактами. */
function loadProgress() {
  try {
    const raw = localStorage.getItem(PROGRESS_KEY);
    const o = raw ? JSON.parse(raw) : {};
    return o && typeof o === 'object' ? o : {};
  } catch (e) { return {}; }
}
function saveProgress() {
  try { localStorage.setItem(PROGRESS_KEY, JSON.stringify(state.progress)); } catch (e) { /* без localStorage прогресс живёт до перезагрузки */ }
}
function today() {
  const d = new Date();
  return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
}
const shortDate = iso => iso ? iso.slice(8, 10) + '.' + iso.slice(5, 7) : '';
const progressOf = n => state.progress[n] || null;
const isDone = n => !!(progressOf(n) && progressOf(n).done);
const times = n => (n % 10 >= 2 && n % 10 <= 4 && (n % 100 < 12 || n % 100 > 14)) ? n + ' раза' : n + ' раз';

function markDone(p) {
  if (p.counted) return;
  p.counted = true;
  const g = state.progress[p.n] || {};
  g.done = today();
  g.times = (g.times || 0) + 1;
  g.left = p.repeat.size;
  delete g.reached; delete g.of;
  state.progress[p.n] = g;
  saveProgress();
}
function markReached(p, s) {
  if (s.replay) return;
  const g = state.progress[p.n] || {};
  if (g.done) return;
  const idx = offset(p, s.bi) + s.ci + 1;
  if ((g.reached || 0) >= idx) return;
  g.reached = idx;
  g.of = countCards(p.data).total;
  state.progress[p.n] = g;
  saveProgress();
}
function toggleDone(n) {
  const g = state.progress[n] || {};
  if (g.done) { delete g.done; delete g.times; delete g.left; }
  else { g.done = today(); delete g.reached; delete g.of; }
  if (Object.keys(g).length) state.progress[n] = g; else delete state.progress[n];
  saveProgress();
}
function resetProgress() {
  if (!Object.keys(state.progress).length) return;
  if (!confirm('Стереть отметки о пройденных и начатых уроках?')) return;
  state.progress = {};
  saveProgress();
  render();
}
/* Курсор в списке встаёт на первый непройденный урок; после урока n на следующий непройденный за ним. */
function selectNext(after) {
  let i = state.list.findIndex(l => (after == null || l.n > after) && !isDone(l.n));
  if (i < 0 && after != null) i = state.list.findIndex(l => l.n > after);
  if (i >= 0) state.listIndex = i;
}

/* Подстановка фактов: {имя}, {город} … Пустой факт оставляет плейсхолдер как есть. */
function fill(text) {
  if (typeof text !== 'string') return text;
  return text.replace(/\{([^}]+)\}/g, (m, k) => {
    const v = state.facts[k];
    return v && v.trim() ? v.trim() : m;
  });
}

const hasAnswer = card => ANSWER_TYPES.has(card.type);
const isRepeatBlock = title => /^6\.\s*Повтор/.test(title) || title.includes('Разбор');
const keyOf = (bi, ci) => bi + ':' + ci;
const posOf = k => { const [bi, ci] = k.split(':').map(Number); return { bi, ci }; };
const shortBlock = title => title.replace(/,\s*\d+\s*минут$/, '');

function countCards(data) {
  let total = 0, answered = 0;
  for (const b of data.blocks) for (const c of b.cards) { total++; if (hasAnswer(c)) answered++; }
  return { total, answered };
}

/* ---------- загрузка ---------- */

async function fetchJson(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(r.status + ' ' + url);
  return r.json();
}

/* Манифест lessons/index.json: слои и уроки с числом карточек. Сами уроки грузятся при открытии. */
async function loadIndex() {
  state.index = await fetchJson(INDEX_URL);
  state.list = [];
  for (const layer of state.index.layers) for (const l of layer.lessons) state.list.push(Object.assign({ layer: layer.id }, l));
  selectNext(null);
}

function lessonEntry(n) { return state.list.find(l => l.n === n) || null; }

async function loadLesson(n) {
  if (state.lessons[n]) return state.lessons[n];
  const entry = lessonEntry(n);
  if (!entry) return null;
  const data = await fetchJson(entry.file);
  state.lessons[n] = data;
  return data;
}

/* ---------- плеер: состояние и переходы ---------- */

function startLesson(n) {
  if (!lessonEntry(n)) return;
  clearDigits();
  loadLesson(n).then(data => { if (data) openLesson(n, data); }).catch(err => { state.error = err; render(); });
}

function openLesson(n, data) {
  const p = { n, data, step: null, history: [], revealed: false, repeat: new Map(), ever: new Map(), done: false, counted: false };
  state.player = p;
  const first = stepIntoBlock(p, 0, false);
  if (first) { p.step = first; markReached(p, first); } else { p.done = true; markDone(p); }
  state.screen = 'player';
  render();
}

/* Вход в блок nbi. Если есть что повторить, сначала повтор, потом блок.
   Блок «6. Повтор» или «Разбор» повторяет всё, что за урок хоть раз отмечали (ever);
   остальные блоки повторяют текущий список (repeat). Пустой блок пропускается. */
function stepIntoBlock(p, nbi, noReplay) {
  const blocks = p.data.blocks;
  if (nbi >= blocks.length) return null;
  const block = blocks[nbi];
  if (!noReplay) {
    const src = isRepeatBlock(block.title) ? p.ever : p.repeat;
    const queue = Array.from(src.keys());
    if (queue.length) return Object.assign(posOf(queue[0]), { replay: { queue, qi: 0, target: nbi } });
  }
  if (block.cards.length) return { bi: nbi, ci: 0, replay: null };
  return stepIntoBlock(p, nbi + 1, noReplay);
}

const cardOf = (p, s) => p.data.blocks[s.bi].cards[s.ci];

function enterStep(p, ns) {
  p.step = ns;
  p.revealed = false;
  /* На повторе карточка снимается со списка; повторное R вернёт её. */
  if (ns.replay) p.repeat.delete(keyOf(ns.bi, ns.ci));
}

function reveal() {
  const p = state.player;
  if (!p || p.done) return;
  if (hasAnswer(cardOf(p, p.step)) && !p.revealed) { p.revealed = true; render(); }
}

function next() {
  const p = state.player;
  if (!p) return;
  if (p.done) { showList(); return; }
  const s = p.step;
  if (hasAnswer(cardOf(p, s)) && !p.revealed) { p.revealed = true; render(); return; }
  let ns;
  if (s.replay) {
    const r = s.replay;
    if (r.qi + 1 < r.queue.length) ns = Object.assign(posOf(r.queue[r.qi + 1]), { replay: { queue: r.queue, qi: r.qi + 1, target: r.target } });
    else ns = stepIntoBlock(p, r.target, true);
  } else {
    const block = p.data.blocks[s.bi];
    if (s.ci + 1 < block.cards.length) ns = { bi: s.bi, ci: s.ci + 1, replay: null };
    else ns = stepIntoBlock(p, s.bi + 1, false);
  }
  p.history.push(s);
  if (ns) { enterStep(p, ns); markReached(p, ns); } else { p.done = true; p.revealed = false; markDone(p); }
  render();
}

function back() {
  const p = state.player;
  if (!p || !p.history.length) return;
  p.step = p.history.pop();
  p.done = false;
  p.revealed = false;
  render();
}

function toggleRepeat() {
  const p = state.player;
  if (!p || p.done) return;
  const s = p.step;
  if (!hasAnswer(cardOf(p, s))) return;
  const k = keyOf(s.bi, s.ci);
  if (p.repeat.has(k)) p.repeat.delete(k);
  else { p.repeat.set(k, true); if (!p.ever.has(k)) p.ever.set(k, true); }
  render();
}

function exitLesson() {
  if (!state.player) { showList(); return; }
  if (state.player.done || confirm('Вернуться к списку уроков? Список повтора этого урока будет забыт.')) showList();
}

function showList() {
  const p = state.player;
  if (p && p.done) selectNext(p.n);
  state.player = null; state.screen = 'list'; render();
}
function showFacts() { state.screen = 'facts'; render(); }

/* Контекст карточки для шапки: последний heading и последний label до неё. */
function context(p, s) {
  const block = p.data.blocks[s.bi];
  let heading = '', label = '';
  for (let i = 0; i <= s.ci; i++) {
    const c = block.cards[i];
    if (c.type === 'heading') { heading = c.text; label = ''; }
    else if (c.type === 'label') label = c.text;
  }
  return { heading, label };
}
function offset(p, bi) {
  let o = 0;
  for (let i = 0; i < bi; i++) o += p.data.blocks[i].cards.length;
  return o;
}

/* ---------- озвучка (необязательная, клавиша T) ---------- */

function germanText(card, revealed) {
  switch (card.type) {
    case 'word': case 'formula': case 'show': case 'reverse': return card.de;
    case 'show_pair': return card.to;
    case 'scene_line': case 'summary': return card.text;
    default:
      if (!hasAnswer(card)) return null;
      if (revealed) return card.answer;
      return TTS_PROMPT_TYPES.has(card.type) ? card.prompt : null;
  }
}
function speak() {
  const p = state.player;
  if (!p || p.done || !('speechSynthesis' in window)) return;
  const text = germanText(cardOf(p, p.step), p.revealed);
  if (!text) return;
  const u = new SpeechSynthesisUtterance(fill(text).replace(/_{2,}/g, '…'));
  u.lang = 'de-DE';
  u.rate = 0.9;
  const voice = speechSynthesis.getVoices().find(v => v.lang && v.lang.toLowerCase().startsWith('de'));
  if (voice) u.voice = voice;
  speechSynthesis.cancel();
  speechSynthesis.speak(u);
}

/* ---------- отрисовка ---------- */

function render() {
  const root = app();
  root.innerHTML = '';
  if (state.error) { root.append(renderError()); return; }
  if (state.screen === 'list') root.append(renderList());
  else if (state.screen === 'facts') root.append(renderFacts());
  else root.append(...renderPlayer());
}

function renderError() {
  const main = el('main');
  const card = el('div', 'card');
  card.append(el('h2', 'big', 'Уроки не загрузились'));
  card.append(el('div', 'mid muted pre', 'Плеер читает JSON через fetch, поэтому его нужно открывать через статический сервер, а не как файл.\n\ndocker compose up\nили\npython3 -m http.server 8000\n\nи открыть http://localhost:8091 или http://localhost:8000'));
  card.append(el('div', 'small muted', String(state.error)));
  main.append(card);
  return main;
}

function renderList() {
  const main = el('main', 'screen-list');
  const box = el('div', 'list-box');
  box.append(el('h1', 'title', 'Lernen wie Kids'));

  const factsLine = el('div', 'facts-line');
  const n = factsFilled();
  factsLine.append(el('span', 'muted', n ? 'Факты ученицы: ' + FACTS.filter(f => (state.facts[f.key] || '').trim()).map(f => state.facts[f.key].trim()).join(', ') : 'Факты ученицы не заполнены: плейсхолдеры {имя}, {город} и другие останутся в карточках как есть.'));
  const fb = el('button', 'btn', n ? 'F · изменить факты' : 'F · заполнить факты');
  fb.addEventListener('click', showFacts);
  factsLine.append(fb);
  box.append(factsLine);

  const doneCount = state.list.filter(l => isDone(l.n)).length;
  const progressLine = el('div', 'progress-line');
  progressLine.append(el('span', null, doneCount ? 'Пройдено ' + doneCount + ' из ' + state.list.length + ' уроков' : 'Пройденных уроков пока нет'));
  const bar = el('div', 'bar');
  const barFill = el('div', 'bar-fill');
  barFill.style.width = (state.list.length ? Math.round(100 * doneCount / state.list.length) : 0) + '%';
  bar.append(barFill);
  progressLine.append(bar);
  if (Object.keys(state.progress).length) {
    const rb = el('button', 'btn small', 'сбросить прогресс');
    rb.addEventListener('click', resetProgress);
    progressLine.append(rb);
  }
  box.append(progressLine);

  let i = 0;
  for (const layer of state.index.layers) {
    const lt = el('div', 'layer-title');
    const layerDone = layer.lessons.filter(l => isDone(l.n)).length;
    lt.append(el('span', null, layer.id + ' · ' + layer.title), el('span', null, layerDone + ' из ' + layer.lessons.length));
    box.append(lt);
    const ul = el('ul', 'lessons');
    for (const l of layer.lessons) {
      const idx = i++;
      const g = progressOf(l.n);
      const done = !!(g && g.done);
      const started = !done && g && g.reached > 0;
      const li = el('li', 'lesson' + (idx === state.listIndex ? ' selected' : '') + (done ? ' done' : started ? ' started' : ''));
      const mark = el('button', 'lesson-mark', done ? '✓' : '○');
      mark.title = done ? 'снять отметку «пройден»' : 'отметить пройденным';
      mark.addEventListener('click', e => { e.stopPropagation(); toggleDone(l.n); render(); });
      li.append(mark);
      li.append(el('span', 'lesson-num', 'Урок ' + l.n));
      li.append(el('span', 'lesson-title', l.title));
      let status;
      if (done) status = 'пройден ' + shortDate(g.done) + (g.times > 1 ? ' · ' + times(g.times) : '') + (g.left ? ' · в повторе ' + g.left : '');
      else if (started) status = 'начат · ' + g.reached + ' из ' + (g.of || l.cards);
      else status = l.cards + ' карточек, ' + l.answers + ' с ответом';
      const count = el('span', 'lesson-count' + (done || started ? '' : ' muted'), status);
      count.title = l.cards + ' карточек, ' + l.answers + ' с ответом';
      li.append(count);
      li.addEventListener('click', () => startLesson(l.n));
      ul.append(li);
    }
    box.append(ul);
  }
  const sel = state.list[state.listIndex];
  const dHint = sel ? ' · D ' + (isDone(sel.n) ? 'снять отметку' : 'отметить пройденным') : '';
  box.append(el('div', 'small muted', state.digits ? 'Урок ' + state.digits + '… Enter или следующая цифра' : 'Номер урока цифрами · ↑ ↓ и Enter · F факты' + dHint));
  main.append(box);
  setTimeout(() => { const sel = main.querySelector('.lesson.selected'); if (sel && sel.scrollIntoView) sel.scrollIntoView({ block: 'nearest' }); }, 0);
  return main;
}

function renderFacts() {
  const main = el('main', 'screen-facts');
  const box = el('div', 'list-box');
  box.append(el('h1', 'title', 'Факты ученицы'));
  box.append(el('p', 'small muted', 'Подставляются в карточки вместо {имя}, {город} и остальных. Писать по-немецки, так, как это прозвучит внутри предложения. Пустое поле оставляет плейсхолдер как есть. Хранится только в этом браузере.'));
  const form = el('div', 'facts-form');
  FACTS.forEach((f, i) => {
    const row = el('label', 'fact-row');
    const head = el('div', 'fact-head');
    head.append(el('span', 'fact-label', f.label));
    head.append(el('span', 'small muted', '{' + f.key + '} · ' + f.note));
    row.append(head);
    const input = el('input', 'fact-input');
    input.type = 'text';
    input.placeholder = f.hint;
    input.value = state.facts[f.key] || '';
    input.dataset.key = f.key;
    input.autocomplete = 'off';
    input.spellcheck = false;
    input.addEventListener('input', () => { state.facts[f.key] = input.value; saveFacts(); });
    input.addEventListener('keydown', e => {
      if (e.key === 'Enter') {
        e.preventDefault();
        const inputs = form.querySelectorAll('input');
        if (i + 1 < inputs.length) inputs[i + 1].focus(); else showList();
      }
    });
    row.append(input);
    form.append(row);
  });
  box.append(form);
  const actions = el('div', 'facts-actions');
  const done = el('button', 'btn', 'Готово · Esc');
  done.addEventListener('click', showList);
  const clear = el('button', 'btn', 'Очистить');
  clear.addEventListener('click', () => { state.facts = {}; saveFacts(); render(); });
  actions.append(done, clear);
  box.append(actions);
  main.append(box);
  setTimeout(() => { const first = form.querySelector('input'); if (first) first.focus(); }, 0);
  return main;
}

function renderPlayer() {
  const p = state.player;
  const header = el('header');
  const main = el('main');
  const footer = el('footer');

  if (p.done) {
    header.append(el('div', 'crumbs', 'Урок ' + p.n + ' · ' + p.data.title), el('div', 'pos', 'конец'));
    const card = el('div', 'card');
    card.append(el('h2', 'big', 'Урок ' + p.n + ' закончен'));
    const g = progressOf(p.n);
    card.append(el('div', 'small muted', 'В списке уроков отмечен пройденным' + (g && g.times > 1 ? ' · ' + times(g.times) : '')));
    const left = Array.from(p.repeat.keys());
    if (left.length) {
      card.append(el('div', 'mid muted', 'Осталось в повторе: ' + left.length));
      const ul = el('ul', 'left-list');
      left.forEach(k => { const c = cardOf(p, posOf(k)); ul.append(el('li', 'small', fill(c.answer))); });
      card.append(ul);
    } else {
      card.append(el('div', 'mid muted', 'Список повтора пуст'));
    }
    main.append(card);
    footer.append(hint('Enter', 'к списку уроков', showList), hint('←', 'назад', back));
    return [header, main, footer];
  }

  const s = p.step;
  const card = cardOf(p, s);
  const ctx = context(p, s);
  const crumbs = el('div', 'crumbs');
  const parts = ['Урок ' + p.n];
  if (s.replay) parts.push('повтор перед «' + shortBlock(p.data.blocks[s.replay.target].title) + '»');
  else parts.push(shortBlock(p.data.blocks[s.bi].title));
  if (ctx.heading) parts.push(ctx.heading);
  if (ctx.label) parts.push(ctx.label);
  crumbs.textContent = parts.join(' · ');
  crumbs.title = parts.join(' · ');
  const total = countCards(p.data).total;
  const pos = s.replay ? 'повтор ' + (s.replay.qi + 1) + ' из ' + s.replay.queue.length : (offset(p, s.bi) + s.ci + 1) + ' из ' + total;
  header.append(crumbs, el('div', 'pos', pos));

  main.append(renderCard(p, s, card));
  main.addEventListener('click', e => { if (e.target.closest('button')) return; next(); });

  const answerable = hasAnswer(card);
  footer.append(
    hint('Space', 'ответ', reveal, !answerable || p.revealed),
    hint('Enter', 'дальше', next),
    hint('R', p.repeat.has(keyOf(s.bi, s.ci)) ? 'снять повтор' : 'повторить позже', toggleRepeat, !answerable),
    hint('←', 'назад', back, !p.history.length),
    hint('Esc', 'к урокам', exitLesson),
  );
  if ('speechSynthesis' in window) footer.append(hint('T', 'озвучить', speak, !germanText(card, p.revealed)));
  return [header, main, footer];
}

function hint(key, text, action, dim) {
  const b = el('button', 'hint' + (dim ? ' dim' : ''));
  b.append(el('kbd', null, key), document.createTextNode(' ' + text));
  b.addEventListener('click', e => { e.stopPropagation(); action(); });
  return b;
}

function renderCard(p, s, card) {
  const wrap = el('div', 'card card-' + card.type);
  const typeLabel = card.type === 'note' && card.tutorOnly ? 'для тьютора' : (TYPE_LABEL[card.type] || '');
  const labelText = [s.replay ? 'Повтор' : '', typeLabel].filter(Boolean).join(' · ');
  if (labelText) wrap.append(el('div', 'type', labelText));
  if (hasAnswer(card) && p.repeat.has(keyOf(s.bi, s.ci))) wrap.append(el('div', 'mark', 'в повтор'));

  switch (card.type) {
    case 'heading':
      wrap.append(el('h2', 'big', fill(card.text)));
      break;
    case 'label':
      wrap.append(el('div', 'big muted', fill(card.text)));
      break;
    case 'note':
      wrap.append(el('div', (card.tutorOnly ? 'small muted' : 'mid') + ' pre', fill(card.text)));
      break;
    case 'echo':
      wrap.append(el('div', 'mid pre', fill(card.text)));
      break;
    case 'word':
      wrap.append(el('div', 'big de', fill(card.de)));
      wrap.append(el('div', 'mid', fill(card.ru)));
      if (card.example) wrap.append(el('div', 'small muted', fill(card.example)));
      break;
    case 'formula':
      wrap.append(el('div', 'big de', fill(card.de)));
      if (card.when) wrap.append(el('div', 'small muted', fill(card.when)));
      break;
    case 'show':
      wrap.append(el('div', 'big de', fill(card.de)));
      wrap.append(el('div', 'small muted', fill(card.ru)));
      break;
    case 'show_pair':
      wrap.append(el('div', 'big de', fill(card.from)));
      wrap.append(el('div', 'mid muted', '↓'));
      wrap.append(el('div', 'big de accent', fill(card.to)));
      break;
    case 'reverse':
      wrap.append(el('div', 'big de', fill(card.de)));
      wrap.append(el('div', 'small muted', 'скажи смысл по-русски'));
      break;
    case 'scene_line':
      wrap.append(el('div', 'small muted', card.speaker));
      wrap.append(el('div', 'mid de pre', fill(card.text)));
      wrap.append(el('div', 'small muted', 'тьютор читает вслух'));
      break;
    case 'summary':
      wrap.append(el('div', 'mid de pre', fill(card.text)));
      break;
    default: {
      const prompt = fill(card.prompt || '');
      if (prompt) wrap.append(el('div', sizeClass(prompt, 'big') + ' pre', prompt));
      else wrap.append(el('div', 'mid muted', 'без подсказки: ученица говорит сама'));
      if (card.type === 'answer_question') wrap.append(el('div', 'small muted', 'тьютор читает вопрос вслух'));
      if (p.revealed) {
        const answer = fill(card.answer);
        wrap.append(el('div', sizeClass(answer, 'big') + ' de accent pre answer', answer));
      } else wrap.append(el('div', 'hidden-answer', 'ответ скрыт · Space'));
    }
  }
  return wrap;
}

/* Длинные подсказки и ответы уменьшаются: до 90 знаков крупно, до 220 средне, дальше текстом. */
function sizeClass(text, base) {
  const n = text.length;
  return n > 220 ? 'text' : n > 90 ? 'mid' : base;
}

/* ---------- клавиатура ---------- */

document.addEventListener('keydown', e => {
  if (e.metaKey || e.ctrlKey || e.altKey) return;
  const tag = e.target && e.target.tagName;
  const inField = tag === 'INPUT' || tag === 'TEXTAREA';

  if (state.error) return;

  if (state.screen === 'facts') {
    if (e.key === 'Escape') { e.preventDefault(); showList(); }
    return;
  }
  if (inField) return;

  if (state.screen === 'list') {
    const total = state.list.length;
    if (isDigit(e)) { e.preventDefault(); pushDigit(digitOf(e)); return; }
    if (e.key === 'ArrowDown') { e.preventDefault(); clearDigits(); state.listIndex = (state.listIndex + 1) % total; render(); return; }
    if (e.key === 'ArrowUp') { e.preventDefault(); clearDigits(); state.listIndex = (state.listIndex + total - 1) % total; render(); return; }
    if (e.key === 'Enter') { e.preventDefault(); if (state.digits) { const n = Number(state.digits); clearDigits(); if (lessonEntry(n)) startLesson(n); else render(); } else startLesson(state.list[state.listIndex].n); return; }
    if (e.key === 'Escape' || e.key === 'Backspace') { e.preventDefault(); clearDigits(); render(); return; }
    if (isLetter(e, 'KeyF', 'fFаА')) { e.preventDefault(); clearDigits(); showFacts(); return; }
    if (isLetter(e, 'KeyD', 'dDвВ')) { e.preventDefault(); clearDigits(); const sel = state.list[state.listIndex]; if (sel) { toggleDone(sel.n); render(); } return; }
    return;
  }

  /* плеер */
  if (e.repeat) { if ([' ', 'Enter', 'Backspace', 'ArrowLeft', 'ArrowRight'].includes(e.key)) e.preventDefault(); return; }
  if (e.key === ' ' || e.code === 'Space') { e.preventDefault(); reveal(); return; }
  switch (e.key) {
    case 'Enter': case 'ArrowRight': e.preventDefault(); next(); return;
    case 'Backspace': case 'ArrowLeft': e.preventDefault(); back(); return;
    case 'Escape': e.preventDefault(); exitLesson(); return;
  }
  if (isLetter(e, 'KeyR', 'rRкК')) { e.preventDefault(); toggleRepeat(); return; }
  if (isLetter(e, 'KeyT', 'tTеЕ')) { e.preventDefault(); speak(); return; }
});

/* Физическая клавиша по e.code не зависит от раскладки; если code пуст, смотрим на e.key
   в латинице и кириллице (R это к, T это е, F это а). */
function isLetter(e, code, keys) { return e.code ? e.code === code : keys.includes(e.key); }
function isDigit(e) { return e.code ? /^(Digit|Numpad)[0-9]$/.test(e.code) : /^[0-9]$/.test(e.key); }

/* Номер урока набирается цифрами: одна цифра открывает урок 1–9 через паузу или Enter,
   вторая цифра открывает урок 10–99, если нет более длинного номера (101…); третья открывает сразу. */
function pushDigit(d) {
  if (digitTimer) clearTimeout(digitTimer);
  state.digits += d;
  const n = Number(state.digits);
  const hasLonger = state.list.some(l => String(l.n).startsWith(state.digits) && String(l.n).length > state.digits.length);
  if (!hasLonger || state.digits.length >= 3) {
    clearDigits();
    if (lessonEntry(n)) startLesson(n); else render();
    return;
  }
  const idx = state.list.findIndex(l => l.n === n);
  if (idx >= 0) state.listIndex = idx;
  render();
  digitTimer = setTimeout(() => { const m = Number(state.digits); clearDigits(); if (lessonEntry(m)) startLesson(m); else render(); }, 700);
}
function clearDigits() { state.digits = ''; if (digitTimer) { clearTimeout(digitTimer); digitTimer = null; } }
function digitOf(e) { return e.code ? e.code.slice(-1) : e.key; }

/* ---------- старт ---------- */

loadIndex().then(render).catch(err => { state.error = err; render(); });

/* Для проверки из консоли: window.lwk.state */
window.lwk = { state, next, back, reveal, toggleRepeat, startLesson, openLesson, loadLesson, showList, fill, countCards, toggleDone, resetProgress };
})();
