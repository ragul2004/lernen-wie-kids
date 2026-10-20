# Плеер уроков Lernen wie Kids: статические файлы за nginx.
# Сборка:  docker build -t lwk-player .
# Запуск:  docker run --rm -p 8091:80 lwk-player   →  http://localhost:8091
FROM nginx:stable-alpine

COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY index.html /usr/share/nginx/html/index.html
COPY player /usr/share/nginx/html/player
# .dockerignore оставляет из lessons только index.json и папки json со всех слоёв.
COPY lessons /usr/share/nginx/html/lessons

EXPOSE 80
