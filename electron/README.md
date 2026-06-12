# Electron Prototype

Это desktop-оболочка для существующего Python backend из корня репозитория. Electron-часть не дублирует логику синхронизации и не ходит в Яндекс Музыку напрямую: она запускает отдельный Python app-backend, получает JSON-ответ и показывает его в интерфейсе.

## Что уже есть

- окно Electron с renderer-интерфейсом для:
  - чтения и сохранения конфигурации;
  - выбора Obsidian vault через системный folder picker;
  - запуска синхронизации;
  - загрузки локального dashboard;
  - поиска активных заметок по тегу или артисту;
  - read-only просмотра структуры `my_music` и preview Markdown-заметок во вкладке Vault;
- безопасный preload-bridge через `window.musicSync`;
- IPC между renderer и main-процессом;
- запуск Python backend как дочернего процесса;
- строгая runtime-валидация JSON-ответов backend по checked-in JSON Schema;
- тесты для разбора backend-команд и CLI-ответов.

## Архитектура

- `src/main/` — lifecycle окна, IPC handlers и запуск Python CLI.
- `src/preload/` — узкий bridge, который отдаёт renderer только разрешённые методы.
- `src/renderer/` — UI прототипа без прямого доступа к Node API.
- `src/shared/` — общие TypeScript-контракты между слоями.
- `tests/` — тесты backend-адаптера и парсинга ответов CLI.

Текущая модель ответственности такая:

- Python отвечает за реальные данные и бизнес-логику.
- Electron отвечает за запуск backend-команд, IPC и UI.
- `music-sync` остаётся отдельным пользовательским CLI.
- `music-sync-app` остаётся отдельным JSON-only backend для Electron.

## Команды

Запускать из директории [electron/](/Users/artem/Programming/music_synchronizer/electron):

```bash
npm install
npm run test
npm run typecheck
npm run build
npm run dev
npm run package:backend
npm run package:standalone
npm run package:mac
```

Что делают команды:

- `npm install` — устанавливает dev-зависимости Electron/TypeScript.
- `npm run test` — запускает тесты `node --test` для backend-обвязки.
- `npm run typecheck` — проверяет типы TypeScript без сборки.
- `npm run build` — очищает `dist/`, проверяет типы и собирает main/preload/renderer.
- `npm run dev` — сначала выполняет `build`, затем запускает `electron .`.
- `npm run package:backend` — подготавливает `dist/package/backend` со standalone Python runtime для production-layout сценария.
- `npm run package:standalone` — собирает Electron-часть и staging backend вместе.
- `npm run package:mac` — создаёт macOS arm64 `.app` bundle в `release/mac-arm64/`.

Важно: `npm run dev` сейчас не даёт hot reload. По факту это локальный запуск уже собранного приложения.

## Как Electron находит backend

По умолчанию desktop shell в dev-режиме запускает backend-команду:

```bash
uv run music-sync-app
```

Команда выполняется из корня репозитория через `MUSIC_SYNC_REPO_ROOT`. Это нужно, чтобы Electron мог использовать тот же Python CLI, что и основное приложение.

Для desktop-конфигурации Electron также всегда пробрасывает:

```text
MUSIC_SYNC_CONFIG_PATH=<app.getPath("userData")>/config.env
```

На macOS это даёт пользовательский config path вида:

```text
~/Library/Application Support/Music Synchronizer/config.env
```

Именно этот файл использует `.app` для first-run setup и дальнейших запусков. Локальный `.env` по-прежнему нужен только для обычного CLI и dev-сценариев вне desktop UI.

`music-sync-app` уже зарегистрирован в корневом [`pyproject.toml`](/Users/artem/Programming/music_synchronizer/pyproject.toml) и не требует отдельного launcher entrypoint в исходниках Electron.

Для локальных экспериментов backend можно переопределить переменной окружения:

```bash
MUSIC_SYNC_BACKEND_COMMAND='["uv", "run", "music-sync-app"]' npm run dev
```

Правила для `MUSIC_SYNC_BACKEND_COMMAND`:

- значение должно быть JSON-массивом токенов команды;
- массив не может быть пустым;
- пустые элементы запрещены;
- shell-строка вроде `"uv run music-sync"` не подойдёт.

Это сделано специально, чтобы запускать subprocess без shell-парсинга.

## Текущий IPC surface

В `window.musicSync` доступны операции:

- `showConfig()`
- `saveConfig({ yandexMusicToken, obsidianVaultPath, discoveryPlaylistName, logLevel })`
- `chooseVaultPath()`
- `runSync()`
- `getDashboard()`
- `listTracks({ kind, value })`
- `getTopListen({ mode })`
- `getRecommendations({ archived })`
- `getDiscoveryRecommendations({ clear })`
- `getVaultView({ selectedPath? })`

Поддерживаемые фильтры для `listTracks`:

- `kind: "tag"`
- `kind: "artist"`

Renderer не вызывает CLI напрямую. Он общается только через preload и IPC-каналы:

- `music-sync:show-config`
- `music-sync:save-config`
- `music-sync:choose-vault-path`
- `music-sync:sync`
- `music-sync:dashboard`
- `music-sync:list`
- `music-sync:top-listen`
- `music-sync:recommend`
- `music-sync:discovery`
- `music-sync:vault`

## Формат ответов от backend

Main-процесс принимает только JSON output от `music-sync-app` и валидирует его по схемам из [src/shared/backend-schemas/](/Users/artem/Programming/music_synchronizer/electron/src/shared/backend-schemas):

```ts
type BackendEnvelope<T> =
  | { ok: true; command: "show-config" | "save-config" | "sync" | "dashboard" | "list" | "top-listen" | "recommend" | "discovery" | "vault"; data: T }
  | { ok: false; command: "show-config" | "save-config" | "sync" | "dashboard" | "list" | "top-listen" | "recommend" | "discovery" | "vault"; error: { code: string; message: string; details: Record<string, unknown> } };
```

- `music-sync-app` должен вернуть JSON envelope вида `{ ok, command, data }` или `{ ok, command, error }`;
- `music-sync-app` должен писать в `stdout` ровно один JSON document на вызов;
- любые логи и диагностические сообщения должны идти в `stderr` или файл, но не в `stdout`;
- payload с пропущенными полями, неверным `command` или лишней структурой отклоняется ещё в main-процессе.

- `show-config` возвращает полные текущие значения desktop-конфига;
- `save-config` сначала проверяет токен Яндекс Музыки, а затем атомарно записывает пользовательский config file;
- `sync` возвращает структурированный summary;
- `dashboard` возвращает path dashboard-файла, summary и top-списки;
- `list` возвращает filter + массив треков;
- `top-listen` всегда возвращает и `mostPlayed`, и `leastPlayed`, при этом одна из коллекций может быть пустой;
- `recommend` возвращает `includeArchived` и массив `recommendations`;
- `discovery` возвращает `summary` и массив `recommendations`;
- `vault` возвращает путь до vault, дерево управляемых Markdown-узлов и выбранную заметку для preview.

Если backend завершается с ошибкой или отдаёт неожиданный формат, Electron строит структурированный error envelope и не пытается “угадать” данные из человекочитаемого текста.

## Что показывает UI

Текущий интерфейс умеет:

- открыть welcome/setup state на первом запуске, если не сохранены и токен, и vault path;
- показать отдельные empty states, если не хватает только токена или только `Obsidian vault path`;
- показать и отредактировать `Yandex Music token`, `Obsidian vault path`, `Discovery playlist name` и `Log level`;
- сохранить настройки в пользовательский config path без терминала;
- показать понятное loading-сообщение, пока приложение проверяет токен перед сохранением настроек;
- не сохранять настройки, если токен невалидный;
- запустить `sync` и показать summary;
- загрузить dashboard, рассчитанный по локальным заметкам и архиву;
- выполнить поиск по активным заметкам;
- загрузить дерево управляемых папок `artists/`, `tags/`, `tracks/`, `tracks/_removed/`, `recommendations/` и root-level Markdown вроде `dashboard.md`;
- открыть заметку из дерева и прочитать её в rendered Markdown preview без YAML frontmatter;
- показать top 10 самых и наименее прослушиваемых локально сохранённых треков из активных заметок;
- показать блок рекомендаций внизу окна и при желании включить архив в расчёт;
- отобразить статус операции: `idle`, `busy`, `success`, `error`.

При незаполненном setup все sync-driven действия блокируются, а приложение ведёт пользователя в `Настройки`.

Ожидаемые recoverable ошибки в UI:

- `YANDEX_AUTH_INVALID` — токен не подошёл, пользователь получает следующий шаг: обновить токен и пересохранить настройки;
- `YANDEX_API_UNAVAILABLE` — Яндекс Музыка недоступна, пользователю предлагается повторить позже;
- `BACKEND_BINARY_NOT_FOUND`, `DEV_RUNTIME_NOT_FOUND`, `BACKEND_UNAVAILABLE` — desktop shell показывает отдельный dev-environment state вместо обычной продуктовой ошибки.

Важно для `npm run dev`:

- dev-запуск наследует переменные окружения текущего терминала;
- если в shell уже заданы `YANDEX_MUSIC_TOKEN` или `OBSIDIAN_VAULT_PATH`, приложение может пропустить first-run welcome screen даже при пустом `config.env`;
- для чистой проверки onboarding лучше запускать `npm run dev` без этих переменных.

## Ограничения текущего прототипа

- Dev-режим по-прежнему ожидает, что `uv` и backend проекта доступны локально.
- Production packaging собирается на macOS arm64 и использует embedded Python runtime из локального build-окружения.
- `npm run package:mac` собирает локальный unsigned `.app`, но ещё не делает DMG, signing или notarization.
- Hot reload пока не реализован.

## Куда смотреть в коде

- [src/main/backend.ts](/Users/artem/Programming/music_synchronizer/electron/src/main/backend.ts) — разбор `MUSIC_SYNC_BACKEND_COMMAND`, запуск процесса и нормализация ответов.
- [src/main/index.ts](/Users/artem/Programming/music_synchronizer/electron/src/main/index.ts) — окно приложения и регистрация IPC handlers.
- [src/preload/index.ts](/Users/artem/Programming/music_synchronizer/electron/src/preload/index.ts) — bridge `window.musicSync`.
- [src/shared/contracts.ts](/Users/artem/Programming/music_synchronizer/electron/src/shared/contracts.ts) — общие типы и envelope-контракты.
- [src/renderer/index.ts](/Users/artem/Programming/music_synchronizer/electron/src/renderer/index.ts) — клиентская логика интерфейса.
- [tests/backend.test.ts](/Users/artem/Programming/music_synchronizer/electron/tests/backend.test.ts) — тесты backend-адаптера.

## Дальше

Следующие логичные шаги для прототипа:

1. решить, будет ли desktop-версия поставляться вместе с Python runtime;
2. расширять UI уже поверх зафиксированного JSON-only backend-контракта;
3. при необходимости добавить live reload и dev-удобства для renderer/main.
