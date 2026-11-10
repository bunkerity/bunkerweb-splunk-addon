# Changelog

## v1.0.0 - 2026/11/10

- [FEATURE] Add the `bunkerweb:access`, `bunkerweb:error` and `bunkerweb:modsec_audit` sourcetypes with timestamps, line breaking and search-time field extraction.
- [FEATURE] Map access and audit events to the CIM Web and Intrusion Detection data models, with the `web`, `ids` and `attack` tags.
- [FEATURE] Add a live test that installs the package on a pinned Splunk Enterprise container, ingests `samples/` and asserts the extracted and CIM fields.
- [BUGFIX] Wait for container bootstrap and the authenticated management API before installing the app or continuing after a restart in the live test.
- [MISC] Check pull requests with pre-commit, Splunk AppInspect and the Plumber CI/CD gate; analyze them with CodeQL.
- [MISC] Publish tagged releases from a protected environment, with a `SHA256SUMS` file, a CycloneDX SBOM and signed build provenance.
