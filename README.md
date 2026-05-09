# music_synchronizer

Небольшой CLI-проект на Python 3.12 и `uv`, который синхронизирует понравившиеся треки из Яндекс Музыки в Obsidian как Markdown-заметки.

Сейчас основная цель проекта:

- выгрузить лайки из Яндекс Музыки;
- сохранить каждый трек как отдельную заметку в vault Obsidian;
- поддерживать заметки в актуальном состоянии при повторных запусках;
- не затирать пользовательские теги, добавленные вручную.

Главная команда:

```bash
uv run music-sync
```

## Возможности

- Синхронизация лайкнутых треков Яндекс Музыки в `tracks/*.md`.
- Архивация удалённых из лайков треков в `tracks/_removed/*.md`.
- Хранение стабильного идентификатора `track_id` в каждой заметке.
- Разделение тегов на:
  - `system_tags` — приходят из Яндекс Музыки;
  - `user_tags` — редактируются пользователем и сохраняются между синками.
- Миграция legacy-поля `tags` в `user_tags`.
- Подсчёт `monthly_listens` по истории прослушиваний за последние 30 дней.
- Поиск уже сохранённых активных треков через `list --tag` и `list --artist`.
- Разрешение конфликтов имён файлов по схеме:
  - `title`;
  - `title - artist`;
  - `title - artist [track_id]`.

## Требования

- Python 3.12+
- `uv`
- токен Яндекс Музыки
- локальный vault Obsidian

## Быстрый старт

```bash
uv sync
cp .env.example .env
```

Заполни `.env` и проверь, что CLI видит конфигурацию:

```bash
uv run music-sync show-config
uv run music-sync --help
```

После этого можно запускать синхронизацию:

```bash
uv run music-sync sync
```

## Конфигурация

Проект читает настройки из `.env`.

Пример:

```env
YANDEX_MUSIC_TOKEN=your-token-here
OBSIDIAN_VAULT_PATH=/Users/your_name/Documents/my_music
LOG_LEVEL=INFO
```

Переменные:

- `YANDEX_MUSIC_TOKEN` — токен для API Яндекс Музыки.
- `OBSIDIAN_VAULT_PATH` — путь до корня vault Obsidian.
- `LOG_LEVEL` — уровень логирования. По умолчанию `INFO`.

Если `OBSIDIAN_VAULT_PATH` не задан, используется путь по умолчанию `~/Documents/my_music`.

## Команды CLI

```bash
uv run music-sync --help
uv run music-sync show-config
uv run music-sync sync
uv run music-sync top-listen --most
uv run music-sync top-listen --least
uv run music-sync list --tag "rock"
uv run music-sync list --artist "Artist Name"
```

Что делают команды:

- `uv run music-sync --help` — показывает список доступных команд.
- `uv run music-sync show-config` — печатает путь до vault и текущий `LOG_LEVEL`.
- `uv run music-sync sync` — запускает синхронизацию лайков в Obsidian.
- `uv run music-sync top-listen --most` — показывает top 10 локально сохранённых треков с самым большим `monthly_listens`.
- `uv run music-sync top-listen --least` — показывает top 10 локально сохранённых треков с самым маленьким `monthly_listens`.
- `uv run music-sync list --tag "rock"` — ищет активные сохранённые треки по тегу.
- `uv run music-sync list --artist "Artist Name"` — ищет активные сохранённые треки по артисту.

Особенности команды `list`:

- нужно передать ровно один фильтр: либо `--tag`, либо `--artist`;
- поиск идёт только по активным заметкам в `tracks/`;
- архив `tracks/_removed/` не участвует в выдаче;
- поиск по тегам учитывает и `system_tags`, и `user_tags`;
- если значение содержит пробелы, его нужно передавать в кавычках.

Особенности команды `top-listen`:

- команда читает только активные заметки из `tracks/`;
- архив `tracks/_removed/` не участвует в выдаче;
- ранжирование идёт по локально сохранённому `monthly_listens`;
- при одинаковом количестве прослушиваний раньше остаётся трек, который выше в лайках;
- нужно передать ровно один флаг: `--most` или `--least`;
- в каждом списке выводится не больше 10 треков.

## Как устроена синхронизация

При запуске `sync` проект:

1. запрашивает список лайкнутых треков через `yandex-music`;
2. пытается посчитать количество прослушиваний за последние 30 дней;
3. создаёт или обновляет заметки в Obsidian;
4. переносит исчезнувшие из лайков треки в архив;
5. сохраняет служебный снапшот в `.music_sync_snapshot.json`.

Синхронизация ориентируется на `track_id`, а не на имя файла. Это важно: заметка может быть переименована при изменении названия трека или разрешении коллизии, но связь с треком остаётся стабильной.

## Структура заметок в Obsidian

Активные заметки:

- `tracks/<имя файла>.md`

Архив:

- `tracks/_removed/<имя файла>.md`

Служебный файл:

- `.music_sync_snapshot.json`

Каждая заметка содержит YAML frontmatter и Markdown-тело. Пример:

```md
---
track_id: "123"
title: "Song"
artists: ["Artist"]
album: "Album"
system_tags: ["indie"]
user_tags: ["favorites"]
year: 2024
monthly_listens: 7
cover_url: "https://example.com/cover.jpg"
duration_seconds: 180
position: 1
source: "likes"
yandex_url: "https://music.yandex.ru/track/123"
synced_at: "2026-04-24T12:00:00+00:00"
---

# Song

Artists: Artist
Album: Album
Year: 2024
Monthly listens (30d): 7
Duration: 3:00
Yandex Music: https://music.yandex.ru/track/123
```

Важные правила:

- `track_id` — главный идентификатор управляемой заметки.
- `system_tags` могут обновляться при следующем `sync`.
- `user_tags` сохраняются и не должны теряться после повторной синхронизации.
- старое поле `tags` считается пользовательским и при обновлении мигрирует в `user_tags`.
- если у трека нет части метаданных, проект подставляет безопасные значения, например `null`, пустую строку или `-` в Markdown-теле.

## Тесты и разработка

Установка зависимостей:

```bash
uv sync
```

Запуск всех тестов:

```bash
uv run pytest
```

Запуск отдельных наборов:

```bash
uv run pytest tests/test_cli.py -v
uv run pytest tests/test_obsidian_sync.py -v
uv run pytest tests/test_config.py -v
uv run pytest tests/test_yandex_client.py -v
```

Полезно помнить:

- если меняется CLI, стоит прогнать `tests/test_cli.py`;
- если меняется логика заметок и файловой синхронизации, стоит прогнать `tests/test_obsidian_sync.py`;
- если меняется загрузка настроек, стоит прогнать `tests/test_config.py`;
- если меняется нормализация данных Яндекс Музыки, стоит прогнать `tests/test_yandex_client.py`.

## Структура репозитория

- [src/music_synchronizer/cli.py](/Users/artem/Programming/music_synchronizer/src/music_synchronizer/cli.py) — Typer CLI и пользовательские сообщения.
- [src/music_synchronizer/config.py](/Users/artem/Programming/music_synchronizer/src/music_synchronizer/config.py) — настройки из окружения и `.env`.
- [src/music_synchronizer/sync.py](/Users/artem/Programming/music_synchronizer/src/music_synchronizer/sync.py) — orchestration слой синхронизации.
- [src/music_synchronizer/yandex_client.py](/Users/artem/Programming/music_synchronizer/src/music_synchronizer/yandex_client.py) — адаптер над `yandex-music`.
- [src/music_synchronizer/obsidian.py](/Users/artem/Programming/music_synchronizer/src/music_synchronizer/obsidian.py) — запись заметок, архив, снапшоты и поиск.
- [src/music_synchronizer/models.py](/Users/artem/Programming/music_synchronizer/src/music_synchronizer/models.py) — общие dataclass-модели.
- [tests/test_cli.py](/Users/artem/Programming/music_synchronizer/tests/test_cli.py) — тесты CLI.
- [tests/test_obsidian_sync.py](/Users/artem/Programming/music_synchronizer/tests/test_obsidian_sync.py) — тесты формата заметок и синка.

## Electron-прототип

В репозитории также есть прототип desktop-оболочки в [electron/](/Users/artem/Programming/music_synchronizer/electron).

Важно:

- это тонкая оболочка над существующим Python CLI;
- текущий backend для Electron по умолчанию запускает `uv run music-sync`;
- Electron-часть пока не заменяет и не дублирует основную логику синхронизации.

Подробности по desktop-прототипу лежат в [electron/README.md](/Users/artem/Programming/music_synchronizer/electron/README.md).
