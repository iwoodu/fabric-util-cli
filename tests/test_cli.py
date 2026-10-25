import contextlib
import io
import json
import unittest
from unittest.mock import Mock, call, patch

from fabutil.auth import FABRIC_SCOPE, POWER_BI_SCOPE
from fabutil.cli import (
    _format_refreshables_table,
    _format_timestamp,
    main,
)


CAPACITY_ID = "a0b1c2d3-e4f5-4678-9012-3456789abcde"


class CapacityListCommandTests(unittest.TestCase):
    @patch("fabutil.cli.list_tenant_capacities")
    @patch("fabutil.cli.acquire_access_token", return_value="user-token")
    def test_outputs_all_capacities_as_json(
        self, _acquire_token: Mock, list_capacities: Mock
    ) -> None:
        capacities = [
            {"id": CAPACITY_ID, "region": "West US"},
            {"id": "b0b1c2d3-e4f5-4678-9012-3456789abcde", "region": "East US"},
        ]
        list_capacities.return_value = capacities
        stdout = io.StringIO()

        with contextlib.redirect_stdout(stdout):
            result = main(
                [
                    "capacity",
                    "list",
                    "--tenant-id",
                    "tenant-id",
                    "--client-id",
                    "client-id",
                    "--output",
                    "json",
                ]
            )

        self.assertEqual(result, 0)
        self.assertEqual(json.loads(stdout.getvalue()), capacities)

    @patch("fabutil.cli.list_tenant_capacities", return_value=[])
    @patch("fabutil.cli.acquire_access_token", return_value="user-token")
    def test_separates_table_output_with_blank_lines(
        self, _acquire_token: Mock, _list_capacities: Mock
    ) -> None:
        stdout = io.StringIO()

        with contextlib.redirect_stdout(stdout):
            result = main(
                [
                    "capacity",
                    "list",
                    "--tenant-id",
                    "tenant-id",
                    "--client-id",
                    "client-id",
                ]
            )

        self.assertEqual(result, 0)
        self.assertTrue(stdout.getvalue().startswith("\nNAME"))
        self.assertTrue(stdout.getvalue().endswith("\n\n"))


class WorkspaceListCommandTests(unittest.TestCase):
    @patch("fabutil.cli.list_capacity_workspaces")
    @patch("fabutil.cli.acquire_access_token", return_value="fabric-token")
    def test_lists_workspaces_by_capacity_id(
        self, acquire_token: Mock, list_workspaces: Mock
    ) -> None:
        workspaces = [{"id": "workspace-id", "name": "Finance"}]
        list_workspaces.return_value = workspaces
        stdout = io.StringIO()

        with contextlib.redirect_stdout(stdout):
            result = main(
                [
                    "workspace",
                    "list",
                    "--capacity",
                    CAPACITY_ID,
                    "--tenant-id",
                    "tenant-id",
                    "--client-id",
                    "client-id",
                    "--output",
                    "json",
                ]
            )

        self.assertEqual(result, 0)
        self.assertEqual(json.loads(stdout.getvalue()), workspaces)
        acquire_token.assert_called_once_with("tenant-id", "client-id", FABRIC_SCOPE)
        list_workspaces.assert_called_once_with("fabric-token", CAPACITY_ID)

    @patch("fabutil.cli.list_capacity_workspaces", return_value=[])
    @patch("fabutil.cli.resolve_capacity_id", return_value=CAPACITY_ID)
    @patch(
        "fabutil.cli.acquire_access_token",
        side_effect=["powerbi-token", "fabric-token"],
    )
    def test_resolves_capacity_name_using_power_bi_then_fabric(
        self,
        acquire_token: Mock,
        resolve_capacity: Mock,
        list_workspaces: Mock,
    ) -> None:
        stdout = io.StringIO()

        with contextlib.redirect_stdout(stdout):
            result = main(
                [
                    "workspace",
                    "list",
                    "--capacity",
                    "Finance",
                    "--tenant-id",
                    "tenant-id",
                    "--client-id",
                    "client-id",
                ]
            )

        self.assertEqual(result, 0)
        self.assertTrue(stdout.getvalue().startswith("\nNAME"))
        self.assertTrue(stdout.getvalue().endswith("\n\n"))
        self.assertEqual(
            acquire_token.call_args_list,
            [
                call("tenant-id", "client-id", POWER_BI_SCOPE),
                call("tenant-id", "client-id", FABRIC_SCOPE),
            ],
        )
        resolve_capacity.assert_called_once_with("powerbi-token", "Finance")
        list_workspaces.assert_called_once_with("fabric-token", CAPACITY_ID)


class ItemListCommandTests(unittest.TestCase):
    @patch("fabutil.cli.list_admin_items")
    @patch("fabutil.cli.acquire_access_token", return_value="fabric-admin-token")
    def test_lists_tenant_items_as_json(
        self, acquire_token: Mock, list_items: Mock
    ) -> None:
        items = [
            {
                "id": "item-id",
                "name": "Sales lakehouse",
                "type": "Lakehouse",
                "state": "Active",
                "workspaceId": "workspace-id",
                "capacityId": "capacity-id",
            }
        ]
        list_items.return_value = items
        stdout = io.StringIO()

        with contextlib.redirect_stdout(stdout):
            result = main(
                [
                    "item",
                    "list",
                    "--tenant-id",
                    "tenant-id",
                    "--client-id",
                    "client-id",
                    "--output",
                    "json",
                ]
            )

        self.assertEqual(result, 0)
        self.assertEqual(
            json.loads(stdout.getvalue()),
            [
                {
                    "id": "item-id",
                    "displayName": "Sales lakehouse",
                    "type": "Lakehouse",
                    "state": "Active",
                    "workspaceId": "workspace-id",
                    "capacityId": "capacity-id",
                }
            ],
        )
        acquire_token.assert_called_once_with(
            "tenant-id", "client-id", FABRIC_SCOPE
        )
        list_items.assert_called_once_with(
            "fabric-admin-token",
            workspace_id=None,
            capacity_id=None,
            state=None,
            item_type=None,
        )

    @patch("fabutil.cli.list_admin_items", return_value=[])
    @patch("fabutil.cli.resolve_admin_workspace_id", return_value=CAPACITY_ID)
    @patch("fabutil.cli.acquire_access_token", return_value="fabric-admin-token")
    def test_resolves_workspace_name_with_capacity_filter(
        self,
        acquire_token: Mock,
        resolve_workspace: Mock,
        list_items: Mock,
    ) -> None:
        stdout = io.StringIO()

        with contextlib.redirect_stdout(stdout):
            result = main(
                [
                    "item",
                    "list",
                    "--workspace",
                    "Finance",
                    "--capacity",
                    CAPACITY_ID,
                    "--state",
                    "active",
                    "--type",
                    "Lakehouse",
                    "--tenant-id",
                    "tenant-id",
                    "--client-id",
                    "client-id",
                    "--output",
                    "json",
                ]
            )

        self.assertEqual(result, 0)
        acquire_token.assert_called_once_with(
            "tenant-id", "client-id", FABRIC_SCOPE
        )
        resolve_workspace.assert_called_once_with(
            "fabric-admin-token", "Finance", CAPACITY_ID
        )
        list_items.assert_called_once_with(
            "fabric-admin-token",
            workspace_id=CAPACITY_ID,
            capacity_id=CAPACITY_ID,
            state="active",
            item_type="Lakehouse",
        )

    @patch("fabutil.cli.list_admin_items", return_value=[])
    @patch("fabutil.cli.resolve_capacity_id", return_value=CAPACITY_ID)
    @patch(
        "fabutil.cli.acquire_access_token",
        side_effect=["powerbi-token", "fabric-admin-token"],
    )
    def test_resolves_capacity_name_and_passes_filters(
        self, acquire_token: Mock, resolve_capacity: Mock, list_items: Mock
    ) -> None:
        stdout = io.StringIO()

        with contextlib.redirect_stdout(stdout):
            result = main(
                [
                    "item",
                    "list",
                    "--capacity",
                    "Premium",
                    "--state",
                    "active",
                    "--type",
                    "Notebook",
                    "--tenant-id",
                    "tenant-id",
                    "--client-id",
                    "client-id",
                ]
            )

        self.assertEqual(result, 0)
        self.assertTrue(stdout.getvalue().startswith("\nNAME"))
        self.assertTrue(stdout.getvalue().endswith("\n\n"))
        self.assertEqual(
            acquire_token.call_args_list,
            [
                call("tenant-id", "client-id", POWER_BI_SCOPE),
                call("tenant-id", "client-id", FABRIC_SCOPE),
            ],
        )
        resolve_capacity.assert_called_once_with("powerbi-token", "Premium")
        list_items.assert_called_once_with(
            "fabric-admin-token",
            workspace_id=None,
            capacity_id=CAPACITY_ID,
            state="active",
            item_type="Notebook",
        )


class RefreshableListCommandTests(unittest.TestCase):
    @patch("fabutil.cli.filter_refreshables")
    @patch("fabutil.cli.list_tenant_refreshables")
    @patch("fabutil.cli.acquire_access_token", return_value="powerbi-token")
    def test_lists_refreshables_with_context_as_json(
        self,
        acquire_token: Mock,
        list_refreshables: Mock,
        filter_rows: Mock,
    ) -> None:
        refreshables = [
            {
                "id": "model-id",
                "name": "Sales",
                "kind": "Dataset",
                "lastRefresh": {
                    "status": "Completed",
                    "startTime": "2026-10-24T14:00:00Z",
                    "endTime": "2026-10-24T14:05:00Z",
                },
                "group": {"id": "workspace-id", "name": "Finance"},
                "capacity": {"id": "capacity-id", "displayName": "Premium"},
            }
        ]
        list_refreshables.return_value = refreshables
        filter_rows.return_value = refreshables
        stdout = io.StringIO()

        with contextlib.redirect_stdout(stdout):
            result = main(
                [
                    "refreshable",
                    "list",
                    "--tenant-id",
                    "tenant-id",
                    "--client-id",
                    "client-id",
                    "--output",
                    "json",
                ]
            )

        self.assertEqual(result, 0)
        self.assertEqual(json.loads(stdout.getvalue()), refreshables)
        acquire_token.assert_called_once_with(
            "tenant-id", "client-id", POWER_BI_SCOPE
        )
        list_refreshables.assert_called_once_with("powerbi-token")
        filter_rows.assert_called_once_with(
            refreshables, workspace=None, capacity=None, status=None
        )

    @patch("fabutil.cli.filter_refreshables", return_value=[])
    @patch("fabutil.cli.list_tenant_refreshables", return_value=[])
    @patch("fabutil.cli.acquire_access_token", return_value="powerbi-token")
    def test_passes_workspace_and_capacity_filters(
        self,
        _acquire_token: Mock,
        _list_refreshables: Mock,
        filter_rows: Mock,
    ) -> None:
        stdout = io.StringIO()

        with contextlib.redirect_stdout(stdout):
            result = main(
                [
                    "refreshable",
                    "list",
                    "--workspace",
                    "Finance",
                    "--capacity",
                    "Premium",
                    "--status",
                    "Failed",
                    "--tenant-id",
                    "tenant-id",
                    "--client-id",
                    "client-id",
                ]
            )

        self.assertEqual(result, 0)
        filter_rows.assert_called_once_with(
            [], workspace="Finance", capacity="Premium", status="Failed"
        )
        self.assertIn("WORKSPACE", stdout.getvalue())
        self.assertIn("CAPACITY", stdout.getvalue())

    def test_formats_utc_timestamp_with_z_suffix(self) -> None:
        result = _format_timestamp("2026-10-24T20:35:30+00:00", "utc")

        self.assertEqual(result, "2026-10-24T20:35:30Z")

    def test_formats_refreshable_start_and_end_times_in_table(self) -> None:
        refreshable = {
            "name": "Sales",
            "kind": "Dataset",
            "lastRefresh": {
                "status": "Completed",
                "startTime": "2026-10-24T20:35:30Z",
                "endTime": "2026-10-24T20:40:30Z",
            },
            "group": {"name": "Finance"},
            "capacity": {"displayName": "Premium"},
        }

        table = _format_refreshables_table([refreshable], "utc")

        self.assertIn("2026-10-24T20:35:30Z", table)
        self.assertIn("2026-10-24T20:40:30Z", table)
        self.assertIn("Finance", table)
        self.assertIn("Premium", table)


if __name__ == "__main__":
    unittest.main()
