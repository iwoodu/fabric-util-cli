"""Power BI REST API operations."""

import requests


ADMIN_CAPACITIES_URL = "https://api.powerbi.com/v1.0/myorg/admin/capacities"


class PowerBIAPIError(Exception):
    """Raised when the Power BI API returns an invalid or unsuccessful response."""


def list_tenant_capacities(access_token: str) -> list[dict[str, object]]:
    response = requests.get(
        ADMIN_CAPACITIES_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=30,
    )
    if not response.ok:
        raise PowerBIAPIError(
            f"Power BI API returned HTTP {response.status_code}: {response.text}"
        )

    try:
        payload = response.json()
    except ValueError as exc:
        raise PowerBIAPIError("Power BI API returned invalid JSON.") from exc

    capacities = payload.get("value") if isinstance(payload, dict) else None
    if not isinstance(capacities, list):
        raise PowerBIAPIError("Power BI API response did not contain a capacity list.")
    return capacities
