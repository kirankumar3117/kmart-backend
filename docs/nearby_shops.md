# 📡 Nearby Shops — Haversine Distance Search

## Endpoint

```
GET /api/v1/shops/nearby?user_lat=17.385&user_lng=78.4867
```

## What It Does

Finds all shops **within a radius** of the user's GPS location, sorted **nearest first**.

## Query Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `user_lat` | float | ✅ | — | User's latitude |
| `user_lng` | float | ✅ | — | User's longitude |
| `radius_km` | float | ❌ | 10.0 | Search radius in kilometers |
| `skip` | int | ❌ | 0 | Pagination offset |
| `limit` | int | ❌ | 100 | Max results |

## How It Works

Uses the **Haversine Formula** computed directly in PostgreSQL:

```
d = 2R × arcsin(√(sin²((Δlat)/2) + cos(lat1)·cos(lat2)·sin²((Δlng)/2)))
```

- `R = 6371 km` (Earth's radius)
- Shops without `latitude`/`longitude` are skipped
- Only active shops are returned

## Example Response

```json
[
  {
    "id": 1,
    "name": "Raju Kirana Store",
    "category": "Grocery",
    "address": "123 Main Road, Hyderabad",
    "latitude": 17.390,
    "longitude": 78.490,
    "owner_id": 2,
    "is_active": true,
    "distance_km": 0.63
  }
]
```

## Files Involved

- `app/api/shops.py` → `get_nearby_shops()`
- `app/schemas/shop.py` → `ShopNearbyResponse`
