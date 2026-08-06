---
id: T080
title: Implement Room full-text search
status: done
depends_on: [T035]
area: android
---

# Goal

Add FTS indexes for POI aliases, dishes and categories with Vietnamese normalization.

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

- [x] Search works offline.
- [x] No search outside active package.
- [x] Ranking is deterministic.
- [x] Relevant tests are added or updated.
- [x] Required checks pass or failures are documented.
- [x] `docs/context/12-progress-tracker.md` is updated.

# Required checks

```bash
./gradlew test
```

# Expected evidence

- Concise summary.
- Exact files changed.
- Test/check output.
- Known limitations.

# Completion record (2026-08-06)

- Room moved exactly once from version 3 to version 4. The exported contentless
  FTS4 index uses `unicode61` and contains only canonical POI names, aliases,
  menu dish names, raw categories and localized Vietnamese category labels.
  Explicit migration 3→4 backfilled the index while preserving T071 account
  keys, saved snapshots, ordered items, revisions, sync/conflict/deletion state
  and foreign keys. No destructive migration fallback was added.
- Search remains Android-local, active-package scoped and independent of
  Firebase authentication. It has no backend, provider, OpenAI, analytics,
  telemetry or logging dependency. The query compiler treats punctuation,
  quotes, wildcard characters and operator-like input as controlled data, and
  ranking remains deterministic by distance, normalized display name and
  stable POI ID. Canonical updates, deletes and package replacement remove stale
  index rows.
- Automated validation passed 253/253 JVM tests and 140/140 connected tests
  with zero failures, errors or skips. The focused migration, search and package
  instrumentation run passed 18/18. `./gradlew test`, `lintDebug`,
  `testDebugUnitTest`, `assembleDebug`, exported-schema validation and source-
  policy checks passed. Backend, T090 and T091 remained untouched.
- Emulator validation passed active-package blank search; airplane-mode and
  Wi-Fi-disabled search; offline cold start and force-stop/relaunch; accented
  and unaccented name, alias and dish search; raw/localized category search;
  punctuation/operator safety; localized no-result state; deterministic order;
  canonical detail navigation; and controlled production package replacement.
  Old terms disappeared and replacement alias/dish terms remained searchable
  offline after relaunch. T016, T019 and T071 regression observations passed,
  and search triggered no itinerary operation or analytics event.
- Android Studio Network Inspector confirmed that explicit Emulator search
  actions created no app-process HTTP, Firebase-token, backend or provider
  request. The nonempty Emulator process-only privacy scan passed.
- The same offline flow passed on nubia NX721J serial `320143952923`, including
  blank/nonblank active-package search, accented/unaccented name, alias, dish
  and category input, punctuation/operator safety, no-result behavior,
  canonical detail navigation, airplane-mode/Wi-Fi-disabled cold start and
  relaunch, stale-index removal and deterministic ordering. The search-generated
  network-request check and process privacy gate passed.
- Stable PID/UID-scoped capture emitted zero app log records; independent
  source-policy and nonempty Emulator scans confirmed absence of sensitive
  logging. Network Inspector independently confirmed the absence of search-
  generated app requests. No production log was added to manufacture evidence.
- Cleanup restored airplane mode off and Wi-Fi on, removed the temporary HTTP
  proxy and all ADB reverse mappings, and removed temporary package hosting and
  artifacts. Manual validation changed no repository file, introduced no
  secret, and required no OpenAI model, endpoint or API key.
- The accepted scope remains full-text search within the active downloaded HCMC
  package. No query-length or result-count cap was invented. T071 retains saved-
  itinerary ownership; T090 owns future analytics and T091 owns end-to-end demo
  tests.
