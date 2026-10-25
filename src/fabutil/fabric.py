"""Microsoft Fabric REST API operations."""

import requests


ADMIN_ITEMS_URL = "https://api.fabric.microsoft.com/v1/admin/items"
ADMIN_CAPACITY_TENANT_SETTING_OVERRIDES_URL = (
    "https://api.fabric.microsoft.com/v1/admin/capacities/"
    "delegatedTenantSettingOverrides"
)
ADMIN_DOMAIN_TENANT_SETTING_OVERRIDES_URL = (
    "https://api.fabric.microsoft.com/v1/admin/domains/"
    "delegatedTenantSettingOverrides"
)
ADMIN_WORKSPACE_TENANT_SETTING_OVERRIDES_URL = (
    "https://api.fabric.microsoft.com/v1/admin/workspaces/"
    "delegatedTenantSettingOverrides"
)
ADMIN_TENANT_SETTINGS_URL = "https://api.fabric.microsoft.com/v1/admin/tenantsettings"
ADMIN_WORKSPACES_URL = "https://api.fabric.microsoft.com/v1/admin/workspaces"


class FabricAPIError(Exception):
    """Raised when the Fabric API returns an invalid or unsuccessful response."""


def _list_admin_collection(
    access_token: str,
    url: str,
    collection_name: str,
    base_params: dict[str, str],
) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    continuation_token: str | None = None
    seen_tokens: set[str] = set()

    while True:
        params = dict(base_params)
        if continuation_token:
            params["continuationToken"] = continuation_token
        response = requests.get(
            url,
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

        page_results = (
            payload.get(collection_name) if isinstance(payload, dict) else None
        )
        if not isinstance(page_results, list) or not all(
            isinstance(result, dict) for result in page_results
        ):
            raise FabricAPIError(
                f"Fabric API response did not contain a {collection_name} list."
            )
        results.extend(page_results)

        next_token = payload.get("continuationToken")
        if next_token is None:
            return results
        if not isinstance(next_token, str) or not next_token:
            raise FabricAPIError(
                "Fabric API response contained an invalid continuation token."
            )
        if next_token in seen_tokens:
            raise FabricAPIError("Fabric API returned a repeated continuation token.")
        seen_tokens.add(next_token)
        continuation_token = next_token


def list_admin_workspaces(
    access_token: str,
    capacity_id: str | None = None,
    name: str | None = None,
) -> list[dict[str, object]]:
    params: dict[str, str] = {}
    if capacity_id:
        params["capacityId"] = capacity_id
    if name:
        params["name"] = name
    return _list_admin_collection(
        access_token, ADMIN_WORKSPACES_URL, "workspaces", params
    )


def list_capacity_workspaces(
    access_token: str, capacity_id: str
) -> list[dict[str, object]]:
    return list_admin_workspaces(access_token, capacity_id=capacity_id)


def resolve_admin_workspace_id(
    access_token: str, workspace_name: str, capacity_id: str | None = None
) -> str:
    workspaces = list_admin_workspaces(
        access_token, capacity_id=capacity_id, name=workspace_name
    )
    matching_ids = [
        workspace.get("id")
        for workspace in workspaces
        if any(
            isinstance(workspace.get(name_field), str)
            and workspace[name_field].casefold() == workspace_name.casefold()
            for name_field in ("name", "displayName")
        )
        and isinstance(workspace.get("id"), str)
    ]
    if not matching_ids:
        raise FabricAPIError(f"No workspace named '{workspace_name}' was found.")
    if len(matching_ids) > 1:
        raise FabricAPIError(
            f"More than one workspace is named '{workspace_name}'; "
            "use its workspace ID."
        )
    return matching_ids[0]


def list_admin_items(
    access_token: str,
    workspace_id: str | None = None,
    capacity_id: str | None = None,
    state: str | None = None,
    item_type: str | None = None,
) -> list[dict[str, object]]:
    params: dict[str, str] = {}
    if workspace_id:
        params["workspaceId"] = workspace_id
    if capacity_id:
        params["capacityId"] = capacity_id
    if state:
        params["state"] = state
    if item_type:
        params["type"] = item_type
    return _list_admin_collection(
        access_token, ADMIN_ITEMS_URL, "itemEntities", params
    )


def get_tenant_settings(access_token: str) -> list[dict[str, object]]:
    return _list_admin_collection(
        access_token,
        ADMIN_TENANT_SETTINGS_URL,
        "value",
        {},
    )


def list_capacity_tenant_setting_overrides(
    access_token: str,
) -> list[dict[str, object]]:
    return _list_admin_collection(
        access_token,
        ADMIN_CAPACITY_TENANT_SETTING_OVERRIDES_URL,
        "value",
        {},
    )


def list_domain_tenant_setting_overrides(
    access_token: str,
) -> list[dict[str, object]]:
    return _list_admin_collection(
        access_token,
        ADMIN_DOMAIN_TENANT_SETTING_OVERRIDES_URL,
        "value",
        {},
    )


def list_workspace_tenant_setting_overrides(
    access_token: str,
) -> list[dict[str, object]]:
    return _list_admin_collection(
        access_token,
        ADMIN_WORKSPACE_TENANT_SETTING_OVERRIDES_URL,
        "value",
        {},
    )
