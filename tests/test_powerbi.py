import unittest
from unittest.mock import Mock, patch

from fabutil.powerbi import (
    ADMIN_CAPACITIES_URL,
    ADMIN_REFRESHABLES_URL,
    PowerBIAPIError,
    filter_refreshables,
    list_tenant_capacities,
    list_tenant_refreshables,
    resolve_capacity_id,
)


class ListTenantCapacitiesTests(unittest.TestCase):
    @patch("fabutil.powerbi.requests.get")
    def test_gets_tenant_capacities_with_bearer_token(self, get: Mock) -> None:
        get.return_value = Mock(
            ok=True,
            json=lambda: {"value": [{"displayName": "Capacity One"}]},
        )

        result = list_tenant_capacities("test-token")

        self.assertEqual(result, [{"displayName": "Capacity One"}])
        get.assert_called_once_with(
            ADMIN_CAPACITIES_URL,
            headers={"Authorization": "Bearer test-token"},
            timeout=30,
        )

    @patch("fabutil.powerbi.requests.get")
    def test_reports_api_errors(self, get: Mock) -> None:
        get.return_value = Mock(ok=False, status_code=403, text="Forbidden")

        with self.assertRaisesRegex(PowerBIAPIError, "HTTP 403"):
            list_tenant_capacities("test-token")

    @patch("fabutil.powerbi.requests.get")
    def test_rejects_unexpected_response_shape(self, get: Mock) -> None:
        get.return_value = Mock(ok=True, json=lambda: {"items": []})

        with self.assertRaisesRegex(PowerBIAPIError, "did not contain a capacity list"):
            list_tenant_capacities("test-token")

    @patch("fabutil.powerbi.list_tenant_capacities")
    def test_resolves_capacity_name_case_insensitively(
        self, list_capacities: Mock
    ) -> None:
        list_capacities.return_value = [
            {"id": "capacity-id", "displayName": "Finance"},
        ]

        result = resolve_capacity_id("token", "finance")

        self.assertEqual(result, "capacity-id")

    @patch("fabutil.powerbi.list_tenant_capacities", return_value=[])
    def test_reports_unknown_capacity_name(self, _list_capacities: Mock) -> None:
        with self.assertRaisesRegex(PowerBIAPIError, "No capacity named"):
            resolve_capacity_id("token", "missing")

    @patch("fabutil.powerbi.list_tenant_capacities")
    def test_reports_ambiguous_capacity_name(self, list_capacities: Mock) -> None:
        list_capacities.return_value = [
            {"id": "one", "displayName": "Finance"},
            {"id": "two", "displayName": "finance"},
        ]

        with self.assertRaisesRegex(PowerBIAPIError, "use its capacity ID"):
            resolve_capacity_id("token", "Finance")


class ListTenantRefreshablesTests(unittest.TestCase):
    @patch("fabutil.powerbi.requests.get")
    def test_lists_refreshables_with_expanded_context(self, get: Mock) -> None:
        refreshables = [{"id": "model-id", "name": "Sales"}]
        get.return_value = Mock(ok=True, json=lambda: {"value": refreshables})

        result = list_tenant_refreshables("test-token")

        self.assertEqual(result, refreshables)
        get.assert_called_once_with(
            ADMIN_REFRESHABLES_URL,
            headers={"Authorization": "Bearer test-token"},
            params={"$top": 1000, "$skip": 0, "$expand": "capacity,group"},
            timeout=30,
        )

    @patch("fabutil.powerbi.requests.get")
    def test_paginates_past_first_thousand_refreshables(self, get: Mock) -> None:
        first_page = [{"id": f"model-{index}"} for index in range(1000)]
        second_page = [{"id": "model-1000"}]
        get.side_effect = [
            Mock(ok=True, json=lambda: {"value": first_page}),
            Mock(ok=True, json=lambda: {"value": second_page}),
        ]

        result = list_tenant_refreshables("test-token")

        self.assertEqual(len(result), 1001)
        self.assertEqual(
            get.call_args_list[1].kwargs["params"],
            {"$top": 1000, "$skip": 1000, "$expand": "capacity,group"},
        )

    @patch("fabutil.powerbi.requests.get")
    def test_reports_api_errors(self, get: Mock) -> None:
        get.return_value = Mock(ok=False, status_code=403, text="Forbidden")

        with self.assertRaisesRegex(PowerBIAPIError, "HTTP 403"):
            list_tenant_refreshables("test-token")

    @patch(
        "fabutil.powerbi.requests.get",
        return_value=Mock(ok=True, json=lambda: {"items": []}),
    )
    def test_rejects_unexpected_response_shape(self, _get: Mock) -> None:
        with self.assertRaisesRegex(PowerBIAPIError, "refreshables list"):
            list_tenant_refreshables("test-token")


class FilterRefreshablesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.refreshables = [
            {
                "id": "model-one",
                "group": {"id": "workspace-one", "name": "Finance"},
                "capacity": {"id": "capacity-one", "displayName": "Premium"},
            },
            {
                "id": "model-two",
                "group": {"id": "workspace-two", "name": "Marketing"},
                "capacity": {"id": "capacity-two", "displayName": "Shared"},
            },
        ]

    def test_filters_by_workspace_name_or_id(self) -> None:
        by_name = filter_refreshables(self.refreshables, workspace="finance")
        by_id = filter_refreshables(self.refreshables, workspace="workspace-one")

        self.assertEqual(by_name, [self.refreshables[0]])
        self.assertEqual(by_id, [self.refreshables[0]])

    def test_filters_by_capacity_name_or_id(self) -> None:
        by_name = filter_refreshables(self.refreshables, capacity="premium")
        by_id = filter_refreshables(self.refreshables, capacity="capacity-two")

        self.assertEqual(by_name, [self.refreshables[0]])
        self.assertEqual(by_id, [self.refreshables[1]])

    def test_combines_workspace_and_capacity_filters(self) -> None:
        result = filter_refreshables(
            self.refreshables, workspace="Finance", capacity="Shared"
        )

        self.assertEqual(result, [])

    def test_filters_by_latest_refresh_status_case_insensitively(self) -> None:
        self.refreshables[0]["lastRefresh"] = {"status": "Completed"}
        self.refreshables[1]["lastRefresh"] = {"status": "Failed"}

        result = filter_refreshables(self.refreshables, status="failed")

        self.assertEqual(result, [self.refreshables[1]])

    def test_status_filter_excludes_refreshables_without_history(self) -> None:
        self.refreshables[0]["lastRefresh"] = None

        result = filter_refreshables(self.refreshables, status="Completed")

        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
