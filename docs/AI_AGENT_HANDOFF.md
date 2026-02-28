# 🤖 Smart Kirana Backend — AI Agent Handoff Document

**Date:** February 26, 2026  
**Project:** Smart Kirana (kmart-backend)  
**Repo:** https://github.com/kirankumar3117/kmart-backend  
**Branch:** `main`  
**Tech Stack:** FastAPI + PostgreSQL 16 + SQLAlchemy + Alembic + JWT Auth  
**Python:** 3.14 (venv at `./venv`)  
**Database:** PostgreSQL via Docker on port `5433` (container: `kmart_db_container`)

---

## 📌 What Is This Project?

Smart Kirana is a backend API for a **local grocery store marketplace** (Indian kirana stores). It connects **customers** with **merchants**. Customers can browse nearby shops, view products, place orders (including uploading handwritten grocery lists called "chitties"), and get real-time updates when the merchant processes their order.

---

## 🏗️ Complete Architecture

```
kmart-backend/
├── app/
│   ├── main.py                    # FastAPI app entry point, route registration
│   ├── __init__.py
│   ├── api/                       # All API route handlers
│   │   ├── auth.py                # POST /register, POST /login
│   │   ├── products.py            # POST /, GET / (search/filter)
│   │   ├── shops.py               # POST /, GET /, GET /nearby, GET /{shop_id}/items
│   │   ├── inventory.py           # POST /, GET /shop/{shop_id}, PATCH /{item_id}
│   │   ├── orders.py              # POST /, GET /shop/{id}, PATCH /{id}, GET /me, GET /{id}/suggestions
│   │   ├── upload.py              # POST / (image upload)
│   │   └── ws.py                  # WebSocket /orders/{user_id}
│   ├── models/                    # SQLAlchemy ORM models
│   │   ├── user.py                # User (customer/merchant/agent)
│   │   ├── product.py             # Product (master catalog)
│   │   ├── shop.py                # Shop (with lat/lng geolocation)
│   │   ├── inventory.py           # InventoryItem (shop ↔ product bridge)
│   │   ├── order.py               # Order + OrderItem
│   │   └── cart_suggestion.py     # CartSuggestion (OCR results)
│   ├── schemas/                   # Pydantic request/response schemas
│   │   ├── user.py                # UserCreate, UserLogin, UserResponse
│   │   ├── product.py             # ProductCreate, ProductResponse
│   │   ├── shop.py                # ShopCreate, ShopResponse, ShopNearbyResponse
│   │   ├── inventory.py           # InventoryCreate, InventoryResponse, InventoryUpdate, ShopItemResponse
│   │   ├── order.py               # OrderCreate, OrderResponse, OrderUpdate, OrderItemCreate/Response
│   │   └── cart_suggestion.py     # CartSuggestionResponse
│   ├── core/
│   │   ├── config.py              # Settings via pydantic-settings (.env)
│   │   ├── security.py            # bcrypt hashing + JWT creation
│   │   └── ws_manager.py          # WebSocket ConnectionManager (per user_id)
│   ├── db/
│   │   ├── base.py                # SQLAlchemy declarative Base
│   │   └── session.py             # Engine + SessionLocal + get_db dependency
│   ├── services/
│   │   ├── __init__.py
│   │   └── ocr.py                 # Tesseract OCR + fuzzy product matching + background task
│   └── utils/
│       └── auth.py                # get_current_user (JWT decode + DB lookup)
├── alembic/                       # Database migrations
│   ├── env.py                     # Configured with our models + DATABASE_URL
│   ├── script.py.mako
│   └── versions/
│       └── 37fb97fb287b_initial_schema_*.py  # First migration (creates cart_suggestions)
├── docs/                          # Feature documentation
│   ├── nearby_shops.md
│   ├── shop_items.md
│   ├── websocket_updates.md
│   ├── ocr_chitty_processing.md
│   └── alembic_migrations.md
├── uploads/                       # Uploaded images (served at /static/)
├── alembic.ini                    # Alembic config (DB URL set dynamically in env.py)
├── docker-compose.yml             # PostgreSQL 16 container
├── requirements.txt               # All Python dependencies
├── seed_products.py               # Script to seed 6 sample products
├── README.md                      # Full project README with diagrams
└── .env                           # DATABASE_URL=postgresql://postgres:agent123@127.0.0.1:5433/kmart_db
```

---

## 🗄️ Database Tables (6 total)

### 1. `users`
| Column | Type | Notes |
|--------|------|-------|
| id | Integer PK | Auto-increment |
| full_name | String | Required |
| phone_number | String | Unique, required, primary login field |
| email | String | Optional, nullable |
| hashed_password | String | bcrypt hash |
| is_active | Boolean | Default true |
| role | String | `"customer"`, `"merchant"`, or `"agent"` |

### 2. `products` (master catalog)
| Column | Type | Notes |
|--------|------|-------|
| id | Integer PK | |
| name | String | e.g. "Aashirvaad Atta" |
| category | String | e.g. "Staples" |
| description | Text | Optional |
| image_url | String | Optional |
| mrp | Float | Max Retail Price |
| unit | String | e.g. "10 kg" |
| barcode | String | Unique, optional |
| is_active | Boolean | Default true |

### 3. `shops`
| Column | Type | Notes |
|--------|------|-------|
| id | Integer PK | |
| owner_id | Integer FK → users | The merchant who owns it |
| name | String | |
| category | String | |
| address | Text | |
| is_active | Boolean | Default true |
| latitude | Float | Nullable, for geolocation |
| longitude | Float | Nullable, for geolocation |

### 4. `inventory_items` (bridge: shop ↔ product)
| Column | Type | Notes |
|--------|------|-------|
| id | Integer PK | |
| shop_id | Integer FK → shops | |
| product_id | Integer FK → products | |
| price | Float | This shop's selling price |
| stock | Integer | Current stock count |

### 5. `orders` + `order_items`
**orders:**
| Column | Type | Notes |
|--------|------|-------|
| id | Integer PK | |
| customer_id | Integer FK → users | From JWT token |
| shop_id | Integer FK → shops | |
| total_amount | Float | Calculated or set by merchant |
| status | String | `"pending"` → `"confirmed"` → `"preparing"` → `"ready"` → `"picked_up"` / `"delivered"` / `"cancelled"` |
| order_type | String | `"instant"` (default) or `"pre_order"` |
| scheduled_pickup_time | DateTime | When customer wants to pick up (required for pre-orders) |
| estimated_preparation_minutes | Integer | merchant sets this on confirmation |
| list_image_url | String | Optional chitty photo URL |
| order_notes | Text | Optional delivery instructions |
| created_at | DateTime | Auto-set with timezone |

**order_items:**
| Column | Type | Notes |
|--------|------|-------|
| id | Integer PK | |
| order_id | Integer FK → orders | |
| product_id | Integer FK → products | **Nullable** (for chitty orders) |
| quantity | Integer | Default 1 |
| price_at_time_of_order | Float | Captured at checkout |
| special_instructions | String | e.g. "Make it extra spicy" |

### 6. `cart_suggestions` (OCR results)
| Column | Type | Notes |
|--------|------|-------|
| id | Integer PK | |
| order_id | Integer FK → orders | |
| extracted_text | String | Raw OCR line |
| product_id | Integer FK → products | Nullable (no match) |
| product_name | String | Matched product name |
| confidence | Float | 0.0 to 1.0 |
| status | String | "suggested", "accepted", "rejected" |

---

## 📡 All API Endpoints

### Auth — `/api/v1/auth`
| Method | Path | Auth | Body/Params |
|--------|------|------|-------------|
| POST | `/register` | Public | `{full_name, phone_number, password, email?, role?}` |
| POST | `/login` | Public | `{phone_number, password, role}` → returns `{access_token, token_type, role}` |

### Products — `/api/v1/products`
| Method | Path | Auth | Body/Params |
|--------|------|------|-------------|
| POST | `/` | Public* | `{name, category, mrp, unit, image_url?, barcode?}` |
| GET | `/` | Public | `?search=&category=&skip=&limit=` |

### Shops — `/api/v1/shops`
| Method | Path | Auth | Body/Params |
|--------|------|------|-------------|
| POST | `/` | 🔒 merchant | `{name, category, address, latitude?, longitude?}` |
| GET | `/` | Public | `?skip=&limit=` |
| GET | `/nearby` | Public | `?user_lat=&user_lng=&radius_km=10` (Haversine formula) |
| GET | `/{shop_id}/items` | Public | Returns joined Product+Inventory (in-stock only) |

### Inventory — `/api/v1/inventory`
| Method | Path | Auth | Body/Params |
|--------|------|------|-------------|
| POST | `/` | Public* | `{shop_id, product_id, price, stock}` |
| GET | `/shop/{shop_id}` | Public | List all inventory for a shop |
| PATCH | `/{item_id}` | Public* | `{price?, stock?}` |

### Orders — `/api/v1/orders`
| Method | Path | Auth | Body/Params |
|--------|------|------|-------------|
| POST | `/` | 🔒 Customer | `{shop_id, order_type?, scheduled_pickup_time?, items?[], list_image_url?, order_notes?}` — triggers OCR if image; pushes `new_order` WS to merchant |
| GET | `/shop/{shop_id}` | 🔒 merchant | All orders for a shop. Filters: `?order_type=pre_order&status=pending` |
| PATCH | `/{order_id}` | 🔒 merchant | `{status?, total_amount?, estimated_preparation_minutes?}` — pushes `order_update` or `pickup_ready` WS to customer |
| GET | `/me` | 🔒 Any user | Customer's own orders |
| GET | `/{order_id}/suggestions` | 🔒 merchant/Customer | OCR cart suggestions |

### Upload — `/api/v1/upload`
| Method | Path | Auth | Body/Params |
|--------|------|------|-------------|
| POST | `/` | Public | Multipart file upload → returns `{list_image_url}` |

### WebSocket — `/ws`
| Protocol | Path | Description |
|----------|------|-------------|
| WS | `/orders/{user_id}` | Customer subscribes for real-time order updates |

---

## 🔑 Authentication System

- **Login:** Phone number + password + role → JWT token (7-day expiry)
- **JWT payload:** `{"sub": "<user_id>", "exp": <timestamp>}`
- **Secret key:** Defined in `config.py` (should be overridden in `.env`)
- **Algorithm:** HS256
- **Protected routes** use `Depends(get_current_user)` which decodes JWT and fetches user from DB
- **Role checks** are done inline (e.g., `if current_user.role != "merchant"`)

---

## 🔔 WebSocket System

**File:** `app/core/ws_manager.py`

- `ConnectionManager` stores connections in a dict: `{user_id: [websocket1, websocket2, ...]}`
- Supports **multi-device** (same user can connect from phone + tablet)
- Cleans up dead connections automatically

**Four message types pushed:**
1. `new_order` → sent to **merchant** when a customer places any order (from `orders.py`)
2. `order_update` → sent to **customer** when merchant updates order status (from `orders.py`)
3. `pickup_ready` → sent to **customer** when merchant sets status to `"ready"` (from `orders.py`)
4. `chitty_processed` → sent to **merchant** when OCR finishes (from `ocr.py`)

---

## 📸 OCR Chitty System

**File:** `app/services/ocr.py`

1. **Tesseract OCR** extracts text from uploaded image
2. **Fuzzy matching** via `difflib.SequenceMatcher` compares each line against all product names
3. Partial match boost: if OCR text contains product name → confidence ≥ 0.75
4. Only matches with confidence > 0.40 are linked
5. Results saved as `CartSuggestion` records
6. merchant notified via WebSocket

**Dependencies:** `brew install tesseract` + `pip install pytesseract Pillow`

---

## 🔄 Database Migrations (Alembic)

**Setup:** Fully configured in `alembic/env.py` — reads `DATABASE_URL` from `.env` and imports all models.

**`Base.metadata.create_all()` has been REMOVED from `main.py`.** All schema changes go through Alembic now.

**Workflow:**
```bash
# After changing models:
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

**Migrations:**
- `37fb97fb287b` — creates `cart_suggestions` table
- `7ea804cba73a` — adds `order_type`, `scheduled_pickup_time`, `estimated_preparation_minutes` to `orders`

---

## 📦 Dependencies (`requirements.txt`)

```
fastapi
uvicorn
sqlalchemy
psycopg2-binary
pydantic-settings
python-dotenv
pytesseract
Pillow
alembic
```

**System dependency:** `tesseract` (installed via `brew install tesseract`)

---

## 🐳 Docker / Database

```yaml
# docker-compose.yml
services:
  postgres:
    image: postgres:16-alpine
    container_name: kmart_db_container
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: agent123
      POSTGRES_DB: kmart_db
    ports:
      - "5433:5432"  # Maps to HOST port 5433
```

```
# .env
DATABASE_URL=postgresql://postgres:agent123@127.0.0.1:5433/kmart_db
```

---

## ⚠️ Known Issues / TODO

1. **Some endpoints lack auth protection** — product creation, inventory add/update are currently public (marked with * in the endpoint table)
2. **No CORS middleware** — `main.py` doesn't have `CORSMiddleware` configured yet (needed for frontend)
3. **`SECRET_KEY`** has a hardcoded default in `config.py` — should be set in `.env` for production
4. **No automated tests** — no test files exist yet
5. **`shops.py`** — the `status` import was fixed (was previously missing)
6. **File uploads** are stored locally in `uploads/` — no cloud storage (S3, etc.)
7. **OCR accuracy** depends on handwriting quality and Tesseract's capabilities

---

## 🏃 How to Run

```bash
# 1. Start PostgreSQL
docker-compose up -d

# 2. Activate venv
source venv/bin/activate

# 3. Run migrations
alembic upgrade head

# 4. Start the server
uvicorn app.main:app --reload

# 5. Open docs
open http://localhost:8000/docs
```

---

## 📂 Documentation Files

All feature docs live in `docs/`:
- `docs/nearby_shops.md` — Haversine distance search
- `docs/shop_items.md` — Product + Inventory joined view
- `docs/websocket_updates.md` — Real-time WebSocket system
- `docs/ocr_chitty_processing.md` — Background OCR task
- `docs/alembic_migrations.md` — Migration setup and workflow
- `docs/preorder_pickup_flow.md` — Pre-order scheduling & pickup notifications
