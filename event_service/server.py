import json
from concurrent import futures

import grpc
import mysql.connector
import event_pb2 as pb
import event_pb2_grpc as rpc

CONFIG = json.load(open("config.json"))


def read(sql, args=()):
    with mysql.connector.connect(**CONFIG["db"]) as db, db.cursor(dictionary=True) as cursor:
        cursor.execute(sql, args)
        return cursor.fetchall()


def write(sql, args=()):
    with mysql.connector.connect(**CONFIG["db"]) as db, db.cursor() as cursor:
        cursor.execute(sql, args)
        db.commit()
        return cursor.lastrowid


class EventService(rpc.EventServiceServicer):
    def GetEvent(self, request, context):
        found = read("""SELECT event_id, name, capacity, capacity - seats_taken AS available_seats
                        FROM events WHERE event_id = %s""", (request.event_id,))
        if not found:
            context.abort(grpc.StatusCode.NOT_FOUND, "Event not found")
        return pb.Event(**found[0])

    def ReleaseSeat(self, request, context):
        self.GetEvent(request, context)
        write("UPDATE events SET seats_taken = seats_taken - 1 WHERE event_id = %s", (request.event_id,))
        return pb.Empty()

    # issue #4: list events (Precious)
    def ListEvents(self, request, context):
        if request.HasField("name_filter") and request.name_filter:
            rows = read(
                """SELECT event_id, name, capacity,
                          capacity - seats_taken AS available_seats
                   FROM events
                   WHERE name LIKE %s
                   ORDER BY event_id""",
                (f"%{request.name_filter}%",)
            )
        else:
            rows = read(
                """SELECT event_id, name, capacity,
                          capacity - seats_taken AS available_seats
                   FROM events
                   ORDER BY event_id"""
            )

        return pb.ListEventsResponse(
            events=[pb.Event(**row) for row in rows]
        )


    # issue #6: create event (Darren)
    def CreateEvent(self, request, context):
        name = request.name.strip()
        if not name:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Event name must not be blank")
        if len(name) > 150:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Event name must be at most 150 characters")
        event_id = write("INSERT INTO events (name, capacity) VALUES (%s, %s)", (name, request.capacity))
        return self.GetEvent(pb.EventId(event_id=event_id), context)

    # issue #7: update event (Darren)
    def UpdateEvent(self, request, context):
        changes, args = [], []
        if request.HasField("name"):
            name = request.name.strip()
            if not name:
                context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Event name must not be blank")
            if len(name) > 150:
                context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Event name must be at most 150 characters")
            changes.append("name = %s")
            args.append(name)

        found = read("SELECT seats_taken FROM events WHERE event_id = %s", (request.event_id,))
        if not found:
            context.abort(grpc.StatusCode.NOT_FOUND, "Event not found")

        if request.HasField("capacity"):
            booked = found[0]["seats_taken"]
            if request.capacity < booked:
                context.abort(grpc.StatusCode.FAILED_PRECONDITION,
                              f"Capacity cannot be below the {booked} seats already booked")
            changes.append("capacity = %s")
            args.append(request.capacity)

        if changes:
            write(f"UPDATE events SET {', '.join(changes)} WHERE event_id = %s", (*args, request.event_id))
        return self.GetEvent(pb.EventId(event_id=request.event_id), context)

    # issue #8: delete event (Anna)
    def DeleteEvent(self, request, context):
        found = read("SELECT seats_taken FROM events WHERE event_id = %s", (request.event_id,))
        # event doesn't exist
        if not found:
            context.abort(grpc.StatusCode.NOT_FOUND, "Event not found")
        # event has bookings
        if found[0]["seats_taken"] > 0:
            context.abort(grpc.StatusCode.FAILED_PRECONDITION, "Event has bookings and cannot be deleted")
        write("DELETE FROM events WHERE event_id = %s", (request.event_id,))
        return pb.Empty()

    # issue #10: reserve a seat for a booking (Jordan)
    def ReserveSeat(self, request, context):
        context.abort(grpc.StatusCode.UNIMPLEMENTED, "TODO #10")


server = grpc.server(futures.ThreadPoolExecutor(max_workers=8))
rpc.add_EventServiceServicer_to_server(EventService(), server)
server.add_insecure_port(CONFIG["listen"])
server.start()
print(f"Event service on {CONFIG['listen']}", flush=True)
server.wait_for_termination()
