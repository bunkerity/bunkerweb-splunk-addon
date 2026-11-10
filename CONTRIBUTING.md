# Contributing to the BunkerWeb add-on for Splunk

Thanks for being here. Before getting started, read [AGENTS.md](AGENTS.md) for the repository layout, tooling and invariants.

## Reporting bugs and asking for features

Use [issues](https://github.com/bunkerity/bunkerweb-splunk-addon/issues) and fill the "Bug report" or "Feature request" template. Include the BunkerWeb, add-on and Splunk versions, your `LOG_FORMAT_1` setting and a few raw events, with IP addresses, host names and tokens anonymized. Report vulnerabilities through the [security policy](.github/SECURITY.md), never in a public issue.

For a substantial change, open an issue first so we can agree on it before you spend time on a pull request.

## Development setup

```sh
python3 -m venv .venv
.venv/bin/python -m pip install --require-hashes -r requirements-dev.txt
.venv/bin/pre-commit install
```

Hooks cover whitespace, final newlines, YAML, ShellCheck, Gitleaks, Black (160 columns), Ruff and Prettier. The Black and Ruff hooks use the POSIX path `.venv/bin/python`; on Windows use `.venv/Scripts/python.exe` in your copy of `.pre-commit-config.yaml`. Run `.venv/bin/pre-commit run --all-files` before opening a pull request. Hooks do not replace the checks below or CI.

## Checks

```sh
./package.sh
.venv/bin/splunk-appinspect inspect dist/TA-bunkerweb-*.tgz --mode precert
tests/run.sh
```

`tests/run.sh` starts a pinned `splunk/splunk` container, installs the package, indexes `samples/` and asserts the extracted and CIM fields. It needs Docker, `curl`, `python3` and about 5 GiB of free memory. It starts Splunk with the Splunk license and general terms accepted for that throwaway container, so read them before you run it. `SPLTA_SABOTAGE=1 tests/run.sh` breaks one extraction on purpose and must fail.

Fix an extraction bug by first adding the sample event and the assertion that fails on the unfixed `props.conf`, then make it pass. Keep the output of the failing run. Anonymize every new sample: documentation IP ranges (`192.0.2.0/24`, `198.51.100.0/24`, `203.0.113.0/24`), no real host names, no tokens.

Never rename the three sourcetypes (`bunkerweb:access`, `bunkerweb:error`, `bunkerweb:modsec_audit`) or the `LOG_FORMAT_1` field names: they are a contract with the BunkerWeb documentation. A change to either needs a matching documentation change, a changelog entry and a new version.

## Pull requests

Submit changes as pull requests, including maintainer changes. A maintainer other than the author reviews each change before merging. Re-request review after changing reviewed code, and do not use administrator bypass for routine work. Repository settings determine the enforced approval count and required checks.

CI runs pre-commit, Gitleaks, the package build with AppInspect, the Plumber CI/CD gate, CodeQL (where code scanning is available) and, when enabled, the live Splunk test. Resolve findings before merging; treat new warnings as defects to investigate rather than suppress.

Update `README.md` and `CHANGELOG.md` when behavior changes. Contributions are licensed under Apache-2.0.

## Releases

Maintainers only.

1. Set the new version in `TA-bunkerweb/default/app.conf` (`[launcher]` and `[id]`) and `TA-bunkerweb/app.manifest`. Replace the `????/??/??` date of the top `CHANGELOG.md` section (`## vX.Y.Z - YYYY/MM/DD`).
2. Merge through a pull request with all checks green.
3. Create a signed, annotated tag on the tested commit and push it: `git tag -s -a vX.Y.Z -m "vX.Y.Z"`, then `git push origin vX.Y.Z`.
4. `release.yml` checks that the tag, the add-on version and the top changelog section agree, reuses `tests.yml`, builds the package once, writes `SHA256SUMS`, generates a CycloneDX SBOM with Trivy, attests the files and exports the signed provenance and Sigstore bundle. A required reviewer then approves the `release` environment; the workflow rechecks the reviewers and GitHub's tag-signature verification before it uploads the assets to a draft release and publishes it. A published release is immutable: fix a mistake with a new version.
5. Releases need the repository variable `RUN_SPLUNK_TESTS` set to `true`, so the live test has passed on the tagged commit.
6. **Splunkbase upload is manual.** Download `TA-bunkerweb-X.Y.Z.tgz` from the release, check it against `SHA256SUMS` (and the attestation with `gh attestation verify TA-bunkerweb-X.Y.Z.tgz --repo bunkerity/bunkerweb-splunk-addon`), then upload that same file on Splunkbase. Do not rebuild it.
