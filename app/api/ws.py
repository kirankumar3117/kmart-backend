from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.core.ws_manager import manager

router = APIRouter()

# ==========================================
# WEBSOCKET ENDPOINT
# ==========================================
# Customers connect here to receive real-time order updates.
#
# Frontend usage (React Native / JavaScript):
#   const ws = new WebSocket("ws://localhost:8000/ws/orders/42");
#   ws.onmessage = (event) => {
#       const data = JSON.parse(event.data);
#       console.log("Order update:", data);
#   };
# ==========================================
@router.websocket("/orders/{user_id}")
async def websocket_order_updates(websocket: WebSocket, user_id: int):
    # 1. Register this connection under the user's ID
    await manager.connect(websocket, user_id)
    
    try:
        # 2. Keep the connection alive — listen for any incoming messages
        #    (We don't really need client messages, but we must keep the loop
        #     running so FastAPI doesn't close the socket)
        while True:
            # Wait for a message from the client (ping/keepalive)
            await websocket.receive_text()
            
    except WebSocketDisconnect:
        # 3. Client disconnected — clean up
        manager.disconnect(websocket, user_id)
