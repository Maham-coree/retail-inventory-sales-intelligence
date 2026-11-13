"""Add user-owned chatbot conversation history.

Revision ID: 0006_chatbot
Revises: 0005_add_barcode
"""

from alembic import op

revision = "0006_chatbot"
down_revision = "0005_add_barcode"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE retail.chat_messages (
            message_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            user_id integer REFERENCES retail.app_users(user_id) ON DELETE SET NULL,
            user_message text NOT NULL CHECK (length(user_message) <= 1000),
            bot_reply text NOT NULL,
            intent varchar(50),
            was_helpful boolean,
            created_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX idx_chat_messages_user_created "
        "ON retail.chat_messages (user_id, created_at)"
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
                        'GRANT SELECT, INSERT, UPDATE ON retail.chat_messages TO %I',
                        role_name
                    );
                    EXECUTE format(
                        'GRANT USAGE, SELECT ON SEQUENCE '
                        'retail.chat_messages_message_id_seq TO %I',
                        role_name
                    );
                END IF;
            END LOOP;
        END
        $$;
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS retail.chat_messages")
