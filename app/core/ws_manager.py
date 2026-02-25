from fastapi import WebSocket
from typing import Dict, List
import json

class ConnectionManager:
    """
    Manages WebSocket connections per user_id.
    A single customer can have multiple connections (e.g. multiple tabs/devices).
    """

    def __init__(self):
        # { user_id: [websocket1, websocket2, ...] }
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        """Accept the connection and register it under the user's ID."""
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)

    def disconnect(self, websocket: WebSocket, user_id: int):
        """Remove the connection when the client disconnects."""
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            # Clean up empty lists
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    async def send_to_user(self, user_id: int, message: dict):
        """Send a JSON message to ALL connections for a specific user."""
        if user_id in self.active_connections:
            dead_connections = []
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    dead_connections.append(connection)
            
            # Clean up any dead connections
            for dc in dead_connections:
                self.active_connections[user_id].remove(dc)


# Single global instance — imported everywhere
manager = ConnectionManager()
