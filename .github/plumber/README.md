# Plumber

The reusable workflow scans GitHub Actions on every PR and main push through `tests.yml`, and weekly on its own schedule. The gate requires grade B or better (`soft-fail: false`). `.plumber.yaml` extends the upstream default policy without disabling controls. Its only change adds `softprops/action-gh-release` to the trusted action sources, because `release.yml` creates the GitHub release with it (pinned to a full commit), the same exception `bunkerity/certbot-dns-hosttech` carries.

Every external action is pinned to a full commit. Plumber's binary version is explicit and its SLSA attestation is verified. The job uploads JSON, SARIF, PBOM and CycloneDX evidence as run artifacts. SARIF upload is off on pull requests. Public score publishing is off on pull requests and private repositories.

CodeQL analyzes Python and GitHub Actions workflows and uploads pull request findings to code scanning; its database upload stays off on pull requests. It runs only on a public repository, or on a private one once the repository variable `CODEQL_PRIVATE` is `true` (code scanning on a private repository needs GitHub Code Security). OpenSSF Scorecard runs on public main pushes, weekly and on branch-protection changes. Dependabot groups weekly updates for GitHub Actions, Python development tools and the capture stack's Docker images.

Local scan results cannot prove hosted permissions, branch protection or public score publishing. Before making this repository public, maintainers must configure main-branch protection, required CI checks, the `release` environment and security features in GitHub. No repository settings are changed by these files.
