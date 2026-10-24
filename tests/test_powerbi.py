import unittest
from unittest.mock import Mock, patch

from fabutil.powerbi import (
    ADMIN_CAPACITIES_URL,
    PowerBIAPIError,
    list_tenant_capacities,
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


if __name__ == "__main__":
    unittest.main()
