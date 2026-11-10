## Summary

<!-- What changed and why? -->

## Related issue

<!-- Use "Fixes #123", "Refs #123", or explain why no issue is needed. -->

## Validation

<!-- List the exact commands run and their results: pre-commit, AppInspect, tests/run.sh. -->

- [ ] `pre-commit run --all-files` passes.
- [ ] AppInspect (`--mode precert`) reports no failure on the built package.
- [ ] `tests/run.sh` passes against the pinned Splunk image, or the change cannot affect ingestion.
- [ ] The three sourcetype names and the `LOG_FORMAT_1` field names are unchanged, or the BunkerWeb docs change in step.
- [ ] No credentials, tokens or unanonymized customer log data are included.

## Documentation and changelog

<!-- List updates, or state why none are needed. -->
