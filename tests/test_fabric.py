import unittest
from unittest.mock import Mock, call, patch

from fabutil.fabric import (
    ADMIN_WORKSPACES_URL,
    FabricAPIError,
    list_capacity_workspaces,
)


CAPACITY_ID = "a0b1c2d3-e4f5-4678-9012-3456789abcde"


class ListCapacityWorkspacesTests(unittest.TestCase):
    @patch("fabutil.fabric.requests.get")
    def test_requests_workspaces_for_capacity(self, get: Mock) -> None:
        workspace = {"id": "workspace-id", "name": "Finance"}
        get.return_value = Mock(
            ok=True,
            json=lambda: {"workspaces": [workspace], "continuationToken": None},
        )

        result = list_capacity_workspaces("fabric-token", CAPACITY_ID)

        self.assertEqual(result, [workspace])
        get.assert_called_once_with(
            ADMIN_WORKSPACES_URL,
            headers={"Authorization": "Bearer fabric-token"},
            params={"capacityId": CAPACITY_ID},
            timeout=30,
        )

    @patch("fabutil.fabric.requests.get")
    def test_follows_continuation_tokens(self, get: Mock) -> None:
        first_workspace = {"id": "one"}
        second_workspace = {"id": "two"}
        get.side_effect = [
            Mock(
                ok=True,
                json=lambda: {
                    "workspaces": [first_workspace],
                    "continuationToken": "next-page",
                },
            ),
            Mock(
                ok=True,
                json=lambda: {
                    "workspaces": [second_workspace],
                    "continuationToken": None,
                },
            ),
        ]

        result = list_capacity_workspaces("fabric-token", CAPACITY_ID)

        self.assertEqual(result, [first_workspace, second_workspace])
        self.assertEqual(
            get.call_args_list,
            [
                call(
                    ADMIN_WORKSPACES_URL,
                    headers={"Authorization": "Bearer fabric-token"},
                    params={"capacityId": CAPACITY_ID},
                    timeout=30,
                ),
                call(
                    ADMIN_WORKSPACES_URL,
                    headers={"Authorization": "Bearer fabric-token"},
                    params={
                        "capacityId": CAPACITY_ID,
                        "continuationToken": "next-page",
                    },
                    timeout=30,
                ),
            ],
        )

    @patch("fabutil.fabric.requests.get")
    def test_reports_http_errors(self, get: Mock) -> None:
        get.return_value = Mock(ok=False, status_code=403, text="Forbidden")

        with self.assertRaisesRegex(FabricAPIError, "HTTP 403"):
            list_capacity_workspaces("fabric-token", CAPACITY_ID)

    @patch("fabutil.fabric.requests.get")
    def test_rejects_invalid_workspace_payload(self, get: Mock) -> None:
        get.return_value = Mock(ok=True, json=lambda: {"items": []})

        with self.assertRaisesRegex(FabricAPIError, "workspace list"):
            list_capacity_workspaces("fabric-token", CAPACITY_ID)

    @patch("fabutil.fabric.requests.get")
    def test_stops_on_repeated_continuation_token(self, get: Mock) -> None:
        response = Mock(
            ok=True,
            json=lambda: {
                "workspaces": [],
                "continuationToken": "repeat",
            },
        )
        get.side_effect = [response, response]

        with self.assertRaisesRegex(FabricAPIError, "repeated continuation token"):
            list_capacity_workspaces("fabric-token", CAPACITY_ID)


if __name__ == "__main__":
    unittest.main()
