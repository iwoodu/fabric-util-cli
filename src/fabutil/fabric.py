"""Microsoft Fabric REST API operations."""

import requests


ADMIN_WORKSPACES_URL = "https://api.fabric.microsoft.com/v1/admin/workspaces"


class FabricAPIError(Exception):
    """Raised when the Fabric API returns an invalid or unsuccessful response."""


def list_capacity_workspaces(
    access_token: str, capacity_id: str
) -> list[dict[str, object]]:
    workspaces: list[dict[str, object]] = []
    continuation_token: str | None = None
    seen_tokens: set[str] = set()

    while True:
        params: dict[str, str] = {"capacityId": capacity_id}
        if continuation_token:
            params["continuationToken"] = continuation_token

        response = requests.get(
            ADMIN_WORKSPACES_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            params=params,
            timeout=30,
        )
        if not response.ok:
            raise FabricAPIError(
                f"Fabric API returned HTTP {response.status_code}: {response.text}"
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise FabricAPIError("Fabric API returned invalid JSON.") from exc

        page_workspaces = (
            payload.get("workspaces") if isinstance(payload, dict) else None
        )
        if not isinstance(page_workspaces, list) or not all(
            isinstance(workspace, dict) for workspace in page_workspaces
        ):
            raise FabricAPIError(
                "Fabric API response did not contain a workspace list."
            )
        workspaces.extend(page_workspaces)

        next_token = payload.get("continuationToken")
        if next_token is None:
            return workspaces
        if not isinstance(next_token, str) or not next_token:
            raise FabricAPIError(
                "Fabric API response contained an invalid continuation token."
            )
        if next_token in seen_tokens:
            raise FabricAPIError(
                "Fabric API returned a repeated continuation token."
            )
        seen_tokens.add(next_token)
        continuation_token = next_token
