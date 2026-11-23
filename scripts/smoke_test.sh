#!/usr/bin/env bash
# Smoke test for issue #9: runs the README's "How to work" sequence from fresh seed data.
# Usage: with `make dev` running in another terminal:
#   bash scripts/smoke_test.sh
set -u
cd "$(dirname "$0")/.." || exit 1   # run from the repo root, wherever the script is called from

base=${BASE:-http://127.0.0.1:8080/api/v1}
json='Content-Type: application/json'
pass=0
fail=0

# check <label> <expected status> <expected text in body, or ""> <curl args...>
check() {
  local label=$1 want_status=$2 want_text=$3
  shift 3
  local out status body
  out=$(curl -sS -w $'\n%{http_code}' "$@")
  status=${out##*$'\n'}
  body=${out%$'\n'*}
  body=${body%$'\n'}
  if [[ $status == "$want_status" && $body == *"$want_text"* ]]; then
    echo "PASS  $label  ($status)"
    pass=$((pass + 1))
  else
    echo "FAIL  $label  wanted $want_status${want_text:+ with $want_text}, got $status: $body"
    fail=$((fail + 1))
  fi
}

echo "Loading fresh seed data (make db)..."
make db > /dev/null || { echo "make db failed"; exit 1; }

check "1. list events named 'lab'"         200 '"name":"API design lab"' "$base/events?name=lab"
check "2. create participant Fay"           201 '"name":"Fay"'            -X POST -H "$json" -d '{"name":"Fay"}' "$base/participants"
check "3. book Dana (4) into event 2"       201 '"participant_name":"Dana"' -X POST -H "$json" -d '{"event_id":2,"participant_id":4}' "$base/registrations"
check "4. event 2 has 3 seats left"         200 '"available_seats":3'     "$base/events/2"
check "5. Dana listed for event 2"          200 '"participant_name":"Dana"' "$base/events/2/registrations"
check "6. book Alex (1) into event 3"       201 '"event_id":3'            -X POST -H "$json" -d '{"event_id":3,"participant_id":1}' "$base/registrations"
check "7. event 3 full, Bao (2) refused"    409 ''                        -X POST -H "$json" -d '{"event_id":3,"participant_id":2}' "$base/registrations"
check "7b. event 3 still 0 seats left"      200 '"available_seats":0'     "$base/events/3"
check "8. cancel Dana's booking (4)"        204 ''                        -X DELETE "$base/registrations/4"
check "9. event 2 back to 4 seats"          200 '"available_seats":4'     "$base/events/2"

echo
echo "$pass passed, $fail failed"
[[ $fail -eq 0 ]]