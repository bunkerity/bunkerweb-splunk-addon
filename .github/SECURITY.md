# Security policy

Even though this project is focused on security, it is still prone to possible vulnerabilities. We consider every security bug as a serious issue and will try our best to address it.

## Responsible disclosure

Report a suspected vulnerability privately, by either route:

- [Report it through a GitHub security advisory](https://github.com/bunkerity/bunkerweb-splunk-addon/security/advisories/new) on this repository.
- Send an email to security \[@\] bunkerity.com (using a ProtonMail if possible) with technical details.

Do not open a public issue for an undisclosed vulnerability. Do not include credentials, Splunk tokens or customer log data in a report: anonymize event samples first.

Only the latest release and the current `main` branch are supported. Upgrade to the latest release before asking for a fix for an older version.

Here is a non-exhaustive list of issues we consider as high risk:

- Vulnerability in the add-on configuration (for example a regular expression that lets crafted log lines break event parsing or take over a search-time field)
- A change that causes the add-on to expose or mislabel security events in the CIM data models
- Vulnerability in a third-party development dependency
- Risk in the supply chain (release artifacts, workflows, pinned actions)

## Scope

This repository holds only Splunk configuration (`props.conf`, `eventtypes.conf`, `tags.conf` and related files), tests and release tooling. It ships no executable code inside the add-on package. Vulnerabilities in BunkerWeb itself belong to [the BunkerWeb security policy](https://github.com/bunkerity/bunkerweb/security/policy); vulnerabilities in Splunk belong to Splunk.

## Bounty

To encourage responsible disclosure, we may reward you with a bounty at the sole discretion of the maintainers.
