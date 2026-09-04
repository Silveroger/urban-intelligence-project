"""
Supabase & PostGIS Connectivity Diagnostic Script
Run with:
  cd backend
  python scripts/test_connection.py
"""
import sys
import os
import asyncio

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import text
from app.core.config import settings
from app.core.security import mask_secret
from app.db.database import AsyncSessionLocal, get_supabase_client


async def run_diagnostics():
    print("=" * 70)
    print("SIH 26124: SUPABASE & POSTGIS CONNECTIVITY DIAGNOSTICS")
    print("=" * 70)

    # 1. Environment & Configuration
    print("\n[1/5] Checking Configuration & Credentials:")
    print(f"  * Environment:               {settings.ENVIRONMENT}")
    print(f"  * PostGIS Schema:            {settings.POSTGIS_SCHEMA}")
    print(f"  * Supabase URL:              {settings.SUPABASE_URL}")
    print(f"  * Supabase Anon Key:         {mask_secret(settings.SUPABASE_ANON_KEY)}")
    print(f"  * Supabase Service Role Key: {mask_secret(settings.SUPABASE_SERVICE_ROLE_KEY)}")
    print(f"  * Storage Bucket:            {settings.SUPABASE_STORAGE_BUCKET}")

    if "your-project-ref" in settings.SUPABASE_URL:
        print("\n  [!] WARNING: Default placeholder credentials detected in .env.")
        print("      Please copy .env.example to .env and insert your real Supabase credentials.")

    # 2. Database Connection
    print("\n[2/5] Testing PostgreSQL Connection:")
    db_connected = False
    try:
        async with AsyncSessionLocal() as session:
            res = await session.execute(text("SELECT version();"))
            db_ver = res.scalar()
            print(f"  [+] SUCCESS: Connected to PostgreSQL!")
            print(f"      Version: {db_ver}")
            db_connected = True
    except Exception as e:
        print(f"  [-] FAILED: Could not connect to PostgreSQL database.")
        print(f"      Error: {e}")

    # 3. PostGIS Extension in `gis` Schema
    print(f"\n[3/5] Testing PostGIS Extension in '{settings.POSTGIS_SCHEMA}' Schema:")
    if db_connected:
        try:
            async with AsyncSessionLocal() as session:
                query = text(f"SELECT {settings.POSTGIS_SCHEMA}.PostGIS_Full_Version();")
                res = await session.execute(query)
                gis_ver = res.scalar()
                print(f"  [+] SUCCESS: PostGIS functions verified in '{settings.POSTGIS_SCHEMA}' schema!")
                print(f"      {gis_ver[:80]}...")
        except Exception as e:
            print(f"  [-] WARNING: Function call in '{settings.POSTGIS_SCHEMA}' failed: {e}")
            try:
                async with AsyncSessionLocal() as session:
                    res = await session.execute(text("SELECT PostGIS_Full_Version();"))
                    print(f"  [+] PostGIS is installed, but in default/extensions schema instead of '{settings.POSTGIS_SCHEMA}'.")
            except Exception as e2:
                print(f"  [-] FAILED: PostGIS is not available: {e2}")
    else:
        print("  [SKIP] Skipped due to DB connection failure.")

    # 4. Table Verification
    print("\n[4/5] Checking Schema Tables:")
    expected_tables = ["buses", "gps_points", "road_segments", "observations", "incidents", "segment_history"]
    if db_connected:
        try:
            async with AsyncSessionLocal() as session:
                res = await session.execute(
                    text(
                        "SELECT table_name FROM information_schema.tables "
                        "WHERE table_schema = 'public' ORDER BY table_name;"
                    )
                )
                found_tables = [r[0] for r in res.fetchall()]
                for tbl in expected_tables:
                    if tbl in found_tables:
                        print(f"  [+] Found table: {tbl}")
                    else:
                        print(f"  [-] MISSING table: {tbl}")

                # Check test seed data
                if "buses" in found_tables:
                    bus_res = await session.execute(text("SELECT vehicle_number FROM buses LIMIT 5;"))
                    buses = [b[0] for b in bus_res.fetchall()]
                    print(f"      Fleet buses in DB: {buses}")

                if "road_segments" in found_tables:
                    seg_res = await session.execute(text("SELECT road_name FROM road_segments LIMIT 5;"))
                    segs = [s[0] for s in seg_res.fetchall()]
                    print(f"      Road segments in DB: {segs}")
        except Exception as e:
            print(f"  [-] Error querying tables: {e}")
    else:
        print("  [SKIP] Skipped due to DB connection failure.")

    # 5. Supabase Storage Bucket
    print(f"\n[5/5] Checking Supabase Storage Bucket '{settings.SUPABASE_STORAGE_BUCKET}':")
    client = get_supabase_client()
    if client:
        try:
            buckets = client.storage.list_buckets()
            bucket_names = [b.name for b in buckets]
            if settings.SUPABASE_STORAGE_BUCKET in bucket_names:
                print(f"  [+] SUCCESS: Bucket '{settings.SUPABASE_STORAGE_BUCKET}' found in Supabase Storage!")
            else:
                print(f"  [-] Bucket '{settings.SUPABASE_STORAGE_BUCKET}' not found in: {bucket_names}")
        except Exception as e:
            print(f"  [-] Error checking Supabase Storage: {e}")
    else:
        print("  [-] Supabase client not initialized (check SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY).")

    print("\n" + "=" * 70)
    print("Diagnostics complete.")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_diagnostics())
