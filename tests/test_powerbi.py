import unittest
from unittest.mock import Mock, patch

from fabutil.powerbi import (
    ADMIN_CAPACITIES_URL,
    PowerBIAPIError,
    list_tenant_capacities,
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


if __name__ == "__main__":
    unittest.main()
