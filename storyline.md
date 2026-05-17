# Storyline

## 2026-04-24

### Commit 1: project design

- Подготовлен дизайн синхронизации Yandex Music -> Obsidian и зафиксирован начальный план проекта.

### Commit 2: project skeleton

- Создан каркас Python CLI-проекта на `uv` с `pyproject.toml`, `.gitignore`, `README.md` и структурой `src/`.
- Добавлены `.env.example`, `Settings` и базовые CLI-команды `show-config` и `sync`.
- Написаны и пройдены стартовые тесты для конфигурации и CLI.
- Подготовлен локальный `.env` с путём к Obsidian vault.

### Commit 3: structured Obsidian track sync

- Добавлена зависимость `yandex-music` и внутренняя модель `TrackInfo` для нормализованных liked tracks.
- Реализован `YandexMusicClient`, который превращает ответ API в предсказуемую внутреннюю структуру.
- Добавлен `ObsidianExporter`, сохраняющий каждый трек как отдельную Markdown-заметку в `tracks/`.
- Закреплён `track_id` как стабильный идентификатор заметки, а для коллизий имён добавлены правила уникализации filename.
- Формат заметок унифицирован: YAML frontmatter плюс короткое Markdown-тело.
- Добавлен `SyncService` и подключён к CLI-команде `music-sync sync`.
- Реализованы архивирование удалённых треков в `tracks/_removed/`, восстановление при повторном появлении и удаление устаревшего `playlist.md`.
- Обновлён `README.md` под фактическое поведение синхронизации без отдельного индексного файла.
- Добавлены тесты на нормализацию, генерацию заметок, переименование, архивирование и безопасный CLI sync без частичной записи.

## 2026-04-25

### Commit 4: track tags in sync and notes

- В `TrackInfo` добавлено поле `tags` для тегов трека во внутренней модели.
- `YandexMusicClient` начал подтягивать жанровые теги из доступных метаданных Yandex Music.
- `ObsidianExporter` стал записывать теги в frontmatter заметок и объединять их с уже существующими ручными тегами.
- На этом этапе заметки ещё использовали единое поле `tags` без разделения на синхронизированные и пользовательские значения.
- Добавлены тесты на нормализацию тегов, запись в заметки и объединение сохранённых тегов.

### Commit 5: remove accidental design artifact

- Из репозитория удалён лишний markdown-файл с дизайн-заметками, попавший в коммит по ошибке.

### Commit 6: list saved tracks by tag

- Добавлена CLI-команда `music-sync list --tag <tag>` для просмотра активных сохранённых треков из Obsidian.
- Фильтрация по тегу работает по точному совпадению без учёта регистра и не затрагивает архив `tracks/_removed/`.

### Commit 7: list saved tracks by artist

- CLI-команда `music-sync list` расширена новым фильтром `--artist <artist>` по аналогии с тегами.
- Поиск по артисту работает по точному совпадению без учёта регистра и учитывает только активные заметки.
- Для `list` закреплено правило взаимоисключающих фильтров: нужно передать ровно один из `--tag` или `--artist`.
- Обновлены `README.md` и CLI-тесты под сценарии списка по артисту и валидацию нового контракта команды.

### Commit 8: make default vault path portable

- Значение по умолчанию для `OBSIDIAN_VAULT_PATH` переведено с жёстко заданного абсолютного пути на путь через `~`.

### Commit 9: expand default vault path

- Дефолтный путь к vault теперь сразу проходит через `expanduser()`, чтобы `~` корректно раскрывался в реальную домашнюю директорию.

## 2026-04-27

### Commit 10: preserve user tags across sync

- Формат заметок разделён на `system_tags` и `user_tags`.
- Во время `sync` обновляются только `system_tags`, а `user_tags` перечитываются из существующей заметки и не теряются.
- Для старых заметок с единым `tags` добавлена мягкая миграция: legacy-теги трактуются как `user_tags` и переписываются в новый формат при следующей синхронизации.
- `music-sync list` теперь ищет по объединению `system_tags` и `user_tags`, сохраняя прежнюю удобную семантику фильтрации.
- Вывод списка печатается в формате `Название - Artist1, Artist2`, а для пустого результата показывается отдельное сообщение.

### Commit 11: enrich note metadata

- В модель трека и заметки добавлены год релиза, URL обложки и человекочитаемая длительность.
- `YandexMusicClient` начал нормализовать эти поля из ответа API.
- `ObsidianExporter` стал сохранять расширенные метаданные в Markdown-заметки.
- Тесты зафиксировали новый формат заметок и поведение нормализации.

## 2026-05-03

### Commit 12: add repository instructions for coding agents

- В репозиторий добавлен `AGENTS.md` с проектным контекстом, рабочими командами и инвариантами для изменений.

### Commit 13: add Electron prototype app

- В репозиторий добавлено отдельное Electron-приложение с `main`, `preload`, `renderer` и базовой сборкой.
- Появился desktop backend в Electron-слое, который запускает существующую Python-логику и готовит данные для интерфейса.
- CLI-часть проекта расширена для сценариев, нужных локальному приложению.
- Добавлены тесты для Electron backend, синхронизации и обновлённого CLI.

### Commit 14: redesign Electron UI

- Обновлены HTML, TypeScript и CSS в renderer-части Electron-приложения.
- Интерфейс получил более проработанный визуальный стиль и доработанную структуру экрана.

### Commit 15: refresh README examples

- В `README.md` уточнён пример использования `music-sync list --tag`, чтобы документация соответствовала фактическому CLI.

## 2026-05-08

### Commit 16: add 30-day listen counts

- В синхронизируемые данные добавлено число прослушиваний трека за последние 30 дней.
- `YandexMusicClient` научился получать и нормализовать это значение, а `ObsidianExporter` записывает его в заметки.
- README и тесты обновлены под новую метрику.

### Commit 17: add snapshot-based incremental sync

- В синхронизацию добавлены snapshot-данные для инкрементального обновления Obsidian-заметок.
- `obsidian.py` и сервис синхронизации теперь умеют определять, когда можно избежать лишних изменений файлов.
- Обновлены CLI- и sync-тесты для сценариев частичного обновления.

## 2026-05-09

### Commit 18: merge Electron UI branch

- В `main` влит UI-branch `electron-app` без изменения уже реализованной логики sync.
- В основной ветке появились финальные файлы Electron UI, документация и backend-тесты из отдельной ветки.

### Commit 19: translate main README to Russian

- Основной `README.md` переписан и расширен на русском языке.
- Документация теперь подробнее описывает установку, CLI-команды и сценарии синхронизации.

### Commit 20: translate Electron README to Russian

- `electron/README.md` локализован на русский язык и синхронизирован с актуальным состоянием desktop-приложения.

### Commit 21: add top-listen command and note ranking

- Добавлена команда `music-sync top-listen` для локального ранжирования заметок по числу недавних прослушиваний.
- В Obsidian-слое и сервисе синхронизации появились структуры и логика для выборки top-треков из локальных заметок.
- Electron backend и UI получили поддержку отображения рейтинга самых прослушиваемых треков.
- README, backend-тесты и CLI-тесты обновлены под новую команду и ранжирование.

### Commit 22: add local dashboard for Obsidian and Electron

- Добавлен локальный dashboard, который агрегирует данные по заметкам Obsidian и отдаёт их в Electron.
- В Python-слое появились модели и функции для сводной статистики по библиотеке.
- Electron UI научился показывать dashboard-данные, а backend расширен новыми контрактами и обработчиками.
- Тесты закрепили поведение dashboard как в Python, так и в Electron-части.

## 2026-05-15

### Commit 23: shared desktop backend and macOS packaging

- Общая desktop-логика вынесена в Python-модуль `app.py`, чтобы CLI и Electron использовали единый backend.
- Добавлена отдельная `backend_cli.py` и переработаны команды CLI для сценариев desktop-интеграции.
- Конфигурация и тесты обновлены под новый способ запуска backend-сервиса.
- В Electron добавлена упаковка macOS-приложения и скрипты для сборки desktop backend вместе с приложением.
- README и `electron/README.md` обновлены под новую архитектуру и процесс упаковки.

## 2026-05-16

### Commit 24: add local re-listen recommendations

- Добавлены локальные рекомендации, какие лайкнутые треки стоит переслушать, без обращения к Yandex Music API.
- В Python backend появились модель рекомендации, локальный скоринг по артистам, жанрам и пользовательским тегам, а также новая команда `recommend --archived`.
- `dashboard.md` теперь включает нижний блок `Re-listen Recommendations`.
- Electron UI получил новый блок рекомендаций после `Monthly Top` и переключатель для включения архивных треков.
- README, Electron README и тесты обновлены под новый пользовательский сценарий.

### Commit 25: add Yandex discovery recommendations

- Добавлен новый сетевой поток `discovery`, который строит рекомендации из Yandex Music по последним прослушанным лайкнутым трекам.
- Discovery смешивает два источника: популярные треки артистов сидов и `tracks_similar`, исключая уже лайкнутые треки и дубликаты.
- В vault появилась новая папка `recommendations/`, а `sync` теперь автоматически удаляет из неё треки, которые пользователь уже лайкнул.
- Python CLI и shared desktop backend получили новую команду `discovery` и режим очистки `discovery --clear`.
- `dashboard.md` и Electron UI получили отдельный блок `Discovery Recommendations` между `Monthly Top` и локальными `Re-listen Recommendations`.
- README и тесты обновлены под новый формат рекомендаций и поведение очистки.

### Commit 26: rebalance re-listen recommendations

- Локальные `recommend`-рекомендации теперь отбираются в два этапа: сначала по обновлённому score, затем через diversity-pass.
- Скоринг стал более сбалансированным: совпадения по артисту всё ещё важны, но жанры, `user_tags` и давность прослушивания сильнее влияют на итоговый порядок.
- В финальной выдаче действует ограничение не более двух треков на одного primary artist, чтобы рекомендации не забивались одним исполнителем.
- Коллаборации с уже использованными артистами получают просадку в tie-break, поэтому список лучше перемешивается без изменения внешнего API.
- README и sync-тесты обновлены под новое поведение локальных рекомендаций.

## 2026-05-17

### Commit 27: sync discovery playlist to Yandex Music

- Discovery-рекомендации теперь дополнительно синхронизируются в отдельный playlist Яндекс Музыки.
- Имя discovery-playlist вынесено в настройку `YANDEX_MUSIC_DISCOVERY_PLAYLIST_NAME` с дефолтом `Рекомендации`.
- Для добавления треков в playlist сохраняется `album_id`, а при необходимости он доразрешается через lookup трека.
- `discovery --clear` очищает локальные рекомендации и удаляет discovery-playlist в Яндекс Музыке; fallback на удаление треков остаётся для клиентов без delete API.
- Обычный `sync` больше не удаляет discovery-рекомендации и не трогает discovery-playlist.
- README и тесты обновлены под новый контракт discovery.

### Commit 28: add Vault browser to Electron app

- В desktop-приложение добавлен read-only раздел `Vault` с деревом заметок и Markdown preview выбранного файла.
- Python backend получил новую команду `vault`, которая безопасно отдаёт структуру `my_music` и содержимое выбранной заметки без YAML frontmatter.
- В shared desktop contracts, preload bridge и Electron main-process добавлена сквозная поддержка нового `vault`-контракта.
- Vault browser сначала охватил `dashboard.md`, `tracks/`, `tracks/_removed/` и `recommendations/`, а затем был расширен на существующие папки `artists/` и `tags/`.
- README, `electron/README.md` и backend-тесты обновлены под новый сценарий просмотра заметок через приложение.

### Commit 29: redesign Electron app as a note-first desktop shell

- Electron renderer полностью перестроен в постоянный desktop-shell с левой навигацией, списком заметок, центральным viewer и правой metadata-панелью.
- Полноценно реализованы разделы `Песни`, `Рекомендации` и `Dashboard`, а остальные пункты меню пока оставлены как заглушки.
- Экран `Песни` теперь читает локальные заметки из `tracks/` и `tracks/_removed/`, парсит frontmatter на клиенте и показывает содержимое заметки вместе с метаданными.
- Экран `Рекомендации` переведён на просмотр локальной папки `recommendations/` через `vault`, без создания новых рекомендаций из UI.
- Для renderer-слоя добавлен отдельный controller и тесты, а стили приведены к новому desktop-оформлению по макету.

### Commit 30: simplify dashboard view and remove recommendation blocks

- `dashboard.md` больше не включает разделы `Discovery Recommendations` и `Re-listen Recommendations`.
- Dashboard в приложении переведён в более спокойный obsidian-like режим: без второй и четвёртой колонок, с упором на чтение самой заметки.
- Заголовок и типографика dashboard-view в Electron подстроены под формат обычной vault-note, а не отдельной dashboard-card.
- Python- и Electron-тесты обновлены под новый формат dashboard без recommendation-блоков.
