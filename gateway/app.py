import json

import grpc
from flask import Flask, abort, jsonify, request
from werkzeug.exceptions import HTTPException
import event_pb2
import event_pb2_grpc
import registration_pb2
import registration_pb2_grpc

CONFIG = json.load(open("config.json"))
STATUS = {
    grpc.StatusCode.INVALID_ARGUMENT: 400,
    grpc.StatusCode.NOT_FOUND: 404,
    grpc.StatusCode.ALREADY_EXISTS: 409,
    grpc.StatusCode.RESOURCE_EXHAUSTED: 409,
    grpc.StatusCode.FAILED_PRECONDITION: 409,
    grpc.StatusCode.UNIMPLEMENTED: 501,
    grpc.StatusCode.UNAVAILABLE: 503,
}

app = Flask(__name__)
events = event_pb2_grpc.EventServiceStub(grpc.insecure_channel(CONFIG["event_service"]))
registrations = registration_pb2_grpc.RegistrationServiceStub(
    grpc.insecure_channel(CONFIG["registration_service"]))


def fields(message):
    return {field.name: getattr(message, field.name) for field in message.DESCRIPTOR.fields}


@app.errorhandler(grpc.RpcError)
def rpc_error(error):
    return jsonify(error=error.details()), STATUS.get(error.code(), 500)


@app.errorhandler(HTTPException)
def http_error(error):
    return jsonify(error=error.description), error.code


# issue #5: staff auth (Precious)
@app.before_request
def require_staff_token():
    return None


@app.get("/api/v1/events")
def list_events():
    abort(501, "TODO task 1: implement GET /api/v1/events")


@app.get("/api/v1/events/<int:event_id>")
def get_event(event_id):
    return jsonify(fields(events.GetEvent(event_pb2.EventId(event_id=event_id))))


@app.post("/api/v1/events")
def add_event():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        abort(400, "Request body must be a JSON object")
    name, capacity = body.get("name"), body.get("capacity")
    if not isinstance(name, str):
        abort(400, "'name' is required and must be a string")
    if type(capacity) is not int:  # isinstance would accept true/false, since bool subclasses int
        abort(400, "'capacity' is required and must be an integer")
    if not 0 <= capacity <= 2**31 - 1:
        abort(400, "'capacity' must be between 0 and 2147483647")
    event = events.CreateEvent(event_pb2.CreateEventRequest(name=name, capacity=capacity))
    return jsonify(fields(event)), 201


@app.patch("/api/v1/events/<int:event_id>")
def edit_event(event_id):
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        abort(400, "Request body must be a JSON object")
    if "name" in body and not isinstance(body["name"], str):
        abort(400, "'name' must be a string")
    if "capacity" in body:
        if type(body["capacity"]) is not int:  # isinstance would accept true/false, since bool subclasses int
            abort(400, "'capacity' must be an integer")
        if not 0 <= body["capacity"] <= 2**31 - 1:
            abort(400, "'capacity' must be between 0 and 2147483647")
    sent = {key: body[key] for key in ("name", "capacity") if key in body}
    event = events.UpdateEvent(event_pb2.UpdateEventRequest(event_id=event_id, **sent))
    return jsonify(fields(event))


@app.delete("/api/v1/events/<int:event_id>")
def delete_event(event_id):
    abort(501, "TODO task 2: implement DELETE /api/v1/events/<event_id>")


@app.post("/api/v1/participants")
def add_participant():
    abort(501, "TODO task 3: implement POST /api/v1/participants")


@app.get("/api/v1/participants/<int:participant_id>")
def get_participant(participant_id):
    reply = registrations.GetParticipant(registration_pb2.ParticipantId(participant_id=participant_id))
    return jsonify(fields(reply))


@app.get("/api/v1/events/<int:event_id>/registrations")
def list_bookings(event_id):
    reply = registrations.ListBookings(registration_pb2.ListBookingsRequest(event_id=event_id))
    return jsonify([fields(booking) for booking in reply.bookings])


@app.post("/api/v1/registrations")
def book():
    abort(501, "TODO task 4: implement POST /api/v1/registrations")


@app.delete("/api/v1/registrations/<int:booking_id>")
def cancel(booking_id):
    registrations.CancelBooking(registration_pb2.BookingId(booking_id=booking_id))
    return "", 204


app.run(host=CONFIG["host"], port=CONFIG["port"])
