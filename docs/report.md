# COMP 4633 Assignment 2 – Team Report

## 1. What we learned
### Joseph

The biggest thing I learned was to write the contract first. I added the new proto messages and an empty method for each unbuilt route in one pull request before any features, and after that everyone filled in their own method and the merges into main were clean. Error handling was new to me too. A service raises a gRPC status such as `NOT_FOUND`, and the gateway is the only place that turns it into an HTTP number like 404. Reviewing the booking code also taught me that passing every acceptance check doesn't make code safe: two requests sent at the same moment could still both take the last seat.

### Precious

I learned how microservices communicate through gRPC and Protocol Buffers while exposing REST endpoints through a central API gateway. Implementing the List Events functionality helped me understand how requests are passed from the gateway to the Event Service, how database queries are performed, and how the results are returned as JSON responses. Implementing staff authentication also showed me how the gateway can enforce access restrictions before requests reach the underlying services. Also, working with separate Git branches, pull requests, and code reviews helped me gain a better understanding of how collaboration in software development works and the importance of testing changes before merging them into the main branch.

### Darren

I learned how a single request crosses process boundaries: the gateway validates JSON, builds a protobuf message, calls a gRPC stub, and the service talks to its own database. Splitting validation between the gateway (shape and types) and the service (business rules like blank names or capacity below seats already booked) made each layer simpler. I also got practice with a stricter Git workflow: one branch and PR per issue, written test tables, and reviewing teammates' code before merging.

### Anna
### Jordan

## 2. Monolithic and microservices architecture
<!-- Precious -->
A monolithic architecture is a software design in which all application components, such as the API, business logic, and database interactions, are developed and deployed as a single application. In contrast, a microservices architecture divides an application into smaller, independently deployable services that communicate over a network.

The main advantage of a monolithic architecture is its simplicity. Since the components run together, development, testing, and deployment can be easier for smaller applications. However, as the application grows, changes to one component may require redeploying the entire application, and scaling individual features becomes more difficult.

Microservices offer greater flexibility because services can be developed, deployed, maintained, and scaled independently. However, they create additional complexity, including network communication, service coordination, and handling failures between services.

In our Campus Events application, the API Gateway receives HTTP requests and communicates with the Event Service and Registration Service using gRPC and Protocol Buffers. Each service manages its own database. This separation allows us to modify functionality such as event management or registration handling without necessarily modifying the other service. Through this assignment, we gained a practical understanding of how microservices improve modularity while requiring more careful coordination between application components.

## 3. JSON and Protocol Buffers
<!-- Anna -->

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
### Jordan

## Design choices from the README
### ListEvents: repeated field or stream
<!-- Precious -->
We chose to use a `repeated Event` field in `ListEventsResponse` rather than gRPC streaming because the Campus Events API retrieves a relatively small collection of events in a single request. A repeated field allows the Event Service to return all matching events in one Protobuf response, which the API Gateway can easily convert into a JSON array for the REST client.

Using gRPC streaming would allow events to be delivered individually as they become available, which could be beneficial for very large datasets or continuous updates. However, streaming would introduce additional complexity that is unnecessary for our application's current requirements. Since our endpoint returns a complete list of events rather than a continuous stream, a repeated field provides a simpler implementation that meets our needs.

### Order of the two booking writes
<!-- Jordan -->