# Repository Guidelines

This is the canonical agent guide. `CLAUDE.md` imports it; edit this file when project guidance changes.

## Purpose and layout

`bunkerity/bunkerweb-splunk-addon` is the official BunkerWeb add-on for Splunk (`TA-bunkerweb`). It gives the BunkerWeb access log, error log and ModSecurity JSON audit log sourcetypes, timestamps, search-time field extraction and CIM mappings (Web, Intrusion Detection). BunkerWeb needs no code for this: the add-on is Splunk configuration only. It is licensed Apache-2.0.

- `TA-bunkerweb/`: the app (`default/{app,props,transforms,eventtypes,tags}.conf`, `metadata/default.meta`, `app.manifest`, `README.txt`, `LICENSES/`). It ships no executable code.
- `samples/`: real BunkerWeb events (IPs anonymized to documentation ranges). Captured bytes are test data: never reformat or normalize them.
- `tests/`: `run.sh` (live Splunk test), `splunk.sh` (throwaway container), `lib.sh`, `test_ta.py` (field and CIM assertions), `capture/` (the BunkerWeb stack that produced `samples/`).
- `package.sh`: builds `dist/TA-bunkerweb-<version>.tgz`.
- `.github/`: workflows (`tests.yml`, `plumber.yml`, `codeql.yml`, `scorecard.yml`, `release.yml`), `scripts/release_check.py`, issue and PR templates, `SECURITY.md`, `CODEOWNERS`, `dependabot.yml`, `plumber/README.md`.
- `.pre-commit-config.yaml`, `pyproject.toml`, `requirements-dev.txt`, `.gitattributes`, `.plumber.yaml`: tooling. `pyproject.toml` declares development tools only; this repository ships no Python package.

## Project profile

| Item                | Value                                                                                                                                                                                                    |
| ------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Languages           | Splunk `.conf` files, shell (`package.sh`, `tests/*.sh`), Python 3.11+ (`tests/test_ta.py`, `.github/scripts/`, standard library only)                                                                   |
| Supported BunkerWeb | 1.6.17 and later. Samples come from `1.6.18-rc3`. To confirm against the final README before release                                                                                                     |
| Supported Splunk    | Tested on Splunk Enterprise 10.2.9 (the image digest is pinned in `tests/splunk.sh`). CIM field names 6.x (`app.manifest` declares Web and Intrusion Detection 6.0.0). Other Splunk versions: to confirm |
| Architectures       | Configuration only, so platform independent. The live test runs on linux/amd64                                                                                                                           |
| Artifact            | `TA-bunkerweb-<version>.tgz` (one top-level `TA-bunkerweb/` directory, deterministic bytes), plus `SHA256SUMS`, a CycloneDX SBOM, and signed build provenance on tagged releases                         |
| Distribution        | [Splunkbase app 10342](https://splunkbase.splunk.com/app/10342), listed since v1.0.1 (2026-11-10). The GitHub repository homepage points to the listing                                                  |
| Functional checks   | Splunk AppInspect `--mode precert` (offline, no Docker); live ingest test `tests/run.sh` (Docker, `splunk/splunk`, about 5 GiB free memory)                                                              |
| Release path        | Signed `vX.Y.Z` tag, `release.yml` (tests reused, package attested, `release` environment approval, GitHub release). Splunkbase upload is manual: see `CONTRIBUTING.md`                                  |

The repository is public. Scorecard runs only on public repositories; CodeQL runs on public repositories or when `CODEQL_PRIVATE` is `true`. Both workflows run for this repository. CodeRabbit may review this public code; its configuration has not been verified.

### Accepted exceptions

- **No fuzzing.** There is no parser code beyond Splunk's own configuration engine. The regular expressions in `props.conf` are exercised by the live test on real samples.
- **No mypy, no pytest, no coverage gate.** The only Python is one assertion script run end to end by `tests/run.sh` (its exit code is the gate) and one small release script covered by `unittest`. A strict-typing and coverage threshold would measure scaffolding, not the add-on. The coverage that matters is the field and CIM assertion list in `tests/test_ta.py`. There is no Codecov integration because there is no coverage gate.
- **The live Splunk test is opt-in in CI.** It runs when the repository variable `RUN_SPLUNK_TESTS` is `true`, because it accepts Splunk's license and general terms for the throwaway container. Releases require it.
- **Local hooks use the POSIX `.venv/bin/python` path.** Windows contributors need `.venv/Scripts/python.exe` in their copy of the Black and Ruff entries.
- **Dependabot cannot see the Splunk image** pinned in `tests/splunk.sh` (neither a Dockerfile nor a compose file). Bump it by hand and record the new digest.
- **Prettier skips** `CHANGELOG.md`, `CODE_OF_CONDUCT.md`, `CONTRIBUTING.md`, `README.md`, `.github/SECURITY.md` and `TA-bunkerweb/`, as BunkerWeb's own `.prettierignore` does for the shared names.

## Invariants

- **The three sourcetype names are a contract**: `bunkerweb:access`, `bunkerweb:error`, `bunkerweb:modsec_audit`. The BunkerWeb documentation (`docs/advanced.md`, Splunk section, in `bunkerity/bunkerweb`) and users' Universal Forwarder `inputs.conf` use them. Never rename one.
- **The `LOG_FORMAT_1` field names are a contract** with the same documentation: `time`, `host`, `client`, `request_id`, `method`, `uri`, `status`, `bytes`, `ua`, `reason`, `modsec_rules`, `modsec_score`, `modsec_id`. A change here needs a matching change in BunkerWeb's docs, a changelog entry and a new add-on version.
- `reason` is the BunkerWeb plugin id that denied a request (empty for a ModSecurity block); `modsec_id` equals the audit entry's `unique_id`. Map only what the events carry.
- Search-time extraction by default; index-time settings only for timestamp and line breaking.
- The version lives in `TA-bunkerweb/default/app.conf` (`[launcher]` and `[id]`) and `TA-bunkerweb/app.manifest`. `release_check.py` requires them, the tag and the top `CHANGELOG.md` section to agree.
- `package.sh` copies the root `LICENSE` into the app: the root file is the single source.
- Never commit credentials, Splunk passwords, tokens, `.env` files, `.venv/`, `dist/` or `.cache/`. Anonymize IPs, host names and tokens in anything added to `samples/` or an issue.
- Docker objects created by the tests carry the `splta-` prefix. Never prune, and never touch containers you did not create.

## Development and verification

Use a repository-local virtual environment with Python 3.11 or newer:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install --require-hashes -r requirements-dev.txt
.venv/bin/pre-commit install            # once per checkout
.venv/bin/pre-commit run --all-files    # trailing whitespace, EOF, YAML, ShellCheck, Gitleaks, Black, Ruff, Prettier
./package.sh                            # prints dist/TA-bunkerweb-<version>.tgz
.venv/bin/splunk-appinspect inspect dist/TA-bunkerweb-*.tgz --mode precert
python3 -I -m unittest discover -s .github/scripts
tests/run.sh                            # live test: Docker, curl, python3, about 5 GiB free memory
SPLTA_SABOTAGE=1 tests/run.sh           # must fail: proves the assertions can fire
```

Black uses line length 160; Ruff selects `E,F,I,UP,B`. `pre-commit run --all-files` walks the Git index: stage new files first, or use `pre-commit run --files <paths>`. Run `actionlint` (pinned release binary) after editing a workflow.

AppInspect: zero failures and zero errors gate CI. Read every warning and decide; do not suppress one without a reason in the PR.

The lock is generated from `pyproject.toml`, never edited by hand:

```sh
uv pip compile pyproject.toml --extra dev --universal --python-version 3.11 --generate-hashes --output-file requirements-dev.txt
```

Use `--upgrade-package <name>` for a targeted update, and review generated lock changes against the same process.
Dependabot's weekly pip version scan excludes `requirements-dev.txt` and updates the declarations in `pyproject.toml` only. Regenerate the lock with the command above in the same PR before merging a Python dependency update; never merge independent bumps to compiled transitive pins. AppInspect constrains several of them, including `lxml<6`. Dependabot security updates can bypass `exclude-paths`; validate and regenerate those locks too. A dependency conflict is not a resolved security alert.

A test is not coverage until it has failed: when a new assertion or extraction fix lands, run it against the unfixed `props.conf` and keep the failing output. `SPLTA_SABOTAGE=1` does this for the `uri_path` extraction.

## OSS workflows and delivery

Keep external Actions pinned to full commit SHAs with a version comment, checkout credentials disabled, and permissions scoped to each job. Preserve Plumber's upstream policy and failing grade-B gate, explicit binary version and attestation verification; do not weaken a control to obtain a passing score. See `.github/plumber/README.md`. Update `README.md` and `CHANGELOG.md` when behavior changes. Preserve Apache-2.0 licensing. Report vulnerabilities through `.github/SECURITY.md`.

Repository configuration files do not prove live GitHub settings (rulesets, the `release` environment and its reviewers, private vulnerability reporting, Dependabot alerts, repository variables). Check those separately.

Preserve unrelated work. Never create a git commit; stage only authorized paths and leave the commit to the maintainer. Do not push, publish (GitHub or Splunkbase), change repository visibility or settings, or post externally without explicit task authorization.

Codex sessions prefix shell commands with `rtk` and use `python3` on the host. Keep user-facing reports concise; code, documentation and proposed commit messages use normal English.
