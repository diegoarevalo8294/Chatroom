#!/usr/bin/env python3
"""
Real-time chat server.

A small async WebSocket server that supports multiple chat "rooms",
usernames, join/leave notifications, a live user list, and message
history for anyone who joins a room after messages were sent.

Run:
    pip install websockets
    python server.py            # listens on 0.0.0.0:8765

Then open client.html in a browser (one tab per user is fine for testing).
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

import websockets
from websockets.server import WebSocketServerProtocol

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("chat")

HOST = "0.0.0.0"
PORT = 8765
HISTORY_LIMIT = 50  # messages kept per room for newcomers


@dataclass
class Room:
    name: str
    clients: dict[WebSocketServerProtocol, str] = field(default_factory=dict)  # ws -> username
    history: list[dict] = field(default_factory=list)

    def usernames(self) -> list[str]:
        return sorted(self.clients.values(), key=str.lower)


rooms: dict[str, Room] = {}


def get_room(name: str) -> Room:
    if name not in rooms:
        rooms[name] = Room(name=name)
    return rooms[name]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def send_json(ws: WebSocketServerProtocol, payload: dict) -> None:
    try:
        await ws.send(json.dumps(payload))
    except websockets.ConnectionClosed:
        pass


async def broadcast(room: Room, payload: dict, exclude: WebSocketServerProtocol | None = None) -> None:
    dead = []
    for client in room.clients:
        if client is exclude:
            continue
        try:
            await client.send(json.dumps(payload))
        except websockets.ConnectionClosed:
            dead.append(client)
    for d in dead:
        room.clients.pop(d, None)


async def handle_connection(ws: WebSocketServerProtocol) -> None:
    room: Room | None = None
    username: str | None = None

    try:
        # --- Handshake: first message from the client must be a "join" ---
        raw = await asyncio.wait_for(ws.recv(), timeout=30)
        msg = json.loads(raw)

        if msg.get("type") != "join":
            await send_json(ws, {"type": "error", "text": "Expected a join message first."})
            return

        username = (msg.get("username") or "").strip()[:32] or f"guest-{id(ws) % 10000}"
        room_name = (msg.get("room") or "general").strip()[:32] or "general"
        room = get_room(room_name)

        # Avoid duplicate usernames in the same room
        existing = set(room.clients.values())
        base = username
        n = 2
        while username in existing:
            username = f"{base}-{n}"
            n += 1

        room.clients[ws] = username
        log.info("join room=%s user=%s (now %d online)", room_name, username, len(room.clients))

        await send_json(ws, {
            "type": "joined",
            "room": room_name,
            "username": username,
            "history": room.history[-HISTORY_LIMIT:],
            "users": room.usernames(),
        })

        await broadcast(room, {
            "type": "system",
            "text": f"{username} joined the room.",
            "ts": now_iso(),
            "users": room.usernames(),
        }, exclude=ws)

        # --- Main receive loop ---
        async for raw in ws:
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            mtype = msg.get("type")

            if mtype == "message":
                text = (msg.get("text") or "").strip()[:2000]
                if not text:
                    continue
                payload = {
                    "type": "message",
                    "username": username,
                    "text": text,
                    "ts": now_iso(),
                }
                room.history.append(payload)
                room.history[:] = room.history[-HISTORY_LIMIT:]
                await broadcast(room, payload)

            elif mtype == "typing":
                await broadcast(room, {
                    "type": "typing",
                    "username": username,
                }, exclude=ws)

    except (websockets.ConnectionClosed, asyncio.TimeoutError):
        pass
    except Exception:
        log.exception("Unhandled error in connection handler")
    finally:
        if room is not None and ws in room.clients:
            room.clients.pop(ws, None)
            log.info("leave room=%s user=%s (now %d online)", room.name, username, len(room.clients))
            await broadcast(room, {
                "type": "system",
                "text": f"{username} left the room.",
                "ts": now_iso(),
                "users": room.usernames(),
            })
            if not room.clients and not room.history:
                rooms.pop(room.name, None)


async def main() -> None:
    async with websockets.serve(handle_connection, HOST, PORT, ping_interval=20, ping_timeout=20):
        log.info("Chat server listening on ws://%s:%d", HOST, PORT)
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Server stopped.")
