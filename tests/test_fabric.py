import unittest
from unittest.mock import Mock, call, patch

from fabutil.fabric import (
    ADMIN_ITEMS_URL,
    ADMIN_WORKSPACES_URL,
    FabricAPIError,
    list_admin_items,
    list_admin_workspaces,
    list_capacity_workspaces,
    resolve_admin_workspace_id,
)


CAPACITY_ID = "a0b1c2d3-e4f5-4678-9012-3456789abcde"
WORKSPACE_ID = "b0b1c2d3-e4f5-4678-9012-3456789abcde"


class ListAdminWorkspacesTests(unittest.TestCase):
    @patch("fabutil.fabric.requests.get")
    def test_lists_capacity_workspaces(self, get: Mock) -> None:
        workspace = {"id": WORKSPACE_ID, "name": "Finance"}
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
    def test_filters_workspaces_by_name_and_capacity(self, get: Mock) -> None:
        get.return_value = Mock(
            ok=True,
            json=lambda: {
                "workspaces": [{"id": WORKSPACE_ID, "name": "Finance"}],
            },
        )

        result = list_admin_workspaces(
            "fabric-token", capacity_id=CAPACITY_ID, name="Finance"
        )

        self.assertEqual(result[0]["name"], "Finance")
        get.assert_called_once_with(
            ADMIN_WORKSPACES_URL,
            headers={"Authorization": "Bearer fabric-token"},
            params={"capacityId": CAPACITY_ID, "name": "Finance"},
            timeout=30,
        )

    @patch("fabutil.fabric.requests.get")
    def test_paginates_and_detects_repeated_tokens(self, get: Mock) -> None:
        first = {"id": "one"}
        second = {"id": "two"}
        get.side_effect = [
            Mock(
                ok=True,
                json=lambda: {
                    "workspaces": [first],
                    "continuationToken": "next",
                },
            ),
            Mock(
                ok=True,
                json=lambda: {
                    "workspaces": [second],
                    "continuationToken": None,
                },
            ),
        ]

        self.assertEqual(
            list_capacity_workspaces("fabric-token", CAPACITY_ID),
            [first, second],
        )
        self.assertEqual(get.call_count, 2)
        self.assertEqual(
            get.call_args_list[1].kwargs["params"],
            {"capacityId": CAPACITY_ID, "continuationToken": "next"},
        )

    @patch("fabutil.fabric.requests.get")
    def test_reports_http_errors(self, get: Mock) -> None:
        get.return_value = Mock(ok=False, status_code=403, text="Forbidden")

        with self.assertRaisesRegex(FabricAPIError, "HTTP 403"):
            list_capacity_workspaces("fabric-token", CAPACITY_ID)

    @patch("fabutil.fabric.requests.get")
    def test_rejects_invalid_workspace_payload(self, get: Mock) -> None:
        get.return_value = Mock(ok=True, json=lambda: {"items": []})

        with self.assertRaisesRegex(FabricAPIError, "workspaces list"):
            list_capacity_workspaces("fabric-token", CAPACITY_ID)

    @patch("fabutil.fabric.list_admin_workspaces")
    def test_resolves_workspace_name_case_insensitively(
        self, list_workspaces: Mock
    ) -> None:
        list_workspaces.return_value = [
            {"id": WORKSPACE_ID, "name": "Finance"},
            {"id": "other-id", "name": "Engineering"},
        ]

        result = resolve_admin_workspace_id(
            "fabric-token", "finance", capacity_id=CAPACITY_ID
        )

        self.assertEqual(result, WORKSPACE_ID)
        list_workspaces.assert_called_once_with(
            "fabric-token", capacity_id=CAPACITY_ID, name="finance"
        )

    @patch(
        "fabutil.fabric.list_admin_workspaces",
        return_value=[
            {"id": "one", "name": "Finance"},
            {"id": "two", "name": "Finance"},
        ],
    )
    def test_rejects_ambiguous_workspace_name(self, _list_workspaces: Mock) -> None:
        with self.assertRaisesRegex(FabricAPIError, "use its workspace ID"):
            resolve_admin_workspace_id("fabric-token", "Finance")

    @patch("fabutil.fabric.list_admin_workspaces", return_value=[])
    def test_reports_workspace_name_not_found(self, _list_workspaces: Mock) -> None:
        with self.assertRaisesRegex(FabricAPIError, "No workspace named"):
            resolve_admin_workspace_id("fabric-token", "Missing")


class ListAdminItemsTests(unittest.TestCase):
    @patch("fabutil.fabric.requests.get")
    def test_lists_all_admin_items(self, get: Mock) -> None:
        item = {"id": "item-id", "name": "Lakehouse", "type": "Lakehouse"}
        get.return_value = Mock(
            ok=True,
            json=lambda: {"itemEntities": [item], "continuationToken": None},
        )

        result = list_admin_items("fabric-token")

        self.assertEqual(result, [item])
        get.assert_called_once_with(
            ADMIN_ITEMS_URL,
            headers={"Authorization": "Bearer fabric-token"},
            params={},
            timeout=30,
        )

    @patch("fabutil.fabric.requests.get")
    def test_sends_filters_and_follows_continuation_token(self, get: Mock) -> None:
        first = {"id": "one", "name": "First"}
        second = {"id": "two", "name": "Second"}
        get.side_effect = [
            Mock(
                ok=True,
                json=lambda: {
                    "itemEntities": [first],
                    "continuationToken": "next-page",
                },
            ),
            Mock(
                ok=True,
                json=lambda: {"itemEntities": [second], "continuationToken": None},
            ),
        ]

        result = list_admin_items(
            "fabric-token",
            workspace_id=WORKSPACE_ID,
            capacity_id=CAPACITY_ID,
            state="active",
            item_type="Lakehouse",
        )

        self.assertEqual(result, [first, second])
        self.assertEqual(
            get.call_args_list,
            [
                call(
                    ADMIN_ITEMS_URL,
                    headers={"Authorization": "Bearer fabric-token"},
                    params={
                        "workspaceId": WORKSPACE_ID,
                        "capacityId": CAPACITY_ID,
                        "state": "active",
                        "type": "Lakehouse",
                    },
                    timeout=30,
                ),
                call(
                    ADMIN_ITEMS_URL,
                    headers={"Authorization": "Bearer fabric-token"},
                    params={
                        "workspaceId": WORKSPACE_ID,
                        "capacityId": CAPACITY_ID,
                        "state": "active",
                        "type": "Lakehouse",
                        "continuationToken": "next-page",
                    },
                    timeout=30,
                ),
            ],
        )

    @patch("fabutil.fabric.requests.get")
    def test_rejects_invalid_item_payload(self, get: Mock) -> None:
        get.return_value = Mock(ok=True, json=lambda: {"value": []})

        with self.assertRaisesRegex(FabricAPIError, "itemEntities list"):
            list_admin_items("fabric-token")

    @patch("fabutil.fabric.requests.get")
    def test_rejects_invalid_json(self, get: Mock) -> None:
        get.return_value = Mock(
            ok=True,
            json=Mock(side_effect=ValueError("invalid JSON")),
        )

        with self.assertRaisesRegex(FabricAPIError, "invalid JSON"):
            list_admin_items("fabric-token")

    @patch("fabutil.fabric.requests.get")
    def test_reports_http_errors(self, get: Mock) -> None:
        get.return_value = Mock(ok=False, status_code=403, text="Forbidden")

        with self.assertRaisesRegex(FabricAPIError, "HTTP 403"):
            list_admin_items("fabric-token")

    @patch("fabutil.fabric.requests.get")
    def test_stops_on_repeated_continuation_token(self, get: Mock) -> None:
        response = Mock(
            ok=True,
            json=lambda: {
                "itemEntities": [],
                "continuationToken": "repeat",
            },
        )
        get.side_effect = [response, response]

        with self.assertRaisesRegex(FabricAPIError, "repeated continuation token"):
            list_admin_items("fabric-token")
