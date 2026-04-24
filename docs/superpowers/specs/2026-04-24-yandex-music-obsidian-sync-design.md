# Yandex Music -> Obsidian Sync Design

## Goal

Build a Python application managed with `uv` that reads data from the Yandex Music API and exports it into Markdown files inside the Obsidian vault at `/Users/artem/Documents/my_music`.

## Scope

The initial MVP focuses on a local CLI application.

Included in MVP:
- project bootstrap with `uv`
- environment-based configuration
- Yandex Music API client wiring
- Markdown export into the Obsidian folder
- a single sync command for initial data pull
- basic test setup and developer documentation

Out of scope for MVP:
- bidirectional sync
- background daemon or scheduler
- conflict resolution between local edits and remote data
- advanced metadata enrichment from third-party services
- GUI or web interface

## Recommended Approach

We will build this as an application-first project:
- a CLI command is the main entry point
- internal modules stay focused on one responsibility each
- the code is structured so it can be split into a reusable library later if needed

This is the fastest path to a working sync tool while keeping the internals clean enough for future growth.

## Architecture

The application will use a small set of modules under `src/music_synchronizer/`:

- `cli.py`: Typer-based command line entry point
- `config.py`: load and validate environment variables
- `client.py`: Yandex Music API wrapper and authentication setup
- `models.py`: normalized internal models for exported entities
- `markdown_exporter.py`: Markdown rendering and file writing into Obsidian
- `sync_service.py`: orchestration layer that fetches data and exports files

Project-level files:
- `pyproject.toml`: dependencies, scripts, and tool configuration
- `.env.example`: example configuration values
- `.gitignore`: Python, `uv`, env, and cache ignores
- `README.md`: setup and run instructions
- `tests/`: baseline tests for config loading and Markdown export

## Data Flow

The main sync flow for MVP:

1. User runs `uv run music-sync sync`
2. The app loads `.env`
3. Config validation ensures the Yandex token and Obsidian path are present
4. The client authenticates against Yandex Music
5. The sync service fetches the chosen account data set for MVP
6. The exporter turns normalized entities into Markdown files
7. Files are written into `/Users/artem/Documents/my_music`

For the first iteration, the exported data set should stay intentionally small and predictable. The recommended MVP target is:
- favorite tracks
- playlists created by the user or saved in the account

## Markdown Storage Design

Markdown files should be easy to browse in Obsidian and safe to regenerate.

Recommended output structure:
- `tracks/<artist> - <title>.md`
- `playlists/<playlist-title>.md`

Each Markdown file should contain:
- YAML frontmatter with stable identifiers from Yandex Music
- human-readable metadata such as title, artist, album, duration, and source URLs when available
- a generated timestamp

The generated content should be deterministic so repeated syncs update existing files instead of creating duplicates.

## Configuration

Environment variables for MVP:
- `YANDEX_MUSIC_TOKEN`: auth token for API access
- `OBSIDIAN_VAULT_PATH`: target path, defaulting to `/Users/artem/Documents/my_music`
- `LOG_LEVEL`: optional logging level for local debugging

We will keep secrets in `.env` and commit only `.env.example`.

## Error Handling

The app should fail clearly for:
- missing or invalid environment variables
- invalid Obsidian path
- authentication failures
- Yandex API request failures
- file system write failures

CLI errors should be human-readable and actionable. We do not need retry logic in the MVP unless the client library makes it trivial.

## Testing

MVP tests should cover:
- config parsing and validation
- Markdown rendering for at least one track and one playlist shape
- sync orchestration with mocked client responses

Live API integration tests are not required for the first pass.

## Success Criteria

The MVP is successful when:
- a fresh clone can be initialized with `uv`
- the user can create a `.env` from `.env.example`
- `uv run music-sync sync` runs locally
- Markdown files appear in `/Users/artem/Documents/my_music`
- rerunning sync updates existing files deterministically

## Future Extensions

Possible next steps after MVP:
- incremental sync using saved state
- album and artist note generation
- richer Obsidian linking between entities
- scheduled sync via cron or launchd
- import filters and selective sync modes
