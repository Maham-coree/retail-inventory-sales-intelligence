"""Add reports and isolated database lab objects.

Revision ID: 0004_db_objects
Revises: 0003_app_users
"""

from alembic import op

revision = "0004_db_objects"
down_revision = "0003_app_users"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE MATERIALIZED VIEW retail.mv_monthly_sales AS
        SELECT date_trunc('month', s.sale_date)::date AS month,
               s.store_id,
               st.store_name,
               count(*)::bigint AS invoices,
               sum(s.total_amount)::numeric(14,2) AS revenue
        FROM retail.sales s
        JOIN retail.stores st ON st.store_id = s.store_id
        GROUP BY date_trunc('month', s.sale_date)::date, s.store_id, st.store_name
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX idx_mv_monthly_sales_month_store "
        "ON retail.mv_monthly_sales USING btree(month, store_id)"
    )
    op.execute(
        """
        CREATE OR REPLACE PROCEDURE retail.sp_adjust_stock(
            p_store_id integer,
            p_product_id integer,
            p_delta integer,
            p_reason text
        )
        LANGUAGE plpgsql
        AS $$
        DECLARE current_qty integer;
        BEGIN
            IF p_delta = 0 THEN
                RAISE EXCEPTION 'Stock adjustment delta must not be zero'
                    USING ERRCODE = '23514';
            END IF;
            INSERT INTO retail.inventory(store_id, product_id, quantity_on_hand)
            VALUES (p_store_id, p_product_id, 0)
            ON CONFLICT (store_id, product_id) DO NOTHING;
            SELECT quantity_on_hand INTO current_qty
            FROM retail.inventory
            WHERE store_id = p_store_id AND product_id = p_product_id
            FOR UPDATE;
            IF current_qty + p_delta < 0 THEN
                RAISE EXCEPTION 'Adjustment would make stock negative for product %', p_product_id
                    USING ERRCODE = '23514';
            END IF;
            UPDATE retail.inventory
            SET quantity_on_hand = current_qty + p_delta, last_updated = now()
            WHERE store_id = p_store_id AND product_id = p_product_id;
            INSERT INTO retail.stock_movements(
                store_id, product_id, movement_type, quantity, reference
            )
            VALUES (p_store_id, p_product_id, 'ADJUSTMENT', p_delta, left(p_reason, 50));
        END
        $$;
        """
    )
    op.execute(
        """
        CREATE TABLE retail.lab_demo (
            item_id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            item_name text NOT NULL UNIQUE,
            qty integer NOT NULL DEFAULT 0
        )
        """
    )
    op.execute(
        """
        INSERT INTO retail.lab_demo(item_name, qty) VALUES
            ('seed-one', 10), ('seed-two', 20), ('seed-three', 30)
        ON CONFLICT (item_name) DO NOTHING
        """
    )
    op.execute(
        """
        CREATE TABLE retail.lab_orders (
            id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            customer_ref text NOT NULL,
            amount numeric(12,2) NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        DO $$
        DECLARE role_name text;
        BEGIN
            FOREACH role_name IN ARRAY ARRAY['role_admin', 'role_manager', 'role_cashier']
            LOOP
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = role_name) THEN
                    EXECUTE format(
                        'GRANT SELECT ON retail.mv_monthly_sales TO %I',
                        role_name
                    );
                    EXECUTE format(
                        'GRANT EXECUTE ON PROCEDURE retail.sp_adjust_stock(integer, integer, integer, text) TO %I',
                        role_name
                    );
                END IF;
            END LOOP;
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'role_admin') THEN
                GRANT SELECT, INSERT, UPDATE, DELETE ON retail.lab_demo, retail.lab_orders TO role_admin;
                GRANT USAGE, SELECT ON SEQUENCE retail.lab_demo_item_id_seq TO role_admin;
                GRANT USAGE, SELECT ON SEQUENCE retail.lab_orders_id_seq TO role_admin;
            END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    op.execute("DROP PROCEDURE IF EXISTS retail.sp_adjust_stock(integer, integer, integer, text)")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS retail.mv_monthly_sales")
    op.execute("DROP TABLE IF EXISTS retail.lab_orders")
    op.execute("DROP TABLE IF EXISTS retail.lab_demo")
