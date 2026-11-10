BunkerWeb Add-on for Splunk (TA-bunkerweb) 1.0.0
================================================

Official add-on of the BunkerWeb project, by Bunkerity.
  BunkerWeb documentation: https://docs.bunkerweb.io
  BunkerWeb source:        https://github.com/bunkerity/bunkerweb
  This add-on:             https://github.com/bunkerity/bunkerweb-splunk-addon
License: Apache-2.0 (LICENSES/LICENSE)

What it does
------------
Gives Splunk three sourcetypes for BunkerWeb (1.6.17 and later), with search-time field
extraction and Common Information Model (CIM 6.x) mappings:

  bunkerweb:access         key=value access log        CIM Web; blocked requests also Intrusion Detection
  bunkerweb:error          nginx error log             fields only (plugin denials, bans, ModSecurity lines)
  bunkerweb:modsec_audit   ModSecurity JSON audit log  CIM Intrusion Detection

Install
-------
Install the app on the search head and on the indexers (or the heavy forwarder that parses
the data). A Universal Forwarder needs only the inputs below; it does not need this app.
There is nothing to configure in the app.

BunkerWeb side (variables, for the access log format and the audit log)
-----------------------------------------------------------------------
  ACCESS_LOG_1=/var/log/bunkerweb/access-splunk.log
  LOG_FORMAT_1=time=$time_iso8601 host=$host client=$remote_addr request_id=$request_id method=$request_method uri="$request_uri" status=$status bytes=$body_bytes_sent ua="$http_user_agent" reason=$reason modsec_rules="$modsecurity_rules" modsec_score=$modsecurity_anomaly_score modsec_id=$modsecurity_unique_id
  MODSECURITY_SEC_AUDIT_LOG_PARTS=BFH
  custom config of type modsec (configs/modsec/audit-json.conf):  SecAuditLogFormat JSON

Universal Forwarder inputs.conf
-------------------------------
  [monitor:///var/log/bunkerweb/access-splunk.log]
  sourcetype = bunkerweb:access
  index = <your index>

  [monitor:///var/log/bunkerweb/error.log]
  sourcetype = bunkerweb:error
  index = <your index>

  [monitor:///var/log/bunkerweb/modsec_audit.log]
  sourcetype = bunkerweb:modsec_audit
  index = <your index>

The complete guide, the field and CIM table and the test suite are in the repository README.
