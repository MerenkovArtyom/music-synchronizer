# AGENTS.md

## Project summary

- This repository is a small Python 3.12 CLI app managed with `uv`.
- Goal: synchronize liked tracks from Yandex Music into an Obsidian vault as Markdown notes.
- Main entrypoint: `uv run music-sync`.

## Working commands

- Install dependencies: `uv sync`
- Show CLI help: `uv run music-sync --help`
- Check config loading: `uv run music-sync show-config`
- Run synchronization: `uv run music-sync sync`
- Run tests: `uv run pytest`
- Run a focused test file: `uv run pytest tests/test_cli.py -v`

## Code map

Local notes for coding agents.
- `src/music_synchronizer/cli.py`: Typer CLI commands and user-facing error handling.
- `src/music_synchronizer/config.py`: environment-based settings loaded from `.env`.
- `src/music_synchronizer/sync.py`: orchestration layer connecting Yandex client and Obsidian exporter.
- `src/music_synchronizer/yandex_client.py`: adapter over `yandex-music`, normalizes API objects into `TrackInfo`.
- `src/music_synchronizer/obsidian.py`: filesystem sync logic, Markdown/frontmatter rendering, archive behavior, note lookup helpers.
- `src/music_synchronizer/models.py`: dataclasses shared across modules.
- `tests/test_obsidian_sync.py`: core sync behavior and note format expectations.
- `tests/test_cli.py`: CLI behavior and filtering behavior.

## Repository conventions

- Keep the implementation simple and local. This project does not need extra layers or abstractions unless repetition becomes real.
- Prefer extending existing modules over creating new ones for small changes.
- Use ASCII unless a file already contains non-ASCII content and there is a reason to keep it.
- Keep CLI messages stable unless behavior intentionally changes; tests assert on exact output.

## Important invariants

- `track_id` is the stable identifier for managed notes. Do not switch matching logic to filename or title.
- Active notes live in `tracks/*.md`. Removed tracks are archived into `tracks/_removed/*.md`.
- Sync should preserve `user_tags` written by the user inside existing notes.
- Sync may update `system_tags` from Yandex Music data.
- Legacy `tags` frontmatter is treated as user-managed data and migrated into `user_tags`.
- The note format in `obsidian.py` is intentionally tested. Be careful when changing YAML/frontmatter keys or Markdown body text.
- Filename collisions are resolved by title, then title plus artist, then title plus artist plus `track_id`.
- `list` should only inspect active notes, not archived ones.

## Change guidance

- If you touch `obsidian.py`, run at least `uv run pytest tests/test_obsidian_sync.py -v`.
- If you touch `cli.py`, also run `uv run pytest tests/test_cli.py -v`.
- If you change config behavior, run `uv run pytest tests/test_config.py -v`.
- If you change Yandex normalization, run `uv run pytest tests/test_yandex_client.py -v`.
- Favor tests that lock in user-visible behavior before broad refactors.

## Safety notes

- Do not commit real tokens or a populated `.env`.
- Avoid writing outside the configured Obsidian vault path in tests or code.
- Prefer `tmp_path`-based tests for filesystem behavior.
- The project may contain user edits in the worktree. Do not revert unrelated changes.

## When updating behavior

- Preserve backward compatibility for existing notes where practical.
- Reflect user-visible command or format changes in `README.md`.
- Before finishing, run the smallest relevant pytest scope, and run the full `uv run pytest` when the change is broad.