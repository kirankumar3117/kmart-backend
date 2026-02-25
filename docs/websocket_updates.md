# 🔔 WebSocket — Real-Time Order Updates

## Endpoint

```
ws://localhost:8000/ws/orders/{user_id}
```

## What It Does

Gives customers **instant push notifications** when a shopkeeper updates their order — no need to keep refreshing!

## How It Works

```
1. Customer opens a WebSocket connection to /ws/orders/{user_id}
2. Connection is stored in a global ConnectionManager (per user_id)
3. Shopkeeper calls PATCH /api/v1/orders/{order_id} to update status
4. Backend pushes the update to ALL of that customer's WebSocket connections
5. Customer's phone/app receives the update instantly
```

## Frontend Usage (React Native / JavaScript)

```javascript
// Connect when the app opens
const ws = new WebSocket("ws://your-server/ws/orders/42");

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    if (data.type === "order_update") {
        // Shopkeeper changed order status!
        console.log(`Order #${data.order_id} is now: ${data.status}`);
        console.log(`Total: ₹${data.total_amount}`);
    }
    
    if (data.type === "chitty_processed") {
        // OCR finished processing the handwritten list!
        console.log(`Found ${data.items_found} products from your list`);
    }
};

ws.onclose = () => {
    console.log("Disconnected — reconnect logic here");
};
```

## Message Types

### `order_update` — Sent to CUSTOMER

Triggered when: shopkeeper calls `PATCH /api/v1/orders/{order_id}`

```json
{
    "type": "order_update",
    "order_id": 7,
    "shop_id": 1,
    "status": "ready",
    "total_amount": 450.0,
    "updated_at": "2025-02-26T12:00:00"
}
```

### `chitty_processed` — Sent to SHOPKEEPER

Triggered when: OCR finishes processing a handwritten list image.

```json
{
    "type": "chitty_processed",
    "order_id": 12,
    "items_found": 4,
    "total_lines": 6,
    "message": "OCR complete! Found 4 product matches from 6 lines."
}
```

## Multi-Device Support

A user can have **multiple WebSocket connections** simultaneously (e.g., phone + tablet). All connections receive the same updates.

## Files Involved

- `app/core/ws_manager.py` → `ConnectionManager` (stores connections per user_id)
- `app/api/ws.py` → WebSocket endpoint
- `app/api/orders.py` → `update_order()` triggers the push
