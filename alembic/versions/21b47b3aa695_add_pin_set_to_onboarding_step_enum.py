"""add_pin_set_to_onboarding_step_enum

Revision ID: 21b47b3aa695
Revises: 11b232c80aca
Create Date: 2026-02-27 02:48:44.162729

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '21b47b3aa695'
down_revision: Union[str, Sequence[str], None] = '11b232c80aca'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add 'PIN_SET' value to the onboarding_step_enum Postgres enum type.
    
    Postgres doesn't support adding enum values with --autogenerate,
    so we use raw DDL. The IF NOT EXISTS guard makes it idempotent.
    NOTE: The existing DB enum values are uppercase (REGISTERED, VERIFIED, COMPLETED)
    as created by the initial migration. PIN_SET must also be uppercase.
    """
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_enum
                WHERE enumlabel = 'PIN_SET'
                AND enumtypid = (
                    SELECT oid FROM pg_type WHERE typname = 'onboarding_step_enum'
                )
            ) THEN
                ALTER TYPE onboarding_step_enum ADD VALUE 'PIN_SET' BEFORE 'COMPLETED';
            END IF;
        END$$;
    """)


def downgrade() -> None:
    """Remove 'PIN_SET' from the onboarding_step_enum type.
    
    Postgres cannot drop individual enum values. We must:
    1. Set any PIN_SET rows back to 'VERIFIED'
    2. Create new enum without PIN_SET
    3. Swap the column to use new enum
    4. Drop old enum, rename new one
    """
    # Move any PIN_SET rows back to VERIFIED
    op.execute("UPDATE shops SET onboarding_step = 'VERIFIED' WHERE onboarding_step = 'PIN_SET'")
    
    # Recreate enum without PIN_SET
    op.execute("CREATE TYPE onboarding_step_enum_new AS ENUM ('REGISTERED', 'VERIFIED', 'COMPLETED')")
    op.execute("ALTER TABLE shops ALTER COLUMN onboarding_step TYPE onboarding_step_enum_new USING onboarding_step::text::onboarding_step_enum_new")
    op.execute("DROP TYPE onboarding_step_enum")
    op.execute("ALTER TYPE onboarding_step_enum_new RENAME TO onboarding_step_enum")
