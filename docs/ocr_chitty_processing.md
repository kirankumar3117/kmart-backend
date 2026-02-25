# 📸 OCR Chitty Processing — Background Task

## What It Does

When a customer uploads a **handwritten grocery list** (chitty) and creates an order, a background task automatically:

1. **Extracts text** from the image using Tesseract OCR
2. **Fuzzy-matches** each line to product names in the database
3. **Saves suggestions** for the shopkeeper to review
4. **Notifies the shopkeeper** via WebSocket

## Prerequisites

```bash
# Install Tesseract OCR engine
brew install tesseract

# Install Python dependencies
pip install pytesseract Pillow
```

## Flow

```
Customer uploads image      → POST /api/v1/upload
Customer creates order      → POST /api/v1/orders { list_image_url: "/static/chitty_abc.jpg" }
                               ↓ (automatic)
Background task starts      → Tesseract extracts text from image
                               ↓
Fuzzy matching runs         → Each line matched against products DB
                               ↓
Suggestions saved           → cart_suggestions table in PostgreSQL
                               ↓
WebSocket notification      → Shopkeeper gets { type: "chitty_processed", items_found: 4 }
                               ↓
Shopkeeper views results    → GET /api/v1/orders/{order_id}/suggestions
```

## API Endpoint

### Get OCR Suggestions

```
GET /api/v1/orders/{order_id}/suggestions
```

**Auth:** 🔒 Shopkeeper or the customer who placed the order

### Example Response

```json
[
  {
    "id": 1,
    "order_id": 12,
    "extracted_text": "Aashirvaad Atta 10kg",
    "product_id": 1,
    "product_name": "Aashirvaad Shudh Chakki Atta",
    "confidence": 0.85,
    "status": "suggested"
  },
  {
    "id": 2,
    "order_id": 12,
    "extracted_text": "Maggi noodles",
    "product_id": 6,
    "product_name": "Maggi Noodles 12-Pack",
    "confidence": 0.72,
    "status": "suggested"
  },
  {
    "id": 3,
    "order_id": 12,
    "extracted_text": "Salt 1kg",
    "product_id": null,
    "product_name": null,
    "confidence": 0.0,
    "status": "suggested"
  }
]
```

> **confidence** ranges from 0.0 to 1.0. Items with `product_id: null` had no match.

## How Fuzzy Matching Works

- Uses Python's `difflib.SequenceMatcher` to compare OCR text against all product names
- **Partial match boost**: If the OCR text contains a product name (or vice-versa), confidence is boosted to ≥ 0.75
- **Threshold**: Only matches with confidence > 0.40 are linked to a product
- Unmatched lines are still saved (with `product_id: null`) so the shopkeeper can manually identify them

## Database Model — `cart_suggestions`

| Column | Type | Description |
|--------|------|-------------|
| `id` | int | Primary key |
| `order_id` | int | FK → orders |
| `extracted_text` | string | Raw OCR text line |
| `product_id` | int (nullable) | FK → products (null if no match) |
| `product_name` | string (nullable) | Matched product name |
| `confidence` | float | Match confidence (0.0 – 1.0) |
| `status` | string | `"suggested"`, `"accepted"`, or `"rejected"` |

## Files Involved

- `app/services/ocr.py` → OCR extraction + fuzzy matching + background task
- `app/models/cart_suggestion.py` → `CartSuggestion` SQLAlchemy model
- `app/schemas/cart_suggestion.py` → `CartSuggestionResponse` Pydantic schema
- `app/api/orders.py` → Background task trigger + suggestions endpoint
