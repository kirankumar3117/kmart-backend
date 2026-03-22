from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.core.ws_manager import manager

router = APIRouter()

# ==========================================
# WEBSOCKET ENDPOINT
# ==========================================
# Customers connect here to receive real-time order updates.
#
# Frontend usage (React Native / JavaScript):
#   const ws = new WebSocket("ws://localhost:8000/api/v1/ws/orders/customer/<user-uuid>");
#   ws.onmessage = (event) => {
#       const data = JSON.parse(event.data);
#       console.log("Order update:", data);
#   };
# ==========================================

async def handle_websocket(websocket: WebSocket, user_id: str):
    # 1. Register this connection under the user's ID
    await manager.connect(websocket, user_id)
    try:
        # Keep connection alive
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)


@router.websocket("/orders/customer/{user_id}")
async def websocket_customer_order_updates(websocket: WebSocket, user_id: str):
    """Endpoint for customers to receive order updates."""
    await handle_websocket(websocket, user_id)


@router.websocket("/orders/merchant/{user_id}")
async def websocket_merchant_order_updates(websocket: WebSocket, user_id: str):
    """Endpoint for merchants to receive new orders."""
    await handle_websocket(websocket, user_id)
