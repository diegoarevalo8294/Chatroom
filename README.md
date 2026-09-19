# Real-Time Chatroom App

A real-time chatroom app coded in Python WebSocket server (`server.py`)
plus a single-file HTML/JS client (`client.html`).

**Features**
- Real-time messaging over WebSockets
- Multiple chat rooms (just type any room name to join/create one)
- Live "who's online" list per room
- Join/leave system messages
- Typing indicator
- Message history replay for anyone who joins a room in progress
- Auto-generated guest name / de-duplicated usernames

## Setup

```bash
pip install -r requirements.txt
python server.py
```

You should see:

```
Chat server listening on ws://0.0.0.0:8765
```

## Using it

Open `client.html` in a browser. Enter a name and a room, leave the server field as
`ws://localhost:8765` (default), and click **Join**.

Open it in a few more browser tabs (or send it to friends on your network,
using your machine's LAN IP instead of `localhost`) to chat with multiple
people at once — each tab/person can pick any name and room.

## Notes

- All state (messages, users) lives in server memory — restarting `server.py`
  clears history. Swap in a database if you need persistence.
- To expose it beyond your local network, run the server on a host with a
  public IP/port (or behind a reverse proxy like nginx with WSS/TLS) and
  update the "server" field in `client.html` to `wss://your-domain:port`.
- Everything needed to run the server is `websockets` — no framework required.
