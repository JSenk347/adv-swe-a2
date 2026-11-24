# COMP 4633 Assignment 2 – Team Report

## 1. What we learned
### Joseph
### Precious
### Darren

I learned how a single request crosses process boundaries: the gateway validates JSON, builds a protobuf message, calls a gRPC stub, and the service talks to its own database. Splitting validation between the gateway (shape and types) and the service (business rules like blank names or capacity below seats already booked) made each layer simpler. I also got practice with a stricter Git workflow: one branch and PR per issue, written test tables, and reviewing teammates' code before merging.

### Anna
### Jordan

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

Our two services already run as separate processes and only talk over gRPC, so moving them to separate VMs or containers is mostly a configuration change. Two settings change. Each service's `listen` address in its `config.json` is `127.0.0.1`, which only accepts connections from the same machine, so each service would listen on `0.0.0.0` or its private IP, with ports 8081 and 8082 opened in the firewall only to the machines that call them. The callers then need the new addresses: the registration service's `event_service` entry, and the gateway's `event_service` and `registration_service` entries. On VMs these become private IPs. In Docker or Kubernetes they become service names such as `event-service:8081` that the platform's DNS resolves, so the address stays the same when a copy is replaced. The code needs two changes as well. We use `grpc.insecure_channel`, which sends everything unencrypted, so across a real network we would switch to a TLS channel; gRPC supports TLS for encrypting traffic and authenticating the server. We would also set a deadline on calls like `ReserveSeat`, because gRPC sets none by default and a client can wait forever on a server that never answers.

To scale a service we would run more copies of it, and because each service is deployed separately the two counts are independent. In Kubernetes each service would be its own Deployment with its own replica count, behind a Service that gives all the copies one stable name, so the event service could run five copies while registration runs two. On VMs the same idea is more VMs behind a load balancer. Load balancing takes some care. gRPC runs on HTTP/2 and sends many requests over one long-lived connection, so a transport-level (L4) load balancer would send all of a client's requests to the same copy. An application-level (L7) load balancer can route each request separately, and client-side load balancing is the other option. The database is the limit. Each service still owns one, so with several copies of the event service, checking for a free seat and taking it has to be a single atomic SQL statement, or two copies can sell the last seat twice. We saw that race in testing even with one copy.

Sources: gRPC documentation, "gRPC Load Balancing" (grpc.io/blog/grpc-load-balancing), "Deadlines" (grpc.io/docs/guides/deadlines) and "Authentication" (grpc.io/docs/guides/auth); Kubernetes documentation, "Service" and "Deployments" (kubernetes.io/docs/concepts).

## 6. Each member's contributions
### Joseph
### Precious
### Darren

I implemented create event (#6, PR #16) and update event (#7, PR #17), covering the gateway route and the Event service method for each, including validation and the 409 when capacity drops below booked seats. I reviewed the contract skeleton (requested changes on #14, approved the revision in #15), approved Jordan's list-bookings PR (#19), and reviewed, approved and merged Joseph's participant PRs (#23, #26).

### Anna
### Jordan

## Design choices from the README
### ListEvents: repeated field or stream
<!-- Precious -->
### Order of the two booking writes
<!-- Jordan -->