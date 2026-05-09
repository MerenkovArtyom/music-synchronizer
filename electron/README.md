# Electron Prototype

Это desktop-прототип для существующего Python backend из корня репозитория. Electron-часть не дублирует логику синхронизации и не ходит в Яндекс Музыку напрямую: она только запускает CLI, получает результат и показывает его в интерфейсе.

## Что уже есть

- окно Electron с renderer-интерфейсом для:
  - чтения конфигурации;
  - запуска синхронизации;
  - поиска активных заметок по тегу или артисту;
- безопасный preload-bridge через `window.musicSync`;
- IPC между renderer и main-процессом;
- запуск Python backend как дочернего процесса;
- нормализация ответов backend в единый типизированный envelope;
- тесты для разбора backend-команд и CLI-ответов.

## Архитектура

- `src/main/` — lifecycle окна, IPC handlers и запуск Python CLI.
- `src/preload/` — узкий bridge, который отдаёт renderer только разрешённые методы.
- `src/renderer/` — UI прототипа без прямого доступа к Node API.
- `src/shared/` — общие TypeScript-контракты между слоями.
- `tests/` — тесты backend-адаптера и парсинга ответов CLI.

Текущая модель ответственности такая:

- Python отвечает за реальные данные и бизнес-логику.
- Electron отвечает за запуск команд, преобразование результатов и UI.

## Команды

Запускать из директории [electron/](/Users/artem/Programming/music_synchronizer/electron):

```bash
npm install
npm run test
npm run typecheck
npm run build
npm run dev
```

Что делают команды:

- `npm install` — устанавливает dev-зависимости Electron/TypeScript.
- `npm run test` — запускает тесты `node --test` для backend-обвязки.
- `npm run typecheck` — проверяет типы TypeScript без сборки.
- `npm run build` — очищает `dist/`, проверяет типы и собирает main/preload/renderer.
- `npm run dev` — сначала выполняет `build`, затем запускает `electron .`.

Важно: `npm run dev` сейчас не даёт hot reload. По факту это локальный запуск уже собранного приложения.

## Как Electron находит backend

По умолчанию desktop shell запускает backend-команду:

```bash
uv run music-sync
```

Команда выполняется из корня репозитория через `MUSIC_SYNC_REPO_ROOT`. Это нужно, чтобы Electron мог использовать тот же Python CLI, что и основное приложение.

Для локальных экспериментов backend можно переопределить переменной окружения:

```bash
MUSIC_SYNC_BACKEND_COMMAND='["uv", "run", "music-sync"]' npm run dev
```

Правила для `MUSIC_SYNC_BACKEND_COMMAND`:

- значение должно быть JSON-массивом токенов команды;
- массив не может быть пустым;
- пустые элементы запрещены;
- shell-строка вроде `"uv run music-sync"` не подойдёт.

Это сделано специально, чтобы запускать subprocess без shell-парсинга.

## Текущий IPC surface

В `window.musicSync` доступны три операции:

- `showConfig()`
- `runSync()`
- `listTracks({ kind, value })`

Поддерживаемые фильтры для `listTracks`:

- `kind: "tag"`
- `kind: "artist"`

Renderer не вызывает CLI напрямую. Он общается только через preload и IPC-каналы:

- `music-sync:show-config`
- `music-sync:sync`
- `music-sync:list`

## Формат ответов от backend

Main-процесс приводит ответы Python CLI к единому виду:

```ts
type BackendEnvelope<T> =
  | { ok: true; command: "show-config" | "sync" | "list"; data: T }
  | { ok: false; command: "show-config" | "sync" | "list"; error: { code: string; message: string; details: Record<string, unknown> } };
```

Сейчас адаптер ожидает от Python CLI текстовый вывод, а не JSON:

- `show-config` должен вернуть строки `Obsidian path: ...` и `Log level: ...`;
- `sync` должен вернуть строку вида `Added: X, unchanged: Y, removed: Z.`;
- `list` должен вернуть либо список строк формата `Title - Artist`, либо сообщение об отсутствии результатов.

Если backend завершается с ошибкой или отдаёт неожиданный формат, Electron строит структурированный error envelope.

## Что показывает UI

Текущий интерфейс умеет:

- загрузить и показать безопасные метаданные конфигурации;
- запустить `sync` и показать summary;
- выполнить поиск по активным заметкам;
- отобразить статус операции: `idle`, `busy`, `success`, `error`.

Интерфейс сознательно не получает секреты напрямую. Например, в конфиг-блоке отображается только факт наличия токена, а не сам токен.

## Ограничения текущего прототипа

- Python runtime и окружение пока не упаковываются внутрь desktop-приложения.
- Прототип ожидает, что `uv` и backend проекта доступны локально.
- Парсинг построен вокруг текущего текстового CLI-вывода, поэтому изменение формата сообщений Python backend потребует синхронного обновления Electron-адаптера.
- Hot reload и packaging пока не реализованы.

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
2. стабилизировать контракт между Python CLI и Electron, чтобы уйти от хрупкого текстового парсинга;
3. при необходимости добавить live reload и dev-удобства для renderer/main.
