# music_synchronizer

Python-приложение на `uv` для синхронизации `Любимых треков` Яндекс Музыки с Obsidian.

## Быстрый старт

```bash
uv sync
cp .env.example .env
uv run music-sync --help
uv run pytest
```

## Команды

- `uv run music-sync --help` — показать доступные команды
- `uv run music-sync show-config` — проверить, что конфигурация читается
- `uv run music-sync sync` — синхронизировать `Любимые треки` в Obsidian
- `uv run music-sync list --tag rock` — вывести активные сохранённые треки с указанным тегом
- `uv run music-sync list --artist "Artist Name"` — вывести активные сохранённые треки с указанным артистом
- `uv run pytest -v` — прогнать тесты

## Конфигурация

Создай `.env` на основе `.env.example` и укажи:

- `YANDEX_MUSIC_TOKEN`
- `OBSIDIAN_VAULT_PATH`
- `LOG_LEVEL`

## Что создает синхронизация

После запуска `uv run music-sync sync` в vault поддерживаются:

- `tracks/<song title>.md` — отдельная заметка на каждый активный трек
- `tracks/_removed/<song title>.md` — архив заметок треков, которые исчезли из `Любимых`

Все трековые заметки создаются в одном формате: YAML frontmatter с метаданными и короткое Markdown-тело.

В frontmatter заметки хранятся `system_tags` и `user_tags`. Синхронизация обновляет только `system_tags` из данных Яндекс Музыки и сохраняет `user_tags`, которые были вручную добавлены пользователем прямо в YAML заметки.

## Примечания

- Для доступа к API используется пакет `yandex-music`.
- Имена файлов строятся по названию песни. При конфликте имен добавляется артист, а при необходимости и `track_id`.
- `track_id` сохраняется в frontmatter и используется как стабильный внутренний идентификатор для обновления, переименования и архивирования.
- `system_tags` содержат теги из Яндекс Музыки, а `user_tags` предназначены для ручного редактирования и не удаляются после `sync`.
- Команда `music-sync list --tag` ищет по объединению `system_tags` и `user_tags`.
- Команда `music-sync list` принимает ровно один фильтр: либо `--tag`, либо `--artist`.

## Electron Backend Contract

- Electron `main` process should invoke the backend with `--json` and parse exactly one JSON document from stdout.
- Supported machine-readable entrypoints are `music-sync show-config --json`, `music-sync sync --json`, and `music-sync list --json`.
- Success payloads use a common envelope: `{"ok": true, "command": "...", "data": ...}`.
- Failure payloads use a common envelope: `{"ok": false, "command": "...", "error": {"code": "...", "message": "...", "details": {...}}}`.
- `sync --json` returns `summary.fetched`, `summary.written`, `summary.archived`, `summary.restored`, and `summary.removed`.
- `show-config --json` exposes only safe config metadata, including whether a Yandex token is present; it does not echo the token value.
- Human-readable text mode remains for terminal use and should not be scraped by Electron.

## Electron Prototype

- The desktop scaffold lives in `electron/`.
- Run `cd electron && npm install && npm run dev` to open the prototype shell.
- Desktop-specific notes, backend command overrides, and packaging follow-ups live in `electron/README.md`.
