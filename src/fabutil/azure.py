"""Azure Resource Manager operations used by fabutil."""

from urllib.parse import quote
from uuid import UUID

import requests


SUBSCRIPTIONS_URL = "https://management.azure.com/subscriptions"
FABRIC_CAPACITY_API_VERSION = "2023-11-01"
FABRIC_CAPACITY_RESOURCE_PROVIDER = "Microsoft.Fabric/capacities"


class AzureAPIError(Exception):
    """Raised when Azure Resource Manager returns an unsuccessful response."""


def _list_arm_collection(
    access_token: str, url: str, params: dict[str, str] | None = None
) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    seen_urls: set[str] = set()

    while True:
        response = requests.get(
            url,
            headers={"Authorization": f"Bearer {access_token}"},
            params=params,
            timeout=30,
        )
        if not response.ok:
            raise AzureAPIError(
                f"Azure API returned HTTP {response.status_code}: {response.text}"
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise AzureAPIError("Azure API returned invalid JSON.") from exc

        page_results = payload.get("value") if isinstance(payload, dict) else None
        if not isinstance(page_results, list) or not all(
            isinstance(result, dict) for result in page_results
        ):
            raise AzureAPIError("Azure API response did not contain a value list.")
        results.extend(page_results)

        next_url = payload.get("nextLink")
        if next_url is None:
            return results
        if not isinstance(next_url, str) or not next_url:
            raise AzureAPIError("Azure API response contained an invalid nextLink.")
        if next_url in seen_urls:
            raise AzureAPIError("Azure API returned a repeated nextLink.")
        seen_urls.add(next_url)
        url = next_url
        params = None


def list_subscriptions(access_token: str) -> list[dict[str, object]]:
    return _list_arm_collection(
        access_token,
        SUBSCRIPTIONS_URL,
        {"api-version": "2022-12-01"},
    )


def list_subscription_capacities(
    access_token: str, subscription_id: str
) -> list[dict[str, object]]:
    url = (
        f"https://management.azure.com/subscriptions/{quote(subscription_id, safe='')}"
        f"/providers/{FABRIC_CAPACITY_RESOURCE_PROVIDER}"
    )
    return _list_arm_collection(
        access_token,
        url,
        {"api-version": FABRIC_CAPACITY_API_VERSION},
    )


def find_capacity_resource(
    access_token: str,
    capacity: str,
    capacity_list: list[dict[str, object]] | None = None,
) -> dict[str, str]:
    capacity_name = capacity
    try:
        capacity_id = str(UUID(capacity))
    except ValueError:
        capacity_id = None

    if capacity_id is not None:
        if capacity_list is None:
            raise AzureAPIError(
                "Capacity listing is required to resolve a capacity ID."
            )
        fabric_matches = [
            item
            for item in capacity_list
            if isinstance(item.get("id"), str)
            and item["id"].casefold() == capacity_id.casefold()
        ]
        if not fabric_matches:
            raise AzureAPIError(
                f"No capacity with ID '{capacity}' was found."
            )
        if len(fabric_matches) > 1:
            raise AzureAPIError(
                f"More than one capacity with ID '{capacity}' was found."
            )
        capacity_name = fabric_matches[0].get("displayName")
        if not isinstance(capacity_name, str) or not capacity_name:
            raise AzureAPIError(
                f"Capacity with ID '{capacity}' has no display name."
            )

    resources: list[dict[str, object]] = []
    for subscription in list_subscriptions(access_token):
        subscription_id = subscription.get("subscriptionId")
        if not isinstance(subscription_id, str) or not subscription_id:
            raise AzureAPIError(
                "Azure subscription response did not contain a subscription ID."
            )
        resources.extend(
            list_subscription_capacities(access_token, subscription_id)
        )

    matches = [
        resource
        for resource in resources
        if isinstance(resource.get("name"), str)
        and resource["name"].casefold() == capacity_name.casefold()
    ]
    if not matches:
        raise AzureAPIError(
            f"No Azure Fabric capacity named '{capacity_name}' was found in "
            "any accessible subscription."
        )
    if len(matches) > 1:
        raise AzureAPIError(
            f"More than one Azure Fabric capacity named '{capacity_name}' was "
            "found across subscriptions or resource groups."
        )

    resource_id = matches[0].get("id")
    if not isinstance(resource_id, str):
        raise AzureAPIError(
            f"Azure Fabric capacity '{capacity_name}' did not contain a resource ID."
        )
    resource_parts = resource_id.strip("/").split("/")
    try:
        subscription_index = next(
            index
            for index, part in enumerate(resource_parts)
            if part.casefold() == "subscriptions"
        )
        resource_group_index = next(
            index
            for index, part in enumerate(resource_parts)
            if part.casefold() == "resourcegroups"
        )
        subscription_id = resource_parts[subscription_index + 1]
        resource_group = resource_parts[resource_group_index + 1]
    except (StopIteration, IndexError) as exc:
        raise AzureAPIError(
            f"Azure Fabric capacity '{capacity_name}' had an invalid resource ID."
        ) from exc

    resource_name = matches[0].get("name")
    if not isinstance(resource_name, str) or not resource_name:
        raise AzureAPIError(
            f"Azure Fabric capacity '{capacity_name}' had no resource name."
        )
    return {
        "subscription_id": subscription_id,
        "resource_group": resource_group,
        "capacity_name": resource_name,
    }


def _set_capacity_state(
    access_token: str,
    subscription_id: str,
    resource_group: str,
    capacity_name: str,
    action: str,
) -> None:
    url = (
        f"https://management.azure.com/subscriptions/{quote(subscription_id, safe='')}"
        f"/resourceGroups/{quote(resource_group, safe='')}/providers/"
        f"{FABRIC_CAPACITY_RESOURCE_PROVIDER}/{quote(capacity_name, safe='')}"
        f"/{action}"
    )
    response = requests.post(
        url,
        headers={"Authorization": f"Bearer {access_token}"},
        params={"api-version": FABRIC_CAPACITY_API_VERSION},
        timeout=30,
    )
    if not response.ok:
        raise AzureAPIError(
            f"Azure API returned HTTP {response.status_code}: {response.text}"
        )


def pause_capacity(
    access_token: str, subscription_id: str, resource_group: str, capacity_name: str
) -> None:
    _set_capacity_state(
        access_token, subscription_id, resource_group, capacity_name, "suspend"
    )


def resume_capacity(
    access_token: str, subscription_id: str, resource_group: str, capacity_name: str
) -> None:
    _set_capacity_state(
        access_token, subscription_id, resource_group, capacity_name, "resume"
    )
