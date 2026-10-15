"""Add application users and role grants.

Revision ID: 0003_app_users
Revises: None
"""

from alembic import op

revision = "0003_app_users"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE retail.app_users (
            user_id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            public_id uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
            username varchar(80) NOT NULL UNIQUE,
            password_hash text NOT NULL,
            role varchar(20) NOT NULL
                CHECK (role IN ('admin', 'manager', 'cashier')),
            employee_id integer NULL
                REFERENCES retail.employees(employee_id) ON DELETE SET NULL,
            is_active boolean NOT NULL DEFAULT true,
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
                        'GRANT SELECT, INSERT, UPDATE, DELETE ON retail.app_users TO %I',
                        role_name
                    );
                    EXECUTE format(
                        'GRANT USAGE, SELECT ON SEQUENCE retail.app_users_user_id_seq TO %I',
                        role_name
                    );
                END IF;
            END LOOP;
        END
        $$;
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS retail.app_users")
