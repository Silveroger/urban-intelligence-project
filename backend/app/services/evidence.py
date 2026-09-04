import logging
from typing import Optional, Tuple
from app.core.config import settings
from app.db.database import get_supabase_client

logger = logging.getLogger("urban_intel.evidence")


async def upload_evidence(
    file_bytes: bytes,
    file_name: str,
    content_type: str = "image/jpeg",
) -> Tuple[str, Optional[str]]:
    """
    Uploads evidence media to the Supabase Storage bucket.
    
    Returns:
        (storage_path, signed_url)
    """
    client = get_supabase_client()
    bucket = settings.SUPABASE_STORAGE_BUCKET

    if not client:
        logger.warning("Supabase client unconfigured. Returning mock evidence path.")
        mock_path = f"simulated/{file_name}"
        return mock_path, f"{settings.SUPABASE_URL}/storage/v1/object/public/{bucket}/{mock_path}"

    try:
        storage_path = f"uploads/{file_name}"
        # Upload using Supabase storage client
        client.storage.from_(bucket).upload(
            path=storage_path,
            file=file_bytes,
            file_options={"content-type": content_type, "upsert": "true"},
        )

        # Generate signed URL valid for 3600 seconds (1 hour)
        signed_res = client.storage.from_(bucket).create_signed_url(storage_path, 3600)
        signed_url = signed_res.get("signedURL") or signed_res.get("signedUrl")

        return storage_path, signed_url
    except Exception as e:
        logger.error(f"Error uploading evidence to Supabase bucket '{bucket}': {e}")
        return f"errors/{file_name}", None


def get_signed_evidence_url(storage_path: Optional[str], expires_in: int = 3600) -> Optional[str]:
    """Generates a temporary signed URL for a stored evidence path."""
    if not storage_path:
        return None

    # If it's already an HTTP URL, return as is
    if storage_path.startswith("http://") or storage_path.startswith("https://"):
        return storage_path

    client = get_supabase_client()
    bucket = settings.SUPABASE_STORAGE_BUCKET

    if not client:
        return f"{settings.SUPABASE_URL}/storage/v1/object/public/{bucket}/{storage_path}"

    try:
        res = client.storage.from_(bucket).create_signed_url(storage_path, expires_in)
        return res.get("signedURL") or res.get("signedUrl")
    except Exception as e:
        logger.warning(f"Failed to generate signed URL for '{storage_path}': {e}")
        return None
