# Repository Guidelines

## Project Structure & Module Organization
- Flutter app entrypoint at `lib/main.dart`; shared services under `lib/services/` (`mqtt_service.dart` for connectivity, `update_service.dart` for update checks).
- Platform scaffolding lives in `android/`, `ios/`, `macos/`, `linux/`, `windows/`, `web/`; tests in `test/`.
- Docs and plans: `CLAUDE.md` (MQTT and workflow notes) and `plans/` for module roadmaps; build outputs reside in `build/`.

## Build, Test, and Development Commands
- Install deps: `fvm flutter pub get` (use FVM for consistent tooling).
- Run app: `fvm flutter run` (add `-d chrome` or device id as needed).
- Lint/analyze: `fvm flutter analyze`.
- Format: `dart format .` (or scope to touched files before committing).
- Tests: `fvm flutter test` (target a file with `fvm flutter test test/widget_test.dart`).
- Release builds: `fvm flutter build apk`, `fvm flutter build ios`, or `fvm flutter build windows`.

## Coding Style & Naming Conventions
- Follow `flutter_lints` from `analysis_options.yaml`; fix analyzer warnings before pushing.
- Dart defaults: 2-space indent, `PascalCase` for classes/widgets, `camelCase` for methods/fields, `SCREAMING_SNAKE_CASE` for consts.
- Prefer `const` constructors where possible; keep widgets small and composable; avoid unused imports and stray `print` in production code.

## Testing Guidelines
- Place tests in `test/` with filenames ending `_test.dart`.
- Add unit tests for service logic (e.g., MQTT reconnect behavior) and widget tests for UI states.
- Run `fvm flutter test` locally before opening a PR; ensure new features include coverage for error paths where feasible.

## Commit & Pull Request Guidelines
- Commits: short, imperative subject lines; optional scope (e.g., `mqtt: handle reconnect backoff`).
- PRs: include a concise summary, testing notes (`fvm flutter test`, `fvm flutter analyze`), and screenshots for UI changes. Link issues/tasks when available and note any follow-ups.
- Keep diffs focused; update docs (`CLAUDE.md`, `plans/`, or in-code comments) when behavior changes.

## Security & Configuration Tips
- Do not commit secrets or credentials; treat keystores and API tokens as sensitive.
- MQTT topics, QoS, and reconnect expectations live in `CLAUDE.md`—adhere to those contracts when modifying `mqtt_service.dart`.
- Avoid hardcoding environment-specific URLs; keep logs free of sensitive payloads.
