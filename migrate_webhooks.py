"""
One-time migration: adds missing columns to webhooks and webhook_deliveries tables.
Safe to run multiple times (skips columns that already exist).
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text


async def migrate():
    engine = create_async_engine("sqlite+aiosqlite:///finanza.db", echo=False)

    async with engine.connect() as conn:
        # ---- webhooks ----
        result = await conn.execute(text("PRAGMA table_info(webhooks)"))
        existing = {row[1] for row in result.fetchall()}
        print("[INFO] webhooks existing columns:", existing)

        webhook_cols = [
            ("user_id",         "INTEGER NOT NULL DEFAULT 0"),
            ("name",            "VARCHAR(255) NOT NULL DEFAULT ''"),
            ("url",             "VARCHAR(2048) NOT NULL DEFAULT ''"),
            ("events",          "TEXT NOT NULL DEFAULT '[]'"),
            ("active",          "BOOLEAN NOT NULL DEFAULT 1"),
            ("secret_key",      "VARCHAR(255)"),
            ("retry_count",     "INTEGER DEFAULT 3"),
            ("timeout_seconds", "INTEGER DEFAULT 30"),
            ("created_at",      "DATETIME DEFAULT CURRENT_TIMESTAMP"),
            ("updated_at",      "DATETIME"),
        ]
        for col, col_def in webhook_cols:
            if col not in existing:
                try:
                    await conn.execute(text(f"ALTER TABLE webhooks ADD COLUMN {col} {col_def}"))
                    print(f"  [OK] Added webhooks.{col}")
                except Exception as e:
                    print(f"  [SKIP] webhooks.{col}: {e}")

        # ---- webhook_deliveries ----
        result2 = await conn.execute(text("PRAGMA table_info(webhook_deliveries)"))
        existing2 = {row[1] for row in result2.fetchall()}
        print("[INFO] webhook_deliveries existing columns:", existing2)

        delivery_cols = [
            ("webhook_id",    "INTEGER NOT NULL DEFAULT 0"),
            ("event_type",    "VARCHAR(255) NOT NULL DEFAULT ''"),
            ("payload",       "TEXT"),
            ("status",        "VARCHAR(50) DEFAULT 'pending'"),
            ("http_status",   "INTEGER"),
            ("error_message", "TEXT"),
            ("attempt_count", "INTEGER DEFAULT 0"),
            ("last_attempt",  "DATETIME"),
            ("next_retry",    "DATETIME"),
            ("created_at",    "DATETIME DEFAULT CURRENT_TIMESTAMP"),
            ("updated_at",    "DATETIME"),
        ]
        for col, col_def in delivery_cols:
            if col not in existing2:
                try:
                    await conn.execute(text(f"ALTER TABLE webhook_deliveries ADD COLUMN {col} {col_def}"))
                    print(f"  [OK] Added webhook_deliveries.{col}")
                except Exception as e:
                    print(f"  [SKIP] webhook_deliveries.{col}: {e}")

        await conn.commit()
        print("[DONE] Migration complete.")


asyncio.run(migrate())
