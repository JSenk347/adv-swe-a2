# COMP 4633 Assignment 2 – Team Report

## 1. What we learned
### Joseph
### Precious
### Darren

I learned how a single request crosses process boundaries: the gateway validates JSON, builds a protobuf message, calls a gRPC stub, and the service talks to its own database. Splitting validation between the gateway (shape and types) and the service (business rules like blank names or capacity below seats already booked) made each layer simpler. I also got practice with a stricter Git workflow: one branch and PR per issue, written test tables, and reviewing teammates' code before merging.

### Anna
### Jordan

Booking helped clarify the microservices split for me. One `POST /registrations` touches two databases owned by two processes, and there's no transaction that covers both, so I had to decide which write happens first. I also learned how status codes travel: the event service aborts with `RESOURCE_EXHAUSTED`, the `call` helper pushes it through the registration service, and the gateway turns it into a 409 without either service using HTTP. On the practical side, merging `main` into my branch produced a second `ReserveSeat` in `event.proto` and `server.py`, which taught me to re-read the generated contract after every merge. Deploying the stack on a Google Cloud VM showed me how much sits outside the code: installing MySQL, switching root off socket auth, binding the gateway to `0.0.0.0` and opening port 8080 in the firewall.

## 2. Monolithic and microservices architecture
<!-- Precious -->

## 3. JSON and Protocol Buffers
<!-- Anna -->

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
### Jordan

I implemented bookings across the two services. For create booking (#10, PR #18) I added `ReserveSeat` to the event service and contract, wrote `CreateBooking` in the registration service (participant check, duplicate check, seat reservation, insert, and the join for `participant_name`), and added the `POST /api/v1/registrations` gateway route. I also fixed the duplicate `ReserveSeat` that came in when I merged `main` into that branch. For list bookings (#11, PR #19) I wrote `ListBookings` and the `GET /api/v1/events/{id}/registrations` route. I set up the team repository, project board and established a branch ruleset requiring a PR to be reviewed by at least 1 person before merging. I also merged Darren's create and update event PRs (#16, #17) and Anna's smoke test and report skeleton PRs (#21, #22), and deployed the system to a Google Cloud VM, including the change that lets the gateway accept outside connections (PR #28).

## Design choices from the README
### ListEvents: repeated field or stream
<!-- Precious -->
### Order of the two booking writes
<!-- Jordan -->

`CreateBooking` reserves the seat and then writes the booking row. Before either write it checks, in its own database, that the participant exists and has no confirmed booking for the event, so the only cross-service step is `ReserveSeat`.

**If the event service answers "full".** Nothing has been written yet. `ReserveSeat` aborts with `RESOURCE_EXHAUSTED`, the `call` helper forwards it, and the client gets a 409 leaving both databases untouched. If we wrote the booking row first, we would then have to delete or cancel it which introduces another potential point of failure.

**If the process dies between the two steps.** `seats_taken` is one higher than the number of confirmed bookings. The event under-sells by one seat, but it's never overbooked, and nobody holds a booking without a seat. The opposite order would leave a confirmed booking with no seat counted, so the event could end up with more bookings than capacity, which is the more serious failure for a booking system.

**Compared with `CancelBooking`.** Cancel uses the opposite order: it marks the row cancelled, then releases the seat. A crash there also leaves `seats_taken` too high. So the two flows use opposite orders to fail in the same direction: any mismatch means a seat counted as taken that nobody holds. That gives one simple repair for both, a job that compares `seats_taken` in `event_db` with the count of confirmed bookings per event in `registration_db` and releases the difference.

The order doesn't remove the gaps. If the insert fails after `ReserveSeat` succeeds, the seat leaks the same way. Calling `ReleaseSeat` as a compensation step would cover that, but we didn't add it. The duplicate check is also a read followed by an insert, so two simultaneous requests can both pass it; a `UNIQUE` constraint would close that, as the README's "Going further" section points out.