import unittest
from unittest.mock import Mock, patch

from fabutil.azure import (
    AzureAPIError,
    FABRIC_CAPACITY_API_VERSION,
    find_capacity_resource,
    list_subscription_capacities,
    list_subscriptions,
    pause_capacity,
    resume_capacity,
)


SUBSCRIPTION_ID = "a0b1c2d3-e4f5-4678-9012-3456789abcde"
CAPACITY_ID = "b0b1c2d3-e4f5-4678-9012-3456789abcde"


class ListSubscriptionsTests(unittest.TestCase):
    @patch("fabutil.azure.requests.get")
    def test_lists_subscriptions(self, get: Mock) -> None:
        subscription = {
            "subscriptionId": SUBSCRIPTION_ID,
            "displayName": "Production",
        }
        get.return_value = Mock(
            ok=True,
            json=lambda: {"value": [subscription]},
        )

        self.assertEqual(list_subscriptions("azure-token"), [subscription])
        get.assert_called_once_with(
            "https://management.azure.com/subscriptions",
            headers={"Authorization": "Bearer azure-token"},
            params={"api-version": "2022-12-01"},
            timeout=30,
        )

class ListResourceGroupCapacitiesTests(unittest.TestCase):
    @patch("fabutil.azure.requests.get")
    def test_lists_capacities_in_subscription(self, get: Mock) -> None:
        capacity = {
            "id": "/subscriptions/sub/resourceGroups/rg/providers/"
            "Microsoft.Fabric/capacities/finance",
            "name": "finance",
        }
        get.return_value = Mock(
            ok=True,
            json=lambda: {"value": [capacity]},
        )

        self.assertEqual(
            list_subscription_capacities("azure-token", "sub"),
            [capacity],
        )
        get.assert_called_once_with(
            "https://management.azure.com/subscriptions/sub/providers/"
            "Microsoft.Fabric/capacities",
            headers={"Authorization": "Bearer azure-token"},
            params={"api-version": FABRIC_CAPACITY_API_VERSION},
            timeout=30,
        )

    @patch("fabutil.azure.list_subscription_capacities")
    @patch("fabutil.azure.list_subscriptions")
    def test_finds_capacity_by_name_and_returns_resource_coordinates(
        self, list_all_subscriptions: Mock, list_capacities: Mock
    ) -> None:
        list_all_subscriptions.return_value = [
            {"subscriptionId": SUBSCRIPTION_ID}
        ]
        list_capacities.return_value = [
            {
                "id": f"/subscriptions/{SUBSCRIPTION_ID}/resourceGroups/rg/"
                "providers/Microsoft.Fabric/capacities/finance",
                "name": "Finance",
            }
        ]

        self.assertEqual(
            find_capacity_resource("azure-token", "finance"),
            {
                "subscription_id": SUBSCRIPTION_ID,
                "resource_group": "rg",
                "capacity_name": "Finance",
            },
        )
        list_all_subscriptions.assert_called_once_with("azure-token")
        list_capacities.assert_called_once_with("azure-token", SUBSCRIPTION_ID)

    @patch("fabutil.azure.list_subscription_capacities")
    @patch("fabutil.azure.list_subscriptions")
    def test_finds_capacity_by_guid(
        self, list_all_subscriptions: Mock, list_capacities: Mock
    ) -> None:
        list_all_subscriptions.return_value = [
            {"subscriptionId": SUBSCRIPTION_ID}
        ]
        list_capacities.return_value = [
            {
                "id": f"/subscriptions/{SUBSCRIPTION_ID}/resourceGroups/rg/"
                "providers/Microsoft.Fabric/capacities/finance",
                "name": "finance",
            }
        ]

        result = find_capacity_resource(
            "azure-token",
            CAPACITY_ID,
            [{"id": CAPACITY_ID, "displayName": "Finance"}],
        )

        self.assertEqual(result["capacity_name"], "finance")

    @patch(
        "fabutil.azure.list_subscription_capacities",
        side_effect=[
            [
                {
                    "id": "/subscriptions/sub1/resourceGroups/rg1/providers/"
                    "Microsoft.Fabric/capacities/finance",
                    "name": "Finance",
                }
            ],
            [
                {
                    "id": "/subscriptions/sub2/resourceGroups/rg2/providers/"
                    "Microsoft.Fabric/capacities/finance",
                    "name": "Finance",
                }
            ],
        ],
    )
    @patch(
        "fabutil.azure.list_subscriptions",
        return_value=[
            {"subscriptionId": "sub1"},
            {"subscriptionId": "sub2"},
        ],
    )
    def test_rejects_capacity_name_ambiguous_across_subscriptions(
        self, _list_subscriptions: Mock, _list_capacities: Mock
    ) -> None:
        with self.assertRaisesRegex(
            AzureAPIError, "across subscriptions or resource groups"
        ):
            find_capacity_resource("azure-token", "Finance")

    @patch(
        "fabutil.azure.list_subscription_capacities",
        return_value=[
            {
                "id": "/subscriptions/sub/resourceGroups/rg1/providers/"
                "Microsoft.Fabric/capacities/finance",
                "name": "Finance",
            },
            {
                "id": "/subscriptions/sub/resourceGroups/rg2/providers/"
                "Microsoft.Fabric/capacities/finance2",
                "name": "Finance",
            },
        ],
    )
    @patch(
        "fabutil.azure.list_subscriptions",
        return_value=[{"subscriptionId": "sub"}],
    )
    def test_rejects_capacity_name_ambiguous_across_resource_groups(
        self, _list_subscriptions: Mock, _list_capacities: Mock
    ) -> None:
        with self.assertRaisesRegex(
            AzureAPIError, "across subscriptions or resource groups"
        ):
            find_capacity_resource("azure-token", "Finance")

    @patch("fabutil.azure.list_subscription_capacities", return_value=[])
    @patch(
        "fabutil.azure.list_subscriptions",
        return_value=[{"subscriptionId": "sub"}],
    )
    def test_reports_unknown_capacity(
        self, _list_subscriptions: Mock, _list_capacities: Mock
    ) -> None:
        with self.assertRaisesRegex(AzureAPIError, "No Azure Fabric capacity"):
            find_capacity_resource("azure-token", "missing")


class CapacityStateTests(unittest.TestCase):
    @patch("fabutil.azure.requests.post")
    def test_pauses_capacity(self, post: Mock) -> None:
        post.return_value = Mock(ok=True)

        pause_capacity("azure-token", SUBSCRIPTION_ID, "rg", "finance")

        post.assert_called_once_with(
            "https://management.azure.com/subscriptions/"
            f"{SUBSCRIPTION_ID}/resourceGroups/rg/providers/"
            "Microsoft.Fabric/capacities/finance/suspend",
            headers={"Authorization": "Bearer azure-token"},
            params={"api-version": FABRIC_CAPACITY_API_VERSION},
            timeout=30,
        )

    @patch("fabutil.azure.requests.post")
    def test_resumes_capacity(self, post: Mock) -> None:
        post.return_value = Mock(ok=True)

        resume_capacity("azure-token", SUBSCRIPTION_ID, "rg", "finance")

        self.assertTrue(post.call_args.args[0].endswith("/resume"))

    @patch("fabutil.azure.requests.post")
    def test_reports_http_error(self, post: Mock) -> None:
        post.return_value = Mock(ok=False, status_code=403, text="Forbidden")

        with self.assertRaisesRegex(AzureAPIError, "HTTP 403"):
            pause_capacity("azure-token", SUBSCRIPTION_ID, "rg", "finance")
