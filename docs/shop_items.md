# 🛍️ Shop Items — Product + Inventory Joined View

## Endpoint

```
GET /api/v1/shops/{shop_id}/items
```

## What It Does

When a customer clicks on a shop, this returns **all products that shop currently has in stock** — combining product details from the master catalog with the shop's own price and stock.

## Query Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `shop_id` | int | ✅ (path) | — | The shop to browse |
| `skip` | int | ❌ | 0 | Pagination offset |
| `limit` | int | ❌ | 100 | Max results |

## How It Works

Performs a SQL **JOIN** between `InventoryItem` and `Product`:

```
InventoryItem (shop_id, product_id, price, stock)
       ↕ JOIN ON product_id
Product (name, category, image_url, mrp, unit)
```

**Filters applied:**
- `stock > 0` — only in-stock items
- `is_active = True` — only active products

## Example Response

```json
[
  {
    "inventory_id": 5,
    "product_id": 1,
    "product_name": "Aashirvaad Shudh Chakki Atta",
    "category": "Staples",
    "image_url": "https://...",
    "mrp": 540.0,
    "unit": "10 kg",
    "price": 499.0,
    "stock": 25
  }
]
```

> **Note:** `mrp` is the Max Retail Price from the catalog. `price` is what this specific shop charges.

## Files Involved

- `app/api/shops.py` → `get_shop_items()`
- `app/schemas/inventory.py` → `ShopItemResponse`
