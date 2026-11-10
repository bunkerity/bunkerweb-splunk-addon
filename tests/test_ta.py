#!/usr/bin/env python3
"""Assert the TA-bunkerweb extractions and CIM fields on events indexed from samples/.

Environment: SPLTA_URL (management URL), SPLTA_PASSFILE, SPLTA_INDEX.
Exit code 0 when every check passes, 1 otherwise. Standard library only.
"""

import base64
import calendar
import csv
import io
import json
import os
import re
import ssl
import sys
import time
import urllib.parse
import urllib.request

URL = os.environ.get("SPLTA_URL", "https://127.0.0.1:19089")
INDEX = os.environ["SPLTA_INDEX"]
with open(os.environ["SPLTA_PASSFILE"], encoding="utf-8") as fh:
    AUTH = "Basic " + base64.b64encode(("admin:" + fh.read().strip()).encode()).decode()
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
SAMPLES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "samples")

FAILS = []
CHECKS = 0


def search(spl):
    """Run a search over all time and return the rows as a list of dicts."""
    if not spl.lstrip().startswith("|"):
        spl = "search " + spl
    body = urllib.parse.urlencode({"search": spl, "earliest_time": "0", "output_mode": "csv"}).encode()
    req = urllib.request.Request(URL + "/services/search/jobs/export", data=body, headers={"Authorization": AUTH})
    with urllib.request.urlopen(req, context=CTX, timeout=180) as resp:
        text = resp.read().decode("utf-8")
    if text.lstrip().startswith("<?xml"):
        raise RuntimeError("search failed: " + text[:400])
    return list(csv.DictReader(io.StringIO(text)))


def first(spl):
    """First row of a search, or an empty row."""
    rows = search(spl)
    return rows[0] if rows else {}


def check(name, ok, detail: object = ""):
    global CHECKS
    CHECKS += 1
    if ok:
        print("PASS  " + name)
    else:
        FAILS.append(name)
        print("FAIL  " + name + ("  -> " + str(detail) if detail else ""))


def one(spl):
    rows = search(spl)
    return rows[0] if len(rows) == 1 else {"__rows__": str(len(rows))}


def mv(value):
    """CSV export joins multivalue fields with newlines."""
    return [v for v in value.split("\n") if v] if value else []


def fields(row, expected):
    """Compare a row with {field: expected}; a list means a multivalue field, None means empty."""
    bad = {}
    for key, want in expected.items():
        got = row.get(key, "")
        if isinstance(want, list):
            got = mv(got)
        elif want is None:
            want, got = "", got or ""
        if got != want:
            bad[key] = (want, got)
    return bad


def sample_lines(name):
    with open(os.path.join(SAMPLES, name), encoding="utf-8") as fh:
        return [line.rstrip("\n") for line in fh if line.strip()]


def epoch(iso):
    return calendar.timegm(time.strptime(iso, "%Y-%m-%dT%H:%M:%S"))


IDX = "index=" + INDEX
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"

# ---------------------------------------------------------------- expectations from the raw samples
captured_access = sample_lines("access.log")
access = captured_access + sample_lines("access_adversarial.log")
captured_error = sample_lines("error.log")
error = captured_error + sample_lines("error_adversarial.log")
audit = [json.loads(line) for line in sample_lines("modsec_audit.log")]
n_blocked_access = sum(
    1
    for line in captured_access
    if int(re.search(r" status=(\d+)", line)[1]) >= 400 and (re.search(r" reason=(?!\s)\S", line) or re.search(r' modsec_rules="\s*\d', line))
)
n_blocked_access += 2  # Synthetic plugin and ModSecurity denials; four synthetic requests are allowed.

# ---------------------------------------------------------------- 1. line breaking and counts
for st, lines in (("bunkerweb:access", access), ("bunkerweb:error", error), ("bunkerweb:modsec_audit", audit)):
    got = one(f'{IDX} sourcetype="{st}" | stats count').get("count")
    check(f"{st}: {len(lines)} events, one per line", got == str(len(lines)), got)

longest = max(len(line) for line in error)
got = one(f"{IDX} sourcetype=bunkerweb:error | eval l=len(_raw) | stats max(l) AS m").get("m", "0")
check(f"bunkerweb:error: longest line ({longest} chars) is not truncated", int(got) == longest, got)

# ---------------------------------------------------------------- 2. timestamps
row = one(f'{IDX} sourcetype=bunkerweb:access request_id=* uri_path="/login" | eval e=_time | table e')
check("access: _time from time=<iso8601>", row.get("e", "").split(".")[0] == str(epoch("2026-11-10T08:14:19")), row)
row = one(f'{IDX} sourcetype=bunkerweb:error modsec_id="17942984718.939014" modsec_verdict="Access denied" | eval e=_time | table e')
check("error: _time from YYYY/MM/DD HH:MM:SS", row.get("e", "").split(".")[0] == str(epoch("2026-11-10T08:14:31")), row)
row = one(f'{IDX} sourcetype=bunkerweb:modsec_audit modsec_id="17942984718.939014" | eval e=_time | table e')
check("audit: _time from transaction.time_stamp", row.get("e", "").split(".")[0] == str(epoch("2026-11-10T08:14:31")), row)

# ---------------------------------------------------------------- 3. access fields and CIM Web
Q = f"{IDX} sourcetype=bunkerweb:access"
COLS = (
    "| table site dest src http_method uri_path uri_query status bytes_out http_user_agent action reason signature "
    "signature_id category ids_type vendor product vendor_product modsec_rules modsec_score modsec_id"
)

bad = fields(
    one(f'{Q} uri_path="/login" {COLS}'),
    {
        "site": "www.example.com",
        "dest": "www.example.com",
        "src": "203.0.113.45",
        "http_method": "POST",
        "uri_path": "/login",
        "uri_query": None,
        "status": "404",
        "bytes_out": "69298",
        "http_user_agent": UA,
        "action": "allowed",
        "reason": None,
        "signature": None,
        "category": None,
        "ids_type": None,
        "vendor": "Bunkerity",
        "product": "BunkerWeb",
        "vendor_product": "BunkerWeb",
        "modsec_rules": None,
        "modsec_score": None,
        "modsec_id": None,
    },
)
check("access: allowed request, CIM Web fields", not bad, bad)

bad = fields(one(f'{Q} uri_path="/search" {COLS}'), {"uri_query": "q=hello+world&page=2", "action": "allowed"})
check("access: uri_query split from the path", not bad, bad)

bad = fields(
    first(f'{Q} uri_path="/limited" status=429 | head 1 {COLS}'),
    {
        "status": "429",
        "reason": "limit",
        "action": "blocked",
        "signature": "limit",
        "category": "BunkerWeb plugin",
        "ids_type": "application",
        "signature_id": None,
        "modsec_id": None,
    },
)
check("access: limit plugin block, CIM Intrusion Detection fields", not bad, bad)
check("access: 3 limit blocks", len(search(f"{Q} reason=limit")) == 3)

bad = fields(one(f"{Q} reason=blacklist {COLS}"), {"status": "403", "action": "blocked", "signature": "blacklist", "category": "BunkerWeb plugin"})
check("access: blacklist plugin block", not bad, bad)

rows = search(f'{Q} uri_path="/gone1" {COLS}')
bad = (
    fields(rows[0], {"reason": "bad behavior", "signature": "bad behavior", "action": "blocked", "status": "403"})
    if len(rows) == 1
    else {"rows": str(len(rows))}
)
check("access: reason with a space is kept whole (bad behavior)", not bad, bad)

bad = fields(
    one(f'{Q} uri_path="/blocked-xss" {COLS}'),
    {
        "status": "403",
        "action": "blocked",
        "reason": None,
        "category": "ModSecurity",
        "ids_type": "application",
        "signature": ["941100", "941110", "941160", "941390"],
        "signature_id": ["941100", "941110", "941160", "941390"],
        "modsec_rules": ["941100", "941110", "941160", "941390"],
        "modsec_score": "20",
        "modsec_id": "17942984718.939014",
        "uri_query": "q=%3Cscript%3Ealert(1)%3C/script%3E",
    },
)
check("access: ModSecurity block, rule ids as multivalue, score, id", not bad, bad)

bad = fields(one(f'{Q} uri_path="/products" {COLS}'), {"modsec_rules": ["942100"], "modsec_score": "5", "action": "blocked"})
check("access: single-rule ModSecurity block", not bad, bad)

bad = fields(
    one(f'{Q} uri_path="/download" {COLS}'),
    {
        "modsec_rules": ["930100", "930110", "930120", "932160"],
        "signature": ["930100", "930110", "930120", "932160"],
        "signature_id": ["930100", "930110", "930120", "932160"],
        "category": "ModSecurity",
        "modsec_score": "30",
    },
)
check("access: repeated rule ids are deduplicated", not bad, bad)
check(
    "access: ModSecurity or plugin is decided by modsec_id, never by reason",
    len(search(f"{Q} category=ModSecurity")) == 7 and len(search(f'{Q} category="BunkerWeb plugin"')) == n_blocked_access - 7,
)

row = one(f'{Q} uri_path="/esc" {COLS}')
check(
    "access: nginx \\xHH escapes survive in quoted values",
    row.get("http_user_agent", "").startswith("Mozilla/5.0 \\x22quoted\\x22 caf\\xC3\\xA9") and "\\x22b\\x22" in row.get("uri_query", ""),
    row,
)

check(
    "access: the virtual host goes to site/dest, not to the Splunk host field",
    len(search(f'{Q} uri_path="/login" | where host="splta-test" AND dest="www.example.com"')) == 1,
)
check("access: scheduler API calls (host=bwapi) are plain Web events", len(search(f"{Q} dest=bwapi action=allowed")) >= 1)
check(f"access: {n_blocked_access} blocked events by action", len(search(f"{Q} action=blocked")) == n_blocked_access, len(search(f"{Q} action=blocked")))

# Synthetic adversarial lines: field-like request data must never become denial metadata.
for request_id in ("crspl-ua-reason", "crspl-ua-id", "crspl-uri-reason", "crspl-uri-id", "crspl-plugin", "crspl-modsec"):
    expected = {
        "site": "www.example.com",
        "dest": "www.example.com",
        "src": "203.0.113.45",
        "status": "403",
        "http_method": "GET",
        "bytes_out": "42",
        "action": "allowed",
        "reason": None,
        "modsec_id": None,
        "modsec_rules": None,
        "modsec_score": None,
        "signature": None,
        "signature_id": None,
        "category": None,
        "ids_type": None,
        "uri_path": "/" + request_id,
    }
    if request_id == "crspl-plugin":
        expected.update(action="blocked", reason="bad behavior", signature="bad behavior", category="BunkerWeb plugin", ids_type="application")
    elif request_id == "crspl-modsec":
        expected.update(
            action="blocked",
            modsec_id="crspl-real-id",
            modsec_rules=["942100"],
            modsec_score="5",
            signature=["942100"],
            signature_id=["942100"],
            category="ModSecurity",
            ids_type="application",
        )
    bad = fields(one(f'{Q} request_id="{request_id}" {COLS}'), expected)
    check(f"access: quoted field spoofing {request_id} preserves actual fields and verdict", not bad, bad)

# ---------------------------------------------------------------- 4. error log
Q = f"{IDX} sourcetype=bunkerweb:error source=error.log"
row = one(f"{Q} bw_plugin=blacklist | table log_level bw_component bw_plugin bw_message src dest http_method uri_path http_host pid")
bad = fields(
    row,
    {
        "log_level": "warn",
        "bw_component": "ACCESS",
        "bw_plugin": "blacklist",
        "src": "203.0.113.45",
        "dest": "www.example.com",
        "http_method": "GET",
        "uri_path": "/blocked-by-blacklist/x",
        "http_host": "www.example.com",
        "bw_message": "URI is blacklisted (info : URI ^/blocked-by-blacklist)",
    },
)
check("error: denied access from <plugin> (blacklist)", not bad, bad)
check("error: denied access from limit (3 lines)", len(search(f"{Q} bw_plugin=limit")) == 3)
rows = search(f'{Q} bw_ban_reason=* uri_path="/after-ban" | table bw_ban_ip bw_ban_reason bw_ban_ttl src')
bad = fields(rows[0], {"bw_ban_ip": "203.0.113.45", "bw_ban_reason": "bad behavior", "src": "203.0.113.45"}) if len(rows) == 1 else {"rows": str(len(rows))}
check("error: IP is banned with reason <r> (<ttl>s remaining)", not bad and float(rows[0]["bw_ban_ttl"]) > 3000, rows)
check(
    "error: every ban line is extracted",
    len(search(f'{Q} bw_ban_reason="bad behavior"')) == sum(1 for line in captured_error if "is banned with reason" in line),
)
rows = search(f'{Q} modsec_verdict="Access denied" | table modsec_http_code modsec_phase modsec_rule_id modsec_id crs_version src uri_path')
check(
    "error: ModSecurity Access denied lines carry 949110 and the unique_id",
    len(rows) == 6
    and all(
        r["modsec_rule_id"] == "949110"
        and r["modsec_http_code"] == "403"
        and r["modsec_phase"] == "2"
        and r["crs_version"] == "OWASP_CRS/4.30.0"
        and r["modsec_id"]
        for r in rows
    ),
    rows[:1],
)
rows = search(f'{Q} modsec_verdict=Warning modsec_rule_id=941100 modsec_id="17942984718.939014" | table modsec_msg modsec_severity modsec_id')
check(
    "error: ModSecurity Warning line (rule 941100)",
    len(rows) == 1
    and rows[0]["modsec_msg"] == "XSS Attack Detected via libinjection"
    and rows[0]["modsec_severity"] == "2"
    and rows[0]["modsec_id"] == "17942984718.939014",
    rows,
)

# Synthetic error envelopes retain only metadata from the trusted message prefix.
ERROR_FIELDS = (
    "bw_component bw_plugin bw_message bw_ban_ip bw_ban_reason bw_ban_ttl modsec_verdict modsec_http_code "
    "modsec_phase modsec_rule_id modsec_msg modsec_severity modsec_id crs_version"
)
actual_rule = {"modsec_rule_id": "942100", "modsec_msg": "Actual rule", "modsec_severity": "2", "modsec_id": "crerr-real", "crs_version": "OWASP_CRS/4.30.0"}
actual_denial = {"modsec_verdict": "Access denied", "modsec_http_code": "403", "modsec_phase": "2"}
for connection, trusted in (
    (9001, {}),  # Unescaped request line, including raw quotes.
    (9002, {}),  # Referrer.
    (9003, {}),  # Host.
    (9004, {}),  # Upstream.
    (9005, {"bw_component": "ACCESS"}),
    (9006, {"bw_component": "API"}),
    (9007, {"bw_component": "ACCESS", "bw_plugin": "bad behavior", "bw_message": "actual denial"}),
    (9008, {"bw_component": "ACCESS", "bw_ban_ip": "203.0.113.45", "bw_ban_reason": "bad behavior", "bw_ban_ttl": "35.5"}),
    (9009, {"bw_component": "ACCESS", "bw_ban_ip": "203.0.113.45", "bw_ban_reason": "limit", "bw_ban_ttl": "15"}),
    (9010, {"modsec_verdict": "Warning", **actual_rule}),  # Real ModSecurity \xHH escaping in data.
    (9011, {"modsec_verdict": "Warning"}),  # Raw quoted metadata inside data, no real id or msg.
    (9012, {"modsec_verdict": "Warning"}),  # Missing details must not be filled from the suffix.
    (9013, {**actual_denial, **actual_rule}),
    (
        9014,
        {
            "bw_component": "ACCESS",
            "bw_plugin": "limit",
            "bw_message": 'URL contains ModSecurity: Access denied with code 451 (phase 4). [id "999999"] [msg "forged"]',
        },
    ),
    (9015, {"modsec_verdict": "Warning"}),  # Decoded URI with raw quotes: ambiguous metadata.
    (9016, {"modsec_verdict": "Warning"}),  # Duplicate metadata blocks: ambiguous origin.
    (9017, {"modsec_verdict": "Warning", **actual_rule}),  # Fake fields in the match's Value text.
    (9018, {"modsec_verdict": "Warning"}),  # Unescaped quotes in a macro-expanded msg.
    (9019, {"modsec_verdict": "Warning"}),  # Fake severity inside data, actual severity missing.
    (9020, {"modsec_verdict": "Warning"}),  # Raw quotes in hostname.
    (9021, {"bw_component": "ACCESS", "bw_plugin": "blacklist", "bw_message": "no request context"}),
    (9022, {**actual_denial, **actual_rule}),  # Valid message without nginx's request suffix.
    (9023, actual_denial),  # Decoded URI forges a complete metadata tail and nginx client boundary.
    (9024, actual_denial),  # Raw quotes in the request suffix make the metadata boundary ambiguous.
    (9025, {**actual_denial, **actual_rule}),  # A client-like substring inside a quoted URI is not nginx context.
):
    expected = dict.fromkeys(ERROR_FIELDS.split())
    expected.update(trusted)
    row = one(f"{IDX} sourcetype=bunkerweb:error source=error_adversarial.log connection={connection} | table connection {ERROR_FIELDS}")
    bad = fields(row, {"connection": str(connection), **expected})
    check(f"error: adversarial envelope {connection} trusts only actual metadata", not bad, bad)

# ---------------------------------------------------------------- 5. ModSecurity audit log
Q = f"{IDX} sourcetype=bunkerweb:modsec_audit"
bad = fields(
    one(
        f'{Q} modsec_id="17942984718.939014" | table src src_port dest dest_ip dest_port http_method uri_path uri_query status '
        "http_user_agent action severity category signature_id signature ids_type vendor product vendor_product"
    ),
    {
        "src": "203.0.113.45",
        "dest": "www.example.com",
        "dest_ip": "198.51.100.3",
        "dest_port": "8080",
        "http_method": "GET",
        "uri_path": "/blocked-xss",
        "uri_query": "q=%3Cscript%3Ealert(1)%3C/script%3E",
        "status": "403",
        "http_user_agent": UA,
        "action": "blocked",
        "severity": "critical",
        "category": ["attack-xss"],
        "ids_type": "application",
        "signature_id": ["941100", "941110", "941160", "941390", "949110"],
        "signature": [
            "XSS Attack Detected via libinjection",
            "XSS Filter - Category 1: Script Tag Vector",
            "NoScript XSS InjectionChecker: HTML Injection",
            "Javascript method detected",
            "Inbound Anomaly Score Exceeded (Total Score: 20)",
        ],
        "vendor": "Bunkerity",
        "product": "BunkerWeb",
        "vendor_product": "BunkerWeb",
    },
)
check("audit: JSON fields mapped to CIM Intrusion Detection", not bad, bad)
rows = search(f"{Q} | stats count by category | sort category")
check(
    "audit: attack categories from the CRS tags",
    {r["category"] for r in rows} >= {"attack-xss", "attack-sqli", "attack-lfi", "attack-rce"},
    [r["category"] for r in rows],
)

# ---------------------------------------------------------------- 6. correlation between the three logs
rows = search(
    f"{IDX} source!=access_adversarial.log source!=error_adversarial.log (sourcetype=bunkerweb:access OR sourcetype=bunkerweb:modsec_audit "
    'OR (sourcetype=bunkerweb:error modsec_verdict="Access denied")) modsec_id=* '
    "| stats dc(sourcetype) AS st count by modsec_id"
)
check("correlation: modsec_id joins access, audit and error for all 6 ModSecurity blocks", len(rows) == 6 and all(r["st"] == "3" for r in rows), rows)

# ---------------------------------------------------------------- 7. CIM: tags, required fields, data models
n_web = len(search(f"{IDX} tag=web"))
check("CIM Web: tag=web covers the access events only", n_web == len(access), n_web)
WEB_REQUIRED = ["action", "src", "dest", "http_method", "http_user_agent", "status", "uri_path", "bytes_out", "vendor_product"]
miss = search(f"{IDX} tag=web | where " + " OR ".join(f"isnull({f})" for f in WEB_REQUIRED) + " | stats count")
check("CIM Web: " + ", ".join(WEB_REQUIRED) + " populated on every event", miss and miss[0]["count"] == "0", miss)
check("CIM Web: action is allowed or blocked", all(r["action"] in ("allowed", "blocked") for r in search(f"{IDX} tag=web | stats count by action")))

n_ids = len(search(f"{IDX} tag=ids tag=attack"))
check(
    f"CIM Intrusion Detection: tag=ids tag=attack = {n_blocked_access} blocked access + {len(audit)} audit entries",
    n_ids == n_blocked_access + len(audit),
    n_ids,
)
IDS_REQUIRED = ["action", "category", "dest", "ids_type", "signature", "src", "vendor_product"]
miss = search(f"{IDX} tag=ids tag=attack | where " + " OR ".join(f"isnull({f})" for f in IDS_REQUIRED) + " | stats count")
check("CIM Intrusion Detection: " + ", ".join(IDS_REQUIRED) + " populated on every event", miss and miss[0]["count"] == "0", miss)
miss = search(f"{IDX} tag=ids tag=attack sourcetype=bunkerweb:modsec_audit | where isnull(severity) OR isnull(signature_id) | stats count")
check("CIM Intrusion Detection: severity and signature_id populated on audit events", miss and miss[0]["count"] == "0", miss)

# Real data models, when the Splunk Common Information Model add-on is installed in the container.
probe = search("| rest /servicesNS/-/-/datamodel/model splunk_server=local count=0 | search title=Web OR title=Intrusion_Detection | table title")
have = {r["title"] for r in probe}
if {"Web", "Intrusion_Detection"} <= have:
    web = search(f"| datamodel Web Web search | search {IDX} | stats count")
    check("data model Web: BunkerWeb access events", web and int(web[0]["count"]) == len(access), web)
    ids = search(f"| datamodel Intrusion_Detection IDS_Attacks search | search {IDX} | stats count")
    check("data model Intrusion_Detection: BunkerWeb blocked events", ids and int(ids[0]["count"]) == n_blocked_access + len(audit), ids)
else:
    print(
        "SKIP  data models Web and Intrusion_Detection: the Splunk Common Information Model add-on is not installed "
        "(Splunkbase download needs a splunk.com login); tag and field checks above stand in for the constraints"
    )

print(f"\n{CHECKS - len(FAILS)}/{CHECKS} checks passed")
sys.exit(1 if FAILS else 0)
