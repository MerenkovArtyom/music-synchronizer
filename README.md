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

## Примечания

- Для доступа к API используется пакет `yandex-music`.
- Имена файлов строятся по названию песни. При конфликте имен добавляется артист, а при необходимости и `track_id`.
- `track_id` сохраняется в frontmatter и используется как стабильный внутренний идентификатор для обновления, переименования и архивирования.
