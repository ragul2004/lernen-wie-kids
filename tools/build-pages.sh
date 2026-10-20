#!/bin/sh
# Собирает две HTML-страницы из markdown: учебный план A1 и спецификацию одной страницей.
# Использование: sh tools/build-pages.sh [папка_вывода]
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${1:-$ROOT/build}"
mkdir -p "$OUT"
python3 "$ROOT/tools/md2html.py" "$ROOT/curriculum/A1.md" "$ROOT/tools/lehrplan.css" "$OUT/lehrplan-a1.html" "Deutsch für russischsprachige Erwachsene · Lehrplan · Entwurf 0.1"
{
  echo "# Спецификация Lernen wie Kids"; echo
  echo "Все документы одной страницей: карта репозитория, обзор, экраны, слова, паттерны и фразы, движок занятия, прогресс и мотивация, данные и правила, дорожная карта, программа MVP по дням, история. Исходники лежат в папке spec проекта, по одному файлу на документ."; echo
  sed '1s/^# Lernen wie Kids$/# Карта репозитория/' "$ROOT/README.md"; echo
  sed '1s/^# Спецификация Lernen wie Kids$/# 00 Обзор/' "$ROOT/spec/00-README.md"; echo
  for f in 01-screens 02-words 03-patterns 04-session-engine 05-progress-motivation 06-data-and-rules 07-roadmap 08-mvp-schedule 09-story; do
    cat "$ROOT/spec/$f.md"; echo
  done
} > "$OUT/spec-combined.md"
python3 "$ROOT/tools/md2html.py" "$OUT/spec-combined.md" "$ROOT/tools/lehrplan.css" "$OUT/spezifikation.html" "Lernen wie Kids · Spezifikation"
{
  echo "# Уроки A1.0"; echo
  echo "MVP-lite одной страницей: как выглядит один экран, как проводить, и девять уроков слоя A1.0, расписанных пошагово. Исходники в spec/MVP-LITE.md и lessons/A1.0."; echo
  sed '1s/^# MVP-lite$/# Как это выглядит/' "$ROOT/spec/MVP-LITE.md"; echo
  sed '1s/^# Уроки A1.0$/# Как проводить/' "$ROOT/lessons/A1.0/README.md"; echo
  for f in 01 02 03 04 05 06 07 08 09; do cat "$ROOT/lessons/A1.0/urok-$f.md"; echo; done
  sed '1s/^# Задание: плеер уроков для проверки обучения$/# Задание на плеер/' "$ROOT/HANDOFF.md"; echo
} > "$OUT/uroki-combined.md"
python3 "$ROOT/tools/lessons-to-json.py" "$ROOT/lessons/A1.0" >/dev/null
python3 "$ROOT/tools/md2html.py" "$OUT/uroki-combined.md" "$ROOT/tools/lehrplan.css" "$OUT/uroki-a1.0.html" "Lernen wie Kids · A1.0 · Unterricht 1–9"
echo "готово: $OUT/uroki-a1.0.html"
{
  echo "# Уроки A1.1"; echo
  echo "Слой A1.1 одной страницей: пятнадцать уроков 10–24, расписанных пошагово: профессия и семья, лица, нравится, время и дни, мой день, самочувствие, кафе, город, анкета, сплошная проверка и ворота. Исходники в lessons/A1.1."; echo
  sed '1s/^# Уроки A1.1$/# Как проводить/' "$ROOT/lessons/A1.1/README.md"; echo
  for f in 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24; do cat "$ROOT/lessons/A1.1/urok-$f.md"; echo; done
} > "$OUT/uroki-a1.1-combined.md"
python3 "$ROOT/tools/lessons-to-json.py" "$ROOT/lessons/A1.1" >/dev/null
(cd "$ROOT" && python3 tools/lessons-index.py >/dev/null)
python3 "$ROOT/tools/md2html.py" "$OUT/uroki-a1.1-combined.md" "$ROOT/tools/lehrplan.css" "$OUT/uroki-a1.1.html" "Lernen wie Kids · A1.1 · Unterricht 10–24"
echo "готово: $OUT/uroki-a1.1.html"
echo "готово: $OUT/lehrplan-a1.html и $OUT/spezifikation.html"
