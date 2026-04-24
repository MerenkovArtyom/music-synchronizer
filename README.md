# music_synchronizer

Каркас Python-приложения на `uv` для будущей синхронизации Яндекс Музыки с Obsidian.

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
- `uv run music-sync sync` — текущая заглушка для будущей синхронизации
- `uv run pytest -v` — прогнать базовые тесты каркаса

## Конфигурация

Создай `.env` на основе `.env.example` и укажи:

- `YANDEX_MUSIC_TOKEN`
- `OBSIDIAN_VAULT_PATH`
- `LOG_LEVEL`
