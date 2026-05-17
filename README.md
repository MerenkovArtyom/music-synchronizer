# music_synchronizer

Небольшой CLI-проект на Python 3.12 и `uv`, который синхронизирует понравившиеся треки из Яндекс Музыки в Obsidian как Markdown-заметки.

Сейчас основная цель проекта:

- выгрузить лайки из Яндекс Музыки;
- сохранить каждый трек как отдельную заметку в vault Obsidian;
- поддерживать заметки в актуальном состоянии при повторных запусках;
- не затирать пользовательские теги, добавленные вручную.

Главные команды:

```bash
uv run music-sync
uv run music-sync-app show-config
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
- Локальный dashboard-файл `dashboard.md` с агрегатами по активным и архивным заметкам.
- Локальные рекомендации, какие лайкнутые треки стоит переслушать, на основе недавних артистов, жанров и тегов.
- Сетевые discovery-рекомендации из Yandex Music в `recommendations/*.md`.
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
YANDEX_MUSIC_DISCOVERY_PLAYLIST_NAME=Рекомендации
LOG_LEVEL=INFO
```

Переменные:

- `YANDEX_MUSIC_TOKEN` — токен для API Яндекс Музыки.
- `OBSIDIAN_VAULT_PATH` — путь до корня vault Obsidian.
- `YANDEX_MUSIC_DISCOVERY_PLAYLIST_NAME` — имя playlist в Яндекс Музыке для discovery-рекомендаций. По умолчанию `Рекомендации`.
- `LOG_LEVEL` — уровень логирования. По умолчанию `INFO`.

Если `OBSIDIAN_VAULT_PATH` не задан, используется путь по умолчанию `~/Documents/my_music`.

## Команды CLI

```bash
uv run music-sync --help
uv run music-sync show-config
uv run music-sync sync
uv run music-sync dashboard
uv run music-sync top-listen --most
uv run music-sync top-listen --least
uv run music-sync discovery
uv run music-sync discovery --clear
uv run music-sync recommend
uv run music-sync recommend --archived
uv run music-sync list --tag "rock"
uv run music-sync list --artist "Artist Name"
uv run music-sync-app show-config
```

Что делают команды:

- `uv run music-sync --help` — показывает список доступных команд.
- `uv run music-sync show-config` — печатает путь до vault и текущий `LOG_LEVEL`.
- `uv run music-sync sync` — запускает синхронизацию лайков в Obsidian.
- `uv run music-sync dashboard` — пересчитывает `dashboard.md` только по локально сохранённым заметкам в vault.
- `uv run music-sync top-listen --most` — показывает top 10 локально сохранённых треков с самым большим `monthly_listens`.
- `uv run music-sync top-listen --least` — показывает top 10 локально сохранённых треков с самым маленьким `monthly_listens`.
- `uv run music-sync recommend` — рекомендует похожие лайкнутые треки, которые давно не слушались.
- `uv run music-sync recommend --archived` — то же самое, но дополнительно включает архив `tracks/_removed/`.
- `uv run music-sync discovery` — получает новые сетевые рекомендации из Yandex Music, сохраняет их в `recommendations/` и добавляет в discovery-плейлист Яндекс Музыки.
- `uv run music-sync discovery --clear` — очищает папку `recommendations/` и discovery-плейлист Яндекс Музыки.
- `uv run music-sync list --tag "rock"` — ищет активные сохранённые треки по тегу.
- `uv run music-sync list --artist "Artist Name"` — ищет активные сохранённые треки по артисту.
- `uv run music-sync-app ...` — machine-readable backend entrypoint для desktop app; печатает JSON envelope вместо человекочитаемого текста.

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

Особенности команды `dashboard`:

- команда читает только локальные заметки в `tracks/` и `tracks/_removed/`;
- Yandex Music API не используется;
- файл `dashboard.md` создаётся в корне vault;
- в отчёт входят счётчики активных и архивных треков, длительность, покрытие `monthly_listens`, лидеры по тегам и артистам, а также блок рекомендаций.

Особенности команды `recommend`:

- команда читает только локальные заметки и не обращается к Yandex Music API;
- по умолчанию участвуют только активные заметки из `tracks/`;
- флаг `--archived` дополнительно включает архив `tracks/_removed/`;
- “жанры” берутся из `system_tags`, а пользовательские сигналы из `user_tags`;
- рекомендация требует хотя бы одного совпадения по артисту, жанру или пользовательскому тегу;
- скоринг балансирует совпадения по артистам, жанрам, `user_tags` и давность прослушивания, чтобы забытые треки поднимались выше;
- в выдаче не больше 2 треков с одним и тем же основным артистом (`artists[0]`);
- в выдаче не больше 10 треков.

Особенности команды `discovery`:

- команда использует Yandex Music API, а не только локальные заметки;
- за основу берутся последние прослушанные лайкнутые треки из `music_history`;
- рекомендации смешиваются из двух источников:
  - популярные треки артистов сидов;
  - `tracks_similar` для самих сидов;
- лайкнутые треки и дубликаты по `track_id` исключаются;
- новые заметки пишутся в `recommendations/` в корне vault;
- новые треки также добавляются в playlist Яндекс Музыки с именем из `YANDEX_MUSIC_DISCOVERY_PLAYLIST_NAME`;
- если такого playlist ещё нет, команда создаёт его автоматически;
- команда работает накопительно и не пересобирает папку целиком;
- `sync` не трогает сохранённые discovery-рекомендации;
- `--clear` полностью очищает `recommendations/` и удаляет discovery-playlist в Яндекс Музыке.

## Как устроена синхронизация

При запуске `sync` проект:

1. запрашивает список лайкнутых треков через `yandex-music`;
2. пытается посчитать количество прослушиваний за последние 30 дней;
3. создаёт или обновляет заметки в Obsidian;
4. переносит исчезнувшие из лайков треки в архив;
5. обновляет локальный `dashboard.md`;
6. сохраняет служебный снапшот в `.music_sync_snapshot.json`.

Синхронизация ориентируется на `track_id`, а не на имя файла. Это важно: заметка может быть переименована при изменении названия трека или разрешении коллизии, но связь с треком остаётся стабильной.

## Структура заметок в Obsidian

Активные заметки:

- `tracks/<имя файла>.md`

Архив:

- `tracks/_removed/<имя файла>.md`

Discovery recommendations:

- `recommendations/<имя файла>.md`

Служебный файл:

- `.music_sync_snapshot.json`

Dashboard:

- `dashboard.md`

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

В репозитории также есть desktop-оболочка в [electron/](/Users/artem/Programming/music_synchronizer/electron).

Важно:

- это оболочка над общим Python app-backend;
- текущий backend для Electron по умолчанию запускает `uv run music-sync-app`;
- Electron-часть пока не заменяет и не дублирует основную логику синхронизации.

Команды для Electron:

```bash
cd electron
npm run test
npm run typecheck
npm run build
npm run dev
npm run package
npm run package:mac
```

Что важно про `npm run package`:

- команда подготавливает packaged-layout backend в `electron/dist/package/backend`;
- внутри staging-бандла лежат `src/`, локальный `.venv` и launcher `music-sync-app`;
- это MVP для standalone-layout и он зависит от локально собранного окружения, а не от универсального инсталлера.
- `npm run package:mac` создаёт локальный macOS `.app` bundle в `electron/release/`.

Подробности по desktop-прототипу лежат в [electron/README.md](/Users/artem/Programming/music_synchronizer/electron/README.md).
