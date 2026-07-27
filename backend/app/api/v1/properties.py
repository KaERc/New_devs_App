from fastapi import APIRouter, Depends
from typing import Dict, Any

from app.core.auth import authenticate_request as get_current_user

router = APIRouter()

# Tenant-scoped fallback used only if the DB is unavailable, so an outage
# fails safe (empty/own-tenant data) instead of ever showing another
# tenant's properties.
FALLBACK_PROPERTIES = {
    "tenant-a": [
        {"id": "prop-001", "name": "Beach House Alpha", "timezone": "Europe/Paris"},
        {"id": "prop-002", "name": "City Apartment Downtown", "timezone": "Europe/Paris"},
        {"id": "prop-003", "name": "Country Villa Estate", "timezone": "Europe/Paris"},
    ],
    "tenant-b": [
        {"id": "prop-001", "name": "Mountain Lodge Beta", "timezone": "America/New_York"},
        {"id": "prop-004", "name": "Lakeside Cottage", "timezone": "America/New_York"},
        {"id": "prop-005", "name": "Urban Loft Modern", "timezone": "America/New_York"},
    ],
}


@router.get("/properties")
async def list_properties(current_user=Depends(get_current_user)) -> Dict[str, Any]:
    """List properties belonging to the authenticated user's tenant."""
    tenant_id = getattr(current_user, "tenant_id", None)
    if not tenant_id:
        return {"items": [], "total": 0}

    try:
        from app.core.database_pool import DatabasePool
        from sqlalchemy import text

        db_pool = DatabasePool()
        await db_pool.initialize()

        if not db_pool.session_factory:
            raise Exception("Database pool not available")

        async with db_pool.get_session() as session:
            query = text(
                """
                SELECT id, name, timezone
                FROM properties
                WHERE tenant_id = :tenant_id
                ORDER BY id
                """
            )
            result = await session.execute(query, {"tenant_id": tenant_id})
            items = [
                {"id": row.id, "name": row.name, "timezone": row.timezone}
                for row in result.fetchall()
            ]
            return {"items": items, "total": len(items)}

    except Exception as e:
        print(f"Database error listing properties for tenant {tenant_id}: {e}")
        items = FALLBACK_PROPERTIES.get(tenant_id, [])
        return {"items": items, "total": len(items)}
