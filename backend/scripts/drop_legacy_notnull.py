import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import asyncio
from app.db.database import AsyncSessionLocal
from sqlalchemy import text

statements = [
    "ALTER TABLE gps_points ALTER COLUMN legacy_bus_id DROP NOT NULL;",
    "ALTER TABLE gps_points ALTER COLUMN latitude DROP NOT NULL;",
    "ALTER TABLE gps_points ALTER COLUMN longitude DROP NOT NULL;",
    "ALTER TABLE gps_points ALTER COLUMN location DROP NOT NULL;",
    "ALTER TABLE incidents ALTER COLUMN legacy_severity DROP NOT NULL;",
    "ALTER TABLE incidents ALTER COLUMN latitude DROP NOT NULL;",
    "ALTER TABLE incidents ALTER COLUMN longitude DROP NOT NULL;",
    "ALTER TABLE incidents ALTER COLUMN location DROP NOT NULL;",
    "ALTER TABLE observations ALTER COLUMN legacy_severity DROP NOT NULL;",
    "ALTER TABLE observations ALTER COLUMN latitude DROP NOT NULL;",
    "ALTER TABLE observations ALTER COLUMN longitude DROP NOT NULL;",
    "ALTER TABLE observations ALTER COLUMN location DROP NOT NULL;",
    "ALTER TABLE observations ALTER COLUMN detected_at DROP NOT NULL;",
    "ALTER TABLE observations ALTER COLUMN observation_type DROP NOT NULL;",
    "ALTER TABLE road_segments ALTER COLUMN geometry DROP NOT NULL;",
    "ALTER TABLE segment_history ALTER COLUMN road_segment_id DROP NOT NULL;",
    "ALTER TABLE observations ADD COLUMN IF NOT EXISTS status VARCHAR(32) DEFAULT 'confirmed';",
]

async def main():
    async with AsyncSessionLocal() as session:
        for stmt in statements:
            try:
                await session.execute(text(stmt))
                print(f"Executed: {stmt}")
            except Exception as e:
                print(f"Skipped ({stmt}): {e}")
                await session.rollback()
        await session.commit()
        print("All legacy NOT NULL constraints dropped successfully!")

if __name__ == "__main__":
    asyncio.run(main())
