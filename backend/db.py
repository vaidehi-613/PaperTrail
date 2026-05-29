from supabase import AsyncClient, acreate_client

from backend.config import get_settings


async def get_supabase() -> AsyncClient:
    s = get_settings()
    return await acreate_client(s.supabase_url, s.supabase_service_key)
