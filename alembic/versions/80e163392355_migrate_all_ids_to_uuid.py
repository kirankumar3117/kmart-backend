"""migrate_all_ids_to_uuid

Revision ID: 80e163392355
Revises: 217f1b975253
Create Date: 2026-03-15 18:37:50.753200

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '80e163392355'
down_revision: Union[str, Sequence[str], None] = '217f1b975253'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1: Drop all FK constraints that reference the INTEGER PK tables being converted.
    # Using a DO block so we don't need to hard-code auto-generated constraint names.
    op.execute("""
        DO $$
        DECLARE
            r RECORD;
        BEGIN
            FOR r IN (
                SELECT tc.table_name, tc.constraint_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.referential_constraints rc
                    ON tc.constraint_name = rc.constraint_name
                JOIN information_schema.table_constraints tc2
                    ON rc.unique_constraint_name = tc2.constraint_name
                WHERE tc2.table_name IN (
                    'users', 'products', 'orders', 'product_categories',
                    'cart_suggestions', 'inventory_items', 'order_items'
                )
                AND tc.constraint_type = 'FOREIGN KEY'
            )
            LOOP
                EXECUTE format('ALTER TABLE %I DROP CONSTRAINT %I', r.table_name, r.constraint_name);
            END LOOP;
        END $$;
    """)

    # Step 2: Convert INTEGER PK columns to UUID.
    # Must drop the SERIAL default before altering type, then set a UUID default.
    for table in ['cart_suggestions', 'inventory_items', 'order_items', 'orders',
                  'product_categories', 'products', 'users']:
        op.execute(f"ALTER TABLE {table} ALTER COLUMN id DROP DEFAULT")
        op.execute(f"DROP SEQUENCE IF EXISTS {table}_id_seq")
        op.execute(f"ALTER TABLE {table} ALTER COLUMN id TYPE UUID USING gen_random_uuid()")
        op.execute(f"ALTER TABLE {table} ALTER COLUMN id SET DEFAULT gen_random_uuid()")

    # Step 3: Convert INTEGER FK columns to UUID.
    op.execute("ALTER TABLE cart_suggestions ALTER COLUMN order_id TYPE UUID USING gen_random_uuid()")
    op.execute("ALTER TABLE cart_suggestions ALTER COLUMN product_id TYPE UUID USING gen_random_uuid()")
    op.execute("ALTER TABLE inventory_items ALTER COLUMN product_id TYPE UUID USING gen_random_uuid()")
    op.execute("ALTER TABLE order_items ALTER COLUMN order_id TYPE UUID USING gen_random_uuid()")
    op.execute("ALTER TABLE order_items ALTER COLUMN product_id TYPE UUID USING gen_random_uuid()")
    op.execute("ALTER TABLE orders ALTER COLUMN customer_id TYPE UUID USING gen_random_uuid()")
    op.execute("ALTER TABLE product_category_link ALTER COLUMN product_id TYPE UUID USING gen_random_uuid()")
    op.execute("ALTER TABLE product_category_link ALTER COLUMN category_id TYPE UUID USING gen_random_uuid()")
    op.execute("ALTER TABLE products ALTER COLUMN merchant_id TYPE UUID USING gen_random_uuid()")
    op.execute("ALTER TABLE shops ALTER COLUMN owner_id TYPE UUID USING gen_random_uuid()")
    op.execute("ALTER TABLE shops ALTER COLUMN onboarded_by_agent_id TYPE UUID USING gen_random_uuid()")

    # Step 4: Recreate FK constraints with the correct UUID types.
    op.execute("ALTER TABLE inventory_items ADD CONSTRAINT inventory_items_product_id_fkey FOREIGN KEY (product_id) REFERENCES products(id)")
    op.execute("ALTER TABLE orders ADD CONSTRAINT orders_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES users(id)")
    op.execute("ALTER TABLE cart_suggestions ADD CONSTRAINT cart_suggestions_order_id_fkey FOREIGN KEY (order_id) REFERENCES orders(id)")
    op.execute("ALTER TABLE cart_suggestions ADD CONSTRAINT cart_suggestions_product_id_fkey FOREIGN KEY (product_id) REFERENCES products(id)")
    op.execute("ALTER TABLE order_items ADD CONSTRAINT order_items_order_id_fkey FOREIGN KEY (order_id) REFERENCES orders(id)")
    op.execute("ALTER TABLE order_items ADD CONSTRAINT order_items_product_id_fkey FOREIGN KEY (product_id) REFERENCES products(id)")
    op.execute("ALTER TABLE product_category_link ADD CONSTRAINT product_category_link_category_id_fkey FOREIGN KEY (category_id) REFERENCES product_categories(id) ON DELETE CASCADE")
    op.execute("ALTER TABLE product_category_link ADD CONSTRAINT product_category_link_product_id_fkey FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE")
    op.execute("ALTER TABLE products ADD CONSTRAINT products_merchant_id_fkey FOREIGN KEY (merchant_id) REFERENCES users(id)")
    op.execute("ALTER TABLE shops ADD CONSTRAINT shops_owner_id_fkey FOREIGN KEY (owner_id) REFERENCES users(id)")
    op.execute("ALTER TABLE shops ADD CONSTRAINT shops_onboarded_by_agent_id_fkey FOREIGN KEY (onboarded_by_agent_id) REFERENCES users(id)")


def downgrade() -> None:
    op.alter_column('users', 'id',
               existing_type=sa.UUID(),
               type_=sa.INTEGER(),
               existing_nullable=False)
    op.alter_column('shops', 'onboarded_by_agent_id',
               existing_type=sa.UUID(),
               type_=sa.INTEGER(),
               existing_nullable=True)
    op.alter_column('shops', 'owner_id',
               existing_type=sa.UUID(),
               type_=sa.INTEGER(),
               existing_nullable=True)
    op.alter_column('products', 'merchant_id',
               existing_type=sa.UUID(),
               type_=sa.INTEGER(),
               existing_nullable=False)
    op.alter_column('products', 'id',
               existing_type=sa.UUID(),
               type_=sa.INTEGER(),
               existing_nullable=False)
    op.alter_column('product_category_link', 'category_id',
               existing_type=sa.UUID(),
               type_=sa.INTEGER(),
               existing_nullable=False)
    op.alter_column('product_category_link', 'product_id',
               existing_type=sa.UUID(),
               type_=sa.INTEGER(),
               existing_nullable=False)
    op.alter_column('product_categories', 'id',
               existing_type=sa.UUID(),
               type_=sa.INTEGER(),
               existing_nullable=False)
    op.alter_column('orders', 'customer_id',
               existing_type=sa.UUID(),
               type_=sa.INTEGER(),
               existing_nullable=False)
    op.alter_column('orders', 'id',
               existing_type=sa.UUID(),
               type_=sa.INTEGER(),
               existing_nullable=False)
    op.alter_column('order_items', 'product_id',
               existing_type=sa.UUID(),
               type_=sa.INTEGER(),
               existing_nullable=True)
    op.alter_column('order_items', 'order_id',
               existing_type=sa.UUID(),
               type_=sa.INTEGER(),
               existing_nullable=False)
    op.alter_column('order_items', 'id',
               existing_type=sa.UUID(),
               type_=sa.INTEGER(),
               existing_nullable=False)
    op.alter_column('inventory_items', 'product_id',
               existing_type=sa.UUID(),
               type_=sa.INTEGER(),
               existing_nullable=False)
    op.alter_column('inventory_items', 'id',
               existing_type=sa.UUID(),
               type_=sa.INTEGER(),
               existing_nullable=False)
    op.alter_column('cart_suggestions', 'product_id',
               existing_type=sa.UUID(),
               type_=sa.INTEGER(),
               existing_nullable=True)
    op.alter_column('cart_suggestions', 'order_id',
               existing_type=sa.UUID(),
               type_=sa.INTEGER(),
               existing_nullable=False)
    op.alter_column('cart_suggestions', 'id',
               existing_type=sa.UUID(),
               type_=sa.INTEGER(),
               existing_nullable=False)
