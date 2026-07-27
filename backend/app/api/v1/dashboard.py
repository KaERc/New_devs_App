from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
from decimal import Decimal, ROUND_HALF_UP
from app.services.cache import get_revenue_summary
from app.services.reservations import RevenueUnavailableError
from app.core.auth import authenticate_request as get_current_user

router = APIRouter()

@router.get("/dashboard/summary")
async def get_dashboard_summary(
    property_id: str,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:

    tenant_id = getattr(current_user, "tenant_id", "default_tenant") or "default_tenant"

    try:
        revenue_data = await get_revenue_summary(property_id, tenant_id)
    except RevenueUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e))

    # Round to whole cents using Decimal before ever touching a float.
    # total_amount is stored with sub-cent precision (NUMERIC(10,3)), so
    # converting straight to float() here let binary floating-point
    # representation error surface as off-by-a-few-cents totals downstream.
    rounded_revenue = Decimal(str(revenue_data['total'])).quantize(
        Decimal('0.01'), rounding=ROUND_HALF_UP
    )

    return {
        "property_id": revenue_data['property_id'],
        "total_revenue": float(rounded_revenue),
        "currency": revenue_data['currency'],
        "reservations_count": revenue_data['count']
    }
