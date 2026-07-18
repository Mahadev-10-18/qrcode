from sqlalchemy import text
from backend.db import engine
import sys
import os
import asyncio

# Setup mock Twilio env vars so settings imports successfully
os.environ.setdefault("TWILIO_ACCOUNT_SID", "AC" + "0" * 32)
os.environ.setdefault("TWILIO_AUTH_TOKEN", "0" * 32)
os.environ.setdefault("TWILIO_PROXY_SERVICE_SID", "KS" + "0" * 32)

sys.path.append(r"d:\qrcode")


async def main():
    async with engine.begin() as conn:
        try:
            # Check if column already exists by querying table info
            # In PostgreSQL, we can use ALTER TABLE ... ADD COLUMN IF NOT EXISTS:
            await conn.execute(text("ALTER TABLE contactevent ADD COLUMN IF NOT EXISTS is_failed BOOLEAN DEFAULT FALSE"))
            print("Successfully migrated contactevent table!")
        except Exception as e:
            print(f"Migration error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
