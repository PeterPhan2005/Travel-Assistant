---
id: T001
title: Verify development environment
status: done
depends_on: [T000]
area: foundation
---

# Goal

Add a checked setup script/document that verifies Git, Android tooling, Python, Docker, Node and Codex CLI.

# Read first

- `AGENTS.md`
- Applicable nested `AGENTS.md`
- `docs/context/00-project-overview.md`
- `docs/context/01-product-requirements.md`
- `docs/context/03-architecture.md`
- `docs/context/12-progress-tracker.md`

# Scope

Implement only the goal and acceptance criteria in this file.

# Out of scope

- Future tasks.
- Unrequested refactors.
- New product behavior not present in context files.

# Acceptance criteria

- [x] A new developer can follow SETUP.md.
- [x] Verification commands are documented.
- [x] Known machine-specific gaps are recorded.
- [x] Relevant tests are added or updated.
- [x] Required checks pass or failures are documented.
- [x] `docs/context/12-progress-tracker.md` is updated.

# Required checks

```bash
python --version
docker --version
node --version
codex --version
```

# Expected evidence

- Concise summary.
- Exact files changed.
- Test/check output.
- Known limitations.

# Verification evidence

Audited on 2026-07-19 on an Apple Silicon Mac. The repository checker is
`scripts/verify-development-environment.sh`; it is read-only and reports all
failures before returning a non-zero exit code.

Verified environment:

- Apple Silicon `arm64`, macOS 26.3.1, Xcode Command Line Tools and Homebrew
  6.0.11.
- Git 2.52.0.
- Android Studio 2026.1 and Java 21.0.5.
- Android SDK Platform `android-36.1`, Build-Tools 36.0.0, adb 37.0.0 and
  Android Emulator 36.6.11.0.
- Android SDK Command-line Tools 22.0. The emitted `sdkmanager` deprecation
  warning is informational; the command exits successfully.
- One ARM64 Google Play Android Virtual Device is configured.
- Emulator acceleration through Hypervisor.Framework is operational.
- Android Gradle wrapper 9.5.0.
- Python 3.12.13 through `python`, `python3` and `python3.12`.
- Node.js 24.18.0 LTS (Krypton), npm 11.16.0 and Codex CLI 0.144.6.
- Docker CLI 29.1.3 and Docker daemon/server 29.1.3.

Check results:

- `bash -n scripts/verify-development-environment.sh`: exit 0.
- `./scripts/verify-development-environment.sh`: exit 0 with all checks passing.
- Required checks: `python --version`, `docker --version`, `node --version` and
  `codex --version` all exit 0.
- Additional runtime checks: `python3 --version`, `python3.12 --version`,
  `node -p "process.release.lts"` and `npm --version` all exit 0.
- `docker info`: exit 0 with Docker server 29.1.3.
- Android checks: `sdkmanager --version`, `emulator -list-avds`, `adb version`
  and emulator `-accel-check` all exit 0.
- `./android/gradlew --version`: exit 0 with Gradle 9.5.0 on JDK 21.
- `git diff --check`: exit 0.

The version checks and repository script were run through a configured
interactive login zsh so the documented shell-profile `PATH` entries were
loaded.

No physical Android device was attached during the audit. T001 verifies the
development tools and emulator; a real device is still required later for GPS
and microphone behavior testing, but it is not a T001 blocker.
