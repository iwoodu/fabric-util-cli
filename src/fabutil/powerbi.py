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


def resolve_capacity_id(access_token: str, capacity_name: str) -> str:
    capacities = list_tenant_capacities(access_token)
    matching_ids = [
        capacity.get("id")
        for capacity in capacities
        if isinstance(capacity, dict)
        and isinstance(capacity.get("displayName"), str)
        and capacity["displayName"].casefold() == capacity_name.casefold()
        and isinstance(capacity.get("id"), str)
    ]
    if not matching_ids:
        raise PowerBIAPIError(f"No capacity named '{capacity_name}' was found.")
    if len(matching_ids) > 1:
        raise PowerBIAPIError(
            f"More than one capacity is named '{capacity_name}'; use its capacity ID."
        )
    return matching_ids[0]
