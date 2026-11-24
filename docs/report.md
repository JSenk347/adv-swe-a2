# COMP 4633 Assignment 2 – Team Report

## 1. What we learned
### Joseph
### Precious
### Darren
I learned how a single request crosses process boundaries: the gateway validates JSON, builds a protobuf message, calls a gRPC stub, and the service talks to its own database. Splitting validation between the gateway (shape and types) and the service (business rules like blank names or capacity below seats already booked) made each layer simpler. I also got practice with a stricter Git workflow: one branch and PR per issue, written test tables, and reviewing teammates' code before merging.

### Anna
The most useful technical concept I learned was how errors travel through a
system made of separate services. In my delete event route (#8), the Event
service never mentions HTTP. Instead, it reports a missing event with `NOT_FOUND`
and an event that still has bookings with `FAILED_PRECONDITION`, and the
gateway's `STATUS` table translates those gRPC status codes into 404 and 409 for
the client. I was able to see exactly why this split matters when a typo in my
service method raised an ordinary Python error instead. gRPC returned an
`UNKNOWN` status, which the gateway has no mapping for, so the client received a
500 with no useful message. This helped me understand how every expected
failure should be reported with `context.abort` and its correct status code, so
the service is responsible for the business rules, and the gateway is
responsible for HTTP.

### Jordan

## 2. Monolithic and microservices architecture
<!-- Precious -->

## 3. JSON and Protocol Buffers
<!-- Anna -->
In our project both the client and the gateway use JSON, and Protobuf is used
between the gateway and services.

**Similarities:**
Both JSON and Protobuf take structured data and
then package it so it can be sent between separate programs. As well, both are
language neutral. JSON can be written or read in any language with a standard
library, and Protobuf is generated for each language from the same
`.proto` file, so a Python program and a Node.js program end up producing and 
reading the same bytes even though their generated code looks different. In our
system, both formats also carry the same data, an event has the same four
fields whether the Event service sends it to the gateway as Protobuf or the
gateway returns it to the client as JSON.

**Differences:** JSON is readable plain text, while Protobuf is binary, which
isn't easily readable. Additionally, JSON sends the name of every field in
every message, but Protobuf only sends a field number because both sides
already know what each number means from the shared `.proto` file. This makes
Protobuf messages much smaller. JSON also has no required schema, so any valid
JSON is accepted even if a field was renamed or changed type, which is why our
gateway has to manually check each field's type. Protobuf requires a schema,
and both the gateway and the services generate their code from it with
`make gen`, so every field's name, number, and type match. Finally, Protobuf
leaves out any field that holds its default value, like 0, so a field has to be
marked `optional` to tell the difference between "not sent" and "sent as zero".

**Example.** We used the `Event` message from the `event.proto`:
```proto
message Event { int64 event_id = 1; string name = 2; int32 capacity = 3; int32 available_seats = 4; }
```
For event 2, the gateway returns this JSON to the client, which is 71 bytes:
For event 2, the gateway returns this JSON to the client, which is 71 bytes:
```json
{"available_seats":4,"capacity":4,"event_id":2,"name":"API design lab"}
```
The same event sent from the Event service to the gateway as Protobuf is only
22 bytes:
```
08 02 12 0e 41 50 49 20 64 65 73 69 67 6e 20 6c 61 62 18 04 20 04
```
Instead of field names, Protobuf marks each field with a short number from the
`.proto` file. For example, the first two bytes, `08 02`, mean "field 1
(`event_id`) is 2", and the bytes after them hold the event's name as text. None
of the field names are sent, which is where most of the size difference comes
from. This is why our system uses JSON at the gateway, where it is easy to read
and test with `curl`, and Protobuf between the gateway and the services, where
smaller and strictly typed messages are more useful.

## 4. REST and gRPC
<!-- Darren -->

Our system uses both, which made the comparison concrete. The gateway is a REST API: clients send HTTP requests such as `POST /api/v1/events` with a JSON body, and the URL plus the HTTP verb say what to do. Behind it, the gateway talks to the Event and Registration services over gRPC, calling methods like `CreateEvent` and `GetParticipant` on a generated stub as if they were local functions.

**Similarities.** Both are client–server request/response styles that usually run over HTTP, both let services written separately talk over a network, and both have a standard set of status codes. That last point is why our gateway can translate one into the other with a single table (`STATUS` in `gateway/app.py`), for example `NOT_FOUND` becomes 404 and `INVALID_ARGUMENT` becomes 400.

**Differences.** REST is resource-oriented (nouns in URLs, verbs from HTTP), while gRPC is procedure-oriented (named methods on a service). REST usually sends human-readable JSON with no enforced schema, so our gateway has to check every field's type by hand; gRPC sends binary Protocol Buffers defined in a `.proto` contract, and the generated code enforces the types. gRPC runs on HTTP/2 and supports streaming in both directions, while REST is typically one request, one response. REST is easy to call from a browser or `curl`, which is why it suits the public edge of our system, and gRPC is faster and more strictly typed, which suits internal service-to-service calls. One thing I ran into was partial updates: for `PATCH /events/{id}` JSON can simply omit a field, but in proto3 an unset string looks the same as an empty string, so `UpdateEventRequest` needed `optional` fields and `HasField()` to tell "not sent" from "sent as empty."

## 5. Deploying Event and Registration separately
<!-- Joseph -->

## 6. Each member's contributions
### Joseph
### Precious
### Darren

I implemented create event (#6, PR #16) and update event (#7, PR #17), covering the gateway route and the Event service method for each, including validation and the 409 when capacity drops below booked seats. I reviewed the contract skeleton (requested changes on #14, approved the revision in #15), approved Jordan's list-bookings PR (#19), and reviewed, approved and merged Joseph's participant PRs (#23, #26).

### Anna
I implemented delete event (#8, PR #20), covering the `DeleteEvent` method in
the Event service and the `delete_event` gateway route, including the 404 for
an unknown event and the 409 when an event still has bookings. I also wrote the
smoke test script (#9, PR #21), which loads fresh seed data, runs the README's
full request sequence, and prints a pass or fail for each expected status code
and seat count. I reviewed and approved Precious's staff authentication
(PR #24) and list events (PR #25) pull requests, testing each one locally
against its acceptance criteria before approving.
For the report, I created the report skeleton (PR #22) so everyone could write
in their own section without merge conflicts, and I wrote the answer to
question 3. I also reran the smoke test as routes were merged to confirm the
whole system worked together.

### Jordan

## Design choices from the README
### ListEvents: repeated field or stream
<!-- Precious -->
### Order of the two booking writes
<!-- Jordan -->