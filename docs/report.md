# COMP 4633 Assignment 2 – Team Report

## 1. What we learned
### Joseph

The biggest thing I learned was to write the contract first. I added the new proto messages and an empty method for each unbuilt route in one pull request before any features, and after that everyone filled in their own method and the merges into main were clean. Error handling was new to me too. A service raises a gRPC status such as `NOT_FOUND`, and the gateway is the only place that turns it into an HTTP number like 404. Reviewing the booking code also taught me that passing every acceptance check doesn't make code safe: two requests sent at the same moment could still both take the last seat.

### Precious

I learned how microservices communicate through gRPC and Protocol Buffers while exposing REST endpoints through a central API gateway. Implementing the List Events functionality helped me understand how requests are passed from the gateway to the Event Service, how database queries are performed, and how the results are returned as JSON responses. Implementing staff authentication also showed me how the gateway can enforce access restrictions before requests reach the underlying services. Also, working with separate Git branches, pull requests, and code reviews helped me gain a better understanding of how collaboration in software development works and the importance of testing changes before merging them into the main branch.

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

Booking helped clarify the microservices split for me. One `POST /registrations` touches two databases owned by two processes, and there's no transaction that covers both, so I had to decide which write happens first. I also learned how status codes travel: the event service aborts with `RESOURCE_EXHAUSTED`, the `call` helper pushes it through the registration service, and the gateway turns it into a 409 without either service using HTTP. On the practical side, merging `main` into my branch produced a second `ReserveSeat` in `event.proto` and `server.py`, which taught me to re-read the generated contract after every merge. Deploying the stack on a Google Cloud VM showed me how much sits outside the code: installing MySQL, switching root off socket auth, binding the gateway to `0.0.0.0` and opening port 8080 in the firewall.

## 2. Monolithic and microservices architecture
<!-- Precious -->
A monolithic architecture is a software design in which all application components, such as the API, business logic, and database interactions, are developed and deployed as a single application. In contrast, a microservices architecture divides an application into smaller, independently deployable services that communicate over a network.

The main advantage of a monolithic architecture is its simplicity. Since the components run together, development, testing, and deployment can be easier for smaller applications. However, as the application grows, changes to one component may require redeploying the entire application, and scaling individual features becomes more difficult.

Microservices offer greater flexibility because services can be developed, deployed, maintained, and scaled independently. However, they create additional complexity, including network communication, service coordination, and handling failures between services.

In our Campus Events application, the API Gateway receives HTTP requests and communicates with the Event Service and Registration Service using gRPC and Protocol Buffers. Each service manages its own database. This separation allows us to modify functionality such as event management or registration handling without necessarily modifying the other service. Through this assignment, we gained a practical understanding of how microservices improve modularity while requiring more careful coordination between application components.

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

Our two services already run as separate processes and only talk over gRPC, so moving them to separate VMs or containers is mostly a configuration change. Each service's `listen` address in its `config.json` is `127.0.0.1`, which only accepts connections from the same machine, so each would listen on `0.0.0.0` or its private IP, with ports 8081 and 8082 opened only to the machines that call them. The callers need the new addresses: the registration service's `event_service` entry, and the gateway's `event_service` and `registration_service` entries. On VMs these become private IPs, and in Docker or Kubernetes they become service names such as `event-service:8081` that the platform's DNS resolves. If a database moves off its service's machine, that service's `db` host changes the same way. In the code, we use `grpc.insecure_channel` on the calling side and `add_insecure_port` on the servers, which send everything unencrypted, so across a real network both ends would switch to TLS, which gRPC supports for encrypting traffic and authenticating the server. We would also set a deadline on calls like `ReserveSeat`, because gRPC sets none by default and a client can wait forever on a server that never answers.

To scale a service we would run more copies of it, and because each service is deployed separately the two counts are independent. In Kubernetes each service would be its own Deployment with its own replica count, so the event service could run five copies while registration runs two; on VMs it would be more VMs behind a load balancer. gRPC makes the load balancing harder than it is for REST. It runs on HTTP/2 and sends many requests over one long-lived connection, so a connection-level (L4) load balancer, which is what Kubernetes provides by default, pins all of them to one copy. We would put an application-level (L7) proxy in front of each service so each request can go to a different copy; client-side load balancing is the other option. With several copies of the event service the database becomes the limit, because they all share `event_db`: checking for a free seat and taking it has to be a single atomic SQL statement, or two copies can sell the last seat twice. We saw that race in testing even with one copy.

Sources: gRPC documentation, "gRPC Load Balancing" (grpc.io/blog/grpc-load-balancing), "Deadlines" (grpc.io/docs/guides/deadlines) and "Authentication" (grpc.io/docs/guides/auth); Kubernetes documentation, "Service" and "Deployments" (kubernetes.io/docs/concepts), and the Kubernetes blog, "gRPC Load Balancing on Kubernetes without Tears".

## 6. Each member's contributions
### Joseph

I wrote the contract skeleton (#1, PR #15): the new RPCs and messages in the two proto files, plus an empty labelled method per unbuilt route so each teammate had one place to work. After that I implemented get participant (#2) and create participant (#3) in the registration service and the gateway. For reviews, I ran Jordan's create booking (PR #18) on fresh seed data, reported that two simultaneous bookings for the last seat both succeed, and merged it, and I approved his gateway host change (PR #28). Some of my work isn't in the commits: I wrote the 13 issues with their acceptance criteria and the plan that split the work into five streams, set up the team's Google Cloud VM, and ran the smoke test on it.

### Precious
I implemented the List Events functionality (Issue #4), including the `ListEvents` gRPC method in the Event Service and the corresponding REST endpoint in the API Gateway. My implementation supports retrieving all events, optional name filtering using SQL `LIKE`, and returning event information with available seat counts. I also implemented staff authentication (Issue #5) in the API Gateway, requiring a valid Bearer token for event creation, updates, and deletion while allowing public read operations. I tested both features using HTTP requests and verified the expected responses for successful requests and unauthorized access. I also reviewed Anna's Delete Event implementation (Issue #8), testing successful deletion, nonexistent events, events with existing bookings, and unauthorized requests. Lastly, I participated in integration testing and contributed to the team's documentation and report.

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

I implemented bookings across the two services. For create booking (#10, PR #18) I added `ReserveSeat` to the event service and contract, wrote `CreateBooking` in the registration service (participant check, duplicate check, seat reservation, insert, and the join for `participant_name`), and added the `POST /api/v1/registrations` gateway route. I also fixed the duplicate `ReserveSeat` that came in when I merged `main` into that branch. For list bookings (#11, PR #19) I wrote `ListBookings` and the `GET /api/v1/events/{id}/registrations` route. I set up the team repository, project board and established a branch ruleset requiring a PR to be reviewed by at least 1 person before merging. I also merged Darren's create and update event PRs (#16, #17) and Anna's smoke test and report skeleton PRs (#21, #22), and deployed the system to a Google Cloud VM, including the change that lets the gateway accept outside connections (PR #28).

## Design choices from the README
### ListEvents: repeated field or stream
<!-- Precious -->
We chose to use a `repeated Event` field in `ListEventsResponse` rather than gRPC streaming because the Campus Events API retrieves a relatively small collection of events in a single request. A repeated field allows the Event Service to return all matching events in one Protobuf response, which the API Gateway can easily convert into a JSON array for the REST client.

Using gRPC streaming would allow events to be delivered individually as they become available, which could be beneficial for very large datasets or continuous updates. However, streaming would introduce additional complexity that is unnecessary for our application's current requirements. Since our endpoint returns a complete list of events rather than a continuous stream, a repeated field provides a simpler implementation that meets our needs.

### Order of the two booking writes
<!-- Jordan -->

`CreateBooking` reserves the seat and then writes the booking row. Before either write it checks, in its own database, that the participant exists and has no confirmed booking for the event, so the only cross-service step is `ReserveSeat`.

**If the event service answers "full".** Nothing has been written yet. `ReserveSeat` aborts with `RESOURCE_EXHAUSTED`, the `call` helper forwards it, and the client gets a 409 leaving both databases untouched. If we wrote the booking row first, we would then have to delete or cancel it which introduces another potential point of failure.

**If the process dies between the two steps.** `seats_taken` is one higher than the number of confirmed bookings. The event under-sells by one seat, but it's never overbooked, and nobody holds a booking without a seat. The opposite order would leave a confirmed booking with no seat counted, so the event could end up with more bookings than capacity, which is the more serious failure for a booking system.

**Compared with `CancelBooking`.** Cancel uses the opposite order: it marks the row cancelled, then releases the seat. A crash there also leaves `seats_taken` too high. So the two flows use opposite orders to fail in the same direction: any mismatch means a seat counted as taken that nobody holds. That gives one simple repair for both, a job that compares `seats_taken` in `event_db` with the count of confirmed bookings per event in `registration_db` and releases the difference.

The order doesn't remove the gaps. If the insert fails after `ReserveSeat` succeeds, the seat leaks the same way. Calling `ReleaseSeat` as a compensation step would cover that, but we didn't add it. The duplicate check is also a read followed by an insert, so two simultaneous requests can both pass it; a `UNIQUE` constraint would close that, as the README's "Going further" section points out.