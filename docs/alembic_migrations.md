# 🔄 Alembic — Database Migrations

## Why Alembic?

Previously, the app used `Base.metadata.create_all()` which only creates **new** tables — it can't modify existing tables (add columns, change types, etc.). To apply model changes, you had to `docker-compose down -v` and lose all data!

**Alembic** tracks every schema change as a versioned **migration script**, so you can:
- Add/remove columns without data loss
- Roll back changes if something breaks
- Keep your database schema in sync with your SQLAlchemy models

## Quick Reference

```bash
# After changing any model (adding columns, new tables, etc.):
alembic revision --autogenerate -m "describe what changed"

# Apply the migration to your database:
alembic upgrade head

# Roll back the last migration:
alembic downgrade -1

# See current migration version:
alembic current

# See migration history:
alembic history
```

## How It Works

```
1. You modify a model         → e.g., add "phone" column to Shop
2. Run autogenerate            → Alembic compares models vs DB, generates a script
3. Review the script          → alembic/versions/xxxx_description.py
4. Run upgrade                 → Alembic applies the changes to PostgreSQL
```

## Project Setup

### Files Created

```
kmart-backend/
├── alembic.ini                  # Alembic config (DB URL set via env.py)
└── alembic/
    ├── env.py                   # Loads our models + DATABASE_URL from .env
    ├── script.py.mako           # Template for new migration files
    └── versions/
        └── 37fb97fb287b_initial_schema.py  # First migration
```

### What Changed in `main.py`

```python
# BEFORE (old way):
Base.metadata.create_all(bind=engine)

# AFTER (Alembic way):
# Previously: Base.metadata.create_all(bind=engine)
# Now we use Alembic! Run: alembic upgrade head
```

### How `env.py` Works

```python
# 1. Imports our Settings to get DATABASE_URL from .env
from app.core.config import settings
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# 2. Imports ALL models so Alembic can detect changes
from app.models import user, product, shop, inventory, order, cart_suggestion

# 3. Points at our Base.metadata for autogenerate
target_metadata = Base.metadata
```

## Common Workflows

### Adding a new column

```python
# 1. Edit the model (e.g., app/models/shop.py)
class Shop(Base):
    # ... existing columns ...
    phone = Column(String, nullable=True)  # NEW!

# 2. Generate migration
alembic revision --autogenerate -m "add phone column to shops"

# 3. Apply it
alembic upgrade head
```

### Adding a new table

```python
# 1. Create new model file (e.g., app/models/delivery.py)

# 2. Import it in alembic/env.py:
from app.models import ..., delivery

# 3. Import it in app/main.py (for model registration):
from app.models import ..., delivery

# 4. Generate and apply
alembic revision --autogenerate -m "add delivery table"
alembic upgrade head
```

### Rolling back

```bash
# Undo the last migration
alembic downgrade -1

# Go back to a specific version
alembic downgrade 37fb97fb287b
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Target database is not up to date" | Run `alembic upgrade head` |
| Empty migration generated | Make sure you imported the model in `env.py` |
| "Can't locate revision" | Run `alembic stamp head` to reset tracking |
| Want to start fresh | `alembic stamp head` marks current DB as latest |

## Files Involved

- `alembic.ini` → Config file (DB URL sourced from env.py)
- `alembic/env.py` → Loads models + DATABASE_URL
- `alembic/versions/` → All migration scripts
- `app/main.py` → `create_all()` removed, Alembic handles migrations
