#!/usr/bin/env bash
# Sends the probe traffic that produced samples/. Run against tests/capture/compose.yml.
# Allowed requests first, then limit, blacklist, ModSecurity blocks, and last the
# bad behavior ban (it bans the source IP, so nothing can follow it).
set -u
B=${1:-http://127.0.0.1:19480}
UA='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36'
c() { curl -s -o /dev/null -w "%{http_code} $*\n" -A "$UA" -H 'Host: www.example.com' "$@"; }

echo "# allowed (the stack has no backend, so nginx answers 404: the WAF let them through)"
c "$B/search?q=hello+world&page=2"
c -X POST -d 'user=alice&pw=secret' "$B/login"
c "$B/about.html"
c -A 'curl/8.18.0' "$B/robots-check"
sleep 12

echo "# limit plugin"
for _ in 1 2 3 4 5; do c "$B/limited"; done

echo "# blacklist plugin"
c "$B/blocked-by-blacklist/x"

echo "# ModSecurity (CRS)"
c "$B/blocked-xss?q=%3Cscript%3Ealert(1)%3C/script%3E"
c "$B/products?id=1%27%20OR%20%271%27=%271"
c "$B/item?id=1%20UNION%20SELECT%20username,password%20FROM%20users--"
c -X POST --data-urlencode 'comment=<img src=x onerror=alert(1)>' "$B/comment"
c "$B/download?file=../../../../etc/passwd"
c "$B/ping?host=127.0.0.1;cat%20/etc/passwd"
sleep 12

echo "# bad behavior ban (5 x 404 inside 10 s, then the ban hits)"
for i in 1 2 3 4 5 6 7; do c "$B/nope$i"; done
sleep 1
c "$B/after-ban"
