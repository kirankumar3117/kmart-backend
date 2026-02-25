# 📦 Pre-Order & Pickup Flow

## Overview

Customers can place **pre-orders** with a scheduled pickup time, and shopkeepers receive **real-time WebSocket notifications** the moment an order lands. When the shopkeeper marks an order as "ready," the customer gets a `pickup_ready` push.

---

## Order Types

| Type | Description | `scheduled_pickup_time` |
|------|-------------|------------------------|
| `instant` | Walk-in / immediate order (default) | Not required |
| `pre_order` | Customer schedules a pickup time | **Required**, must be in the future |

---

## Order Status Lifecycle

```
pending → confirmed → preparing → ready → picked_up
                                       ↘ cancelled
```

| Status | Set By | WebSocket Notification |
|--------|--------|----------------------|
| `pending` | System (on create) | `new_order` → **shopkeeper** |
| `confirmed` | Shopkeeper | `order_update` → customer |
| `preparing` | Shopkeeper | `order_update` → customer |
| `ready` | Shopkeeper | `pickup_ready` → **customer** |
| `picked_up` | Shopkeeper | `order_update` → customer |
| `cancelled` | Shopkeeper | `order_update` → customer |

---

## API Usage

### 1. Place a Pre-Order (Customer)

```bash
POST /api/v1/orders/
Authorization: Bearer <customer_token>
```

```json
{
  "shop_id": 1,
  "order_type": "pre_order",
  "scheduled_pickup_time": "2026-02-26T17:00:00+05:30",
  "order_notes": "Will come at 5 PM sharp",
  "items": [
    { "product_id": 1, "quantity": 2 }
  ]
}
```

### 2. Shopkeeper Confirms + Sets Prep Time

```bash
PATCH /api/v1/orders/{order_id}
Authorization: Bearer <shopkeeper_token>
```

```json
{
  "status": "confirmed",
  "estimated_preparation_minutes": 20
}
```

### 3. Shopkeeper Marks Ready

```json
{ "status": "ready" }
```

Customer receives a `pickup_ready` WebSocket push ✅

### 4. Filter Shop Orders by Type/Status

```bash
GET /api/v1/orders/shop/{shop_id}?order_type=pre_order&status=pending
```

---

## WebSocket Messages

### `new_order` (→ Shopkeeper)

Triggered when any customer places an order at the shop.

```json
{
  "type": "new_order",
  "order_id": 15,
  "customer_name": "Kiran Kumar",
  "order_type": "pre_order",
  "scheduled_pickup_time": "2026-02-26T17:00:00+05:30",
  "total_amount": 120.0,
  "item_count": 3,
  "has_chitty": false
}
```

### `pickup_ready` (→ Customer)

Triggered when shopkeeper sets status to `"ready"`.

```json
{
  "type": "pickup_ready",
  "order_id": 15,
  "shop_id": 2,
  "status": "ready",
  "estimated_preparation_minutes": 15,
  "message": "Your order is ready for pickup!"
}
```

### `order_update` (→ Customer)

Triggered on any other status change (confirmed, preparing, etc.).

```json
{
  "type": "order_update",
  "order_id": 15,
  "shop_id": 2,
  "status": "confirmed",
  "total_amount": 120.0,
  "estimated_preparation_minutes": 20,
  "updated_at": "2026-02-26T11:35:00+05:30"
}
```

---

## Database Changes

Three new columns added to the `orders` table:

| Column | Type | Default | Notes |
|--------|------|---------|-------|
| `order_type` | String | `"instant"` | `"instant"` or `"pre_order"` |
| `scheduled_pickup_time` | DateTime (TZ) | NULL | Required for pre-orders |
| `estimated_preparation_minutes` | Integer | NULL | Set by shopkeeper |

Migration: `alembic revision --autogenerate -m "add pre_order fields to orders"`
