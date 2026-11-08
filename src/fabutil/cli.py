"""Command-line entry point."""

import argparse
import copy
import json
import os
import sys
from collections.abc import Sequence
from datetime import datetime, timezone
from uuid import UUID

import requests

from fabutil.auth import (
    AZURE_MANAGEMENT_SCOPE,
    FABRIC_SCOPE,
    POWER_BI_SCOPE,
    AuthenticationError,
    acquire_access_token,
)
from fabutil.azure import (
    AzureAPIError,
    find_capacity_resource,
    pause_capacity,
    resume_capacity,
)
from fabutil.fabric import (
    FabricAPIError,
    get_tenant_settings,
    list_admin_items,
    list_capacity_workspaces,
    list_capacity_tenant_setting_overrides,
    list_domain_tenant_setting_overrides,
    list_workspace_tenant_setting_overrides,
    resolve_admin_workspace_id,
)
from fabutil.powerbi import (
    PowerBIAPIError,
    filter_refreshables,
    list_tenant_capacities,
    list_tenant_refreshables,
    resolve_capacity_id,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fabutil",
        description="Command-line tools for Microsoft Fabric and Power BI.",
    )
    groups = parser.add_subparsers(dest="command_group", required=True)
    capacity_parser = groups.add_parser("capacity", help="Manage capacities.")
    capacity_commands = capacity_parser.add_subparsers(
        dest="command", required=True
    )
    list_parser = capacity_commands.add_parser(
        "list", help="List capacities across the tenant."
    )
    list_parser.add_argument(
        "--tenant-id",
        default=os.getenv("FABUTIL_TENANT_ID"),
        help="Microsoft Entra tenant ID (or FABUTIL_TENANT_ID).",
    )
    list_parser.add_argument(
        "--client-id",
        default=os.getenv("FABUTIL_CLIENT_ID"),
        help="Entra public-client app ID (or FABUTIL_CLIENT_ID).",
    )
    list_parser.add_argument(
        "--output",
        choices=("table", "json"),
        default="table",
        help="Output format (default: table).",
    )
    for action in ("pause", "resume"):
        action_parser = capacity_commands.add_parser(
            action,
            help=f"{action.capitalize()} a capacity.",
        )
        action_parser.add_argument(
            "--capacity",
            required=True,
            help="Capacity name or ID.",
        )
        _add_auth_arguments(action_parser)
    refreshable_parser = groups.add_parser(
        "refreshable", help="Manage refreshable Power BI items."
    )
    refreshable_commands = refreshable_parser.add_subparsers(
        dest="command", required=True
    )
    list_refreshables_parser = refreshable_commands.add_parser(
        "list", help="List refreshable items across the tenant."
    )
    list_refreshables_parser.add_argument(
        "--workspace",
        help="Filter by workspace name or ID.",
    )
    list_refreshables_parser.add_argument(
        "--capacity",
        help="Filter by capacity name or ID.",
    )
    list_refreshables_parser.add_argument(
        "--status",
        help="Filter locally by latest refresh status (for example, Completed or Failed).",
    )
    list_refreshables_parser.add_argument(
        "--time-zone",
        choices=("utc", "local"),
        default="utc",
        help="Display timestamps in UTC (default) or the local time zone.",
    )
    _add_auth_arguments(list_refreshables_parser)
    list_refreshables_parser.add_argument(
        "--output",
        choices=("table", "json"),
        default="table",
        help="Output format (default: table).",
    )
    workspace_parser = groups.add_parser("workspace", help="Manage workspaces.")
    workspace_commands = workspace_parser.add_subparsers(
        dest="command", required=True
    )
    list_workspaces_parser = workspace_commands.add_parser(
        "list", help="List workspaces assigned to a capacity."
    )
    list_workspaces_parser.add_argument(
        "--capacity",
        required=True,
        help="Capacity name or ID.",
    )
    _add_auth_arguments(list_workspaces_parser)
    list_workspaces_parser.add_argument(
        "--output",
        choices=("table", "json"),
        default="table",
        help="Output format (default: table).",
    )
    item_parser = groups.add_parser("item", help="Manage workspace items.")
    item_commands = item_parser.add_subparsers(dest="command", required=True)
    list_items_parser = item_commands.add_parser(
        "list", help="List active items across the tenant."
    )
    list_items_parser.add_argument(
        "--workspace",
        help="Filter by workspace name or ID.",
    )
    list_items_parser.add_argument(
        "--capacity",
        help="Filter by capacity name or ID.",
    )
    list_items_parser.add_argument(
        "--state",
        choices=("active",),
        help="Filter by item state (the Admin API currently supports active items).",
    )
    list_items_parser.add_argument(
        "--type",
        dest="item_type",
        help="Filter by Fabric item type (for example, Lakehouse or Notebook).",
    )
    _add_auth_arguments(list_items_parser)
    list_items_parser.add_argument(
        "--output",
        choices=("table", "json"),
        default="table",
        help="Output format (default: table).",
    )
    tenant_parser = groups.add_parser(
        "tenant", help="Manage tenant settings."
    )
    tenant_commands = tenant_parser.add_subparsers(
        dest="command", required=True
    )
    tenant_settings_parser = tenant_commands.add_parser(
        "settings", help="Get tenant settings and their details."
    )
    tenant_settings_commands = tenant_settings_parser.add_subparsers(
        dest="subcommand", required=True
    )
    tenant_settings_list_parser = tenant_settings_commands.add_parser(
        "list", help="List tenant settings and their details."
    )
    _add_auth_arguments(tenant_settings_list_parser)
    tenant_settings_list_parser.add_argument(
        "--output",
        choices=("table", "json"),
        default="table",
        help="Output format (default: table).",
    )
    tenant_overrides_parser = tenant_commands.add_parser(
        "overrides",
        help="List capacity and domain tenant setting overrides.",
    )
    tenant_overrides_commands = tenant_overrides_parser.add_subparsers(
        dest="subcommand", required=True
    )
    tenant_overrides_list_parser = tenant_overrides_commands.add_parser(
        "list", help="List tenant setting overrides."
    )
    _add_auth_arguments(tenant_overrides_list_parser)
    tenant_overrides_list_parser.add_argument(
        "--scope",
        choices=("capacity", "domain", "workspace"),
        help=(
            "Restrict results to capacity, domain, or workspace overrides "
            "(default: all scopes)."
        ),
    )
    tenant_overrides_list_parser.add_argument(
        "--output",
        choices=("table", "json"),
        default="table",
        help="Output format (default: table).",
    )
    return parser


def _add_auth_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--tenant-id",
        default=os.getenv("FABUTIL_TENANT_ID"),
        help="Microsoft Entra tenant ID (or FABUTIL_TENANT_ID).",
    )
    parser.add_argument(
        "--client-id",
        default=os.getenv("FABUTIL_CLIENT_ID"),
        help="Entra public-client app ID (or FABUTIL_CLIENT_ID).",
    )


def _format_table(capacities: list[dict[str, object]]) -> str:
    columns = ("displayName", "sku", "state", "region", "id")
    headers = ("NAME", "SKU", "STATE", "REGION", "ID")
    rows = [
        [str(capacity.get(column) or "-") for column in columns]
        for capacity in capacities
    ]
    widths = [
        max([len(header), *(len(row[index]) for row in rows)])
        for index, header in enumerate(headers)
    ]
    lines = [
        "  ".join(header.ljust(widths[index]) for index, header in enumerate(headers)),
        "  ".join("-" * width for width in widths),
    ]
    lines.extend(
        "  ".join(value.ljust(widths[index]) for index, value in enumerate(row))
        for row in rows
    )
    return "\n".join(lines)


def _format_workspace_table(workspaces: list[dict[str, object]]) -> str:
    columns = ("name", "type", "state", "id", "capacityId")
    headers = ("NAME", "TYPE", "STATE", "ID", "CAPACITY ID")
    rows = [
        [str(workspace.get(column) or "-") for column in columns]
        for workspace in workspaces
    ]
    widths = [
        max([len(header), *(len(row[index]) for row in rows)])
        for index, header in enumerate(headers)
    ]
    lines = [
        "  ".join(header.ljust(widths[index]) for index, header in enumerate(headers)),
        "  ".join("-" * width for width in widths),
    ]
    lines.extend(
        "  ".join(value.ljust(widths[index]) for index, value in enumerate(row))
        for row in rows
    )
    return "\n".join(lines)


def _format_item_table(items: list[dict[str, object]]) -> str:
    columns = (
        "displayName",
        "type",
        "state",
        "id",
        "workspaceId",
        "capacityId",
    )
    headers = ("NAME", "TYPE", "STATE", "ID", "WORKSPACE ID", "CAPACITY ID")
    rows = [
        [str(item.get(column) or "-") for column in columns]
        for item in items
    ]
    widths = [
        max([len(header), *(len(row[index]) for row in rows)])
        for index, header in enumerate(headers)
    ]
    lines = [
        "  ".join(header.ljust(widths[index]) for index, header in enumerate(headers)),
        "  ".join("-" * width for width in widths),
    ]
    lines.extend(
        "  ".join(value.ljust(widths[index]) for index, value in enumerate(row))
        for row in rows
    )
    return "\n".join(lines)


def _format_tenant_settings_table(
    settings: list[dict[str, object]],
) -> str:
    rows = [
        [
            str(setting.get("settingName") or "-"),
            str(setting.get("enabled") if "enabled" in setting else "-"),
            json.dumps(
                {
                    key: value
                    for key, value in setting.items()
                    if key not in ("settingName", "enabled")
                },
                sort_keys=True,
            ),
        ]
        for setting in settings
    ]
    headers = ("SETTING", "ENABLED", "DETAILS")
    widths = [
        max([len(header), *(len(row[index]) for row in rows)])
        for index, header in enumerate(headers)
    ]
    lines = [
        "  ".join(header.ljust(widths[index]) for index, header in enumerate(headers)),
        "  ".join("-" * width for width in widths),
    ]
    lines.extend(
        "  ".join(value.ljust(widths[index]) for index, value in enumerate(row))
        for row in rows
    )
    return "\n".join(lines)


def _format_tenant_overrides_table(
    overrides: list[dict[str, object]],
) -> str:
    rows = [
        [
            str(override.get("scope") or "-"),
            str(override.get("id") or "-"),
            json.dumps(override.get("tenantSettings", []), sort_keys=True),
        ]
        for override in overrides
    ]
    headers = ("SCOPE", "ID", "TENANT SETTINGS OVERRIDES")
    widths = [
        max([len(header), *(len(row[index]) for row in rows)])
        for index, header in enumerate(headers)
    ]
    lines = [
        "  ".join(header.ljust(widths[index]) for index, header in enumerate(headers)),
        "  ".join("-" * width for width in widths),
    ]
    lines.extend(
        "  ".join(value.ljust(widths[index]) for index, value in enumerate(row))
        for row in rows
    )
    return "\n".join(lines)


def _format_timestamp(value: object, time_zone: str) -> str:
    if not isinstance(value, str) or not value:
        return "-"
    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return value
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    if time_zone == "local":
        return timestamp.astimezone().isoformat()
    return timestamp.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _refreshables_for_output(
    refreshables: list[dict[str, object]], time_zone: str
) -> list[dict[str, object]]:
    result = copy.deepcopy(refreshables)
    if time_zone == "utc":
        return result

    def convert_timestamps(value: object) -> None:
        if isinstance(value, dict):
            for key, nested_value in value.items():
                if key in ("startTime", "endTime") and isinstance(
                    nested_value, str
                ):
                    value[key] = _format_timestamp(nested_value, time_zone)
                else:
                    convert_timestamps(nested_value)
        elif isinstance(value, list):
            for nested_value in value:
                convert_timestamps(nested_value)

    for refreshable in result:
        convert_timestamps(refreshable)
    return result


def _format_refreshables_table(
    refreshables: list[dict[str, object]], time_zone: str
) -> str:
    rows = []
    for refreshable in refreshables:
        last_refresh = refreshable.get("lastRefresh")
        last_refresh = last_refresh if isinstance(last_refresh, dict) else {}
        workspace = refreshable.get("group")
        workspace = workspace if isinstance(workspace, dict) else {}
        capacity = refreshable.get("capacity")
        capacity = capacity if isinstance(capacity, dict) else {}
        rows.append(
            [
                str(refreshable.get("name") or "-"),
                str(refreshable.get("kind") or "-"),
                str(last_refresh.get("status") or "-"),
                _format_timestamp(last_refresh.get("startTime"), time_zone),
                _format_timestamp(last_refresh.get("endTime"), time_zone),
                str(workspace.get("name") or "-"),
                str(capacity.get("displayName") or "-"),
            ]
        )

    headers = (
        "ITEM",
        "TYPE",
        "LATEST STATUS",
        "START TIME",
        "END TIME",
        "WORKSPACE",
        "CAPACITY",
    )
    widths = [
        max([len(header), *(len(row[index]) for row in rows)])
        for index, header in enumerate(headers)
    ]
    lines = [
        "  ".join(header.ljust(widths[index]) for index, header in enumerate(headers)),
        "  ".join("-" * width for width in widths),
    ]
    lines.extend(
        "  ".join(value.ljust(widths[index]) for index, value in enumerate(row))
        for row in rows
    )
    return "\n".join(lines)


def _print_table(table: str) -> None:
    print(f"\n{table}\n")


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if not args.tenant_id:
        parser.error("provide --tenant-id or set FABUTIL_TENANT_ID")
    if not args.client_id:
        parser.error("provide --client-id or set FABUTIL_CLIENT_ID")

    try:
        if args.command_group == "capacity" and args.command == "list":
            access_token = acquire_access_token(
                args.tenant_id, args.client_id, POWER_BI_SCOPE
            )
            capacities = list_tenant_capacities(access_token)
            output_rows = capacities
        elif args.command_group == "capacity":
            azure_token = acquire_access_token(
                args.tenant_id, args.client_id, AZURE_MANAGEMENT_SCOPE
            )
            capacity_list = None
            try:
                UUID(args.capacity)
            except ValueError:
                pass
            else:
                power_bi_token = acquire_access_token(
                    args.tenant_id, args.client_id, POWER_BI_SCOPE
                )
                capacity_list = list_tenant_capacities(power_bi_token)
            capacity_resource = find_capacity_resource(
                azure_token, args.capacity, capacity_list
            )
            if args.command == "pause":
                pause_capacity(
                    azure_token,
                    capacity_resource["subscription_id"],
                    capacity_resource["resource_group"],
                    capacity_resource["capacity_name"],
                )
                action = "pause"
            else:
                resume_capacity(
                    azure_token,
                    capacity_resource["subscription_id"],
                    capacity_resource["resource_group"],
                    capacity_resource["capacity_name"],
                )
                action = "resume"
            print(
                "Capacity "
                f"{action} request accepted for {capacity_resource['capacity_name']}."
            )
            return 0
        elif args.command_group == "workspace":
            try:
                capacity_id = str(UUID(args.capacity))
            except ValueError:
                power_bi_token = acquire_access_token(
                    args.tenant_id, args.client_id, POWER_BI_SCOPE
                )
                capacity_id = resolve_capacity_id(power_bi_token, args.capacity)

            fabric_token = acquire_access_token(
                args.tenant_id, args.client_id, FABRIC_SCOPE
            )
            workspaces = list_capacity_workspaces(fabric_token, capacity_id)
        elif args.command_group == "refreshable":
            access_token = acquire_access_token(
                args.tenant_id, args.client_id, POWER_BI_SCOPE
            )
            refreshables = list_tenant_refreshables(access_token)
            output_rows = filter_refreshables(
                refreshables,
                workspace=args.workspace,
                capacity=args.capacity,
                status=args.status,
            )
        elif args.command_group == "tenant":
            access_token = acquire_access_token(
                args.tenant_id, args.client_id, FABRIC_SCOPE
            )
            if args.command == "settings":
                tenant_settings = get_tenant_settings(access_token)
            else:
                tenant_overrides = []
                if args.scope in (None, "capacity"):
                    tenant_overrides.extend(
                        {
                            **override,
                            "scope": "capacity",
                        }
                        for override in list_capacity_tenant_setting_overrides(
                            access_token
                        )
                    )
                if args.scope in (None, "domain"):
                    tenant_overrides.extend(
                        {
                            **override,
                            "scope": "domain",
                        }
                        for override in list_domain_tenant_setting_overrides(
                            access_token
                        )
                    )
                if args.scope in (None, "workspace"):
                    tenant_overrides.extend(
                        {
                            **override,
                            "scope": "workspace",
                        }
                        for override in list_workspace_tenant_setting_overrides(
                            access_token
                        )
                    )
        else:
            capacity_id = None
            if args.capacity:
                try:
                    capacity_id = str(UUID(args.capacity))
                except ValueError:
                    power_bi_token = acquire_access_token(
                        args.tenant_id, args.client_id, POWER_BI_SCOPE
                    )
                    capacity_id = resolve_capacity_id(
                        power_bi_token, args.capacity
                    )
            access_token = acquire_access_token(
                args.tenant_id, args.client_id, FABRIC_SCOPE
            )
            workspace_id = None
            if args.workspace:
                try:
                    workspace_id = str(UUID(args.workspace))
                except ValueError:
                    workspace_id = resolve_admin_workspace_id(
                        access_token, args.workspace, capacity_id
                    )
            items = list_admin_items(
                access_token,
                workspace_id=workspace_id,
                capacity_id=capacity_id,
                state=args.state,
                item_type=args.item_type,
            )
            items = [
                {
                    **{key: value for key, value in item.items() if key != "name"},
                    **(
                        {"displayName": item["name"]}
                        if "name" in item
                        else {}
                    ),
                }
                for item in items
            ]
    except AuthenticationError as exc:
        print(f"Authentication error: {exc}", file=sys.stderr)
        return 1
    except PowerBIAPIError as exc:
        print(f"Power BI API error: {exc}", file=sys.stderr)
        return 1
    except FabricAPIError as exc:
        print(f"Fabric API error: {exc}", file=sys.stderr)
        return 1
    except AzureAPIError as exc:
        print(f"Azure API error: {exc}", file=sys.stderr)
        return 1
    except requests.RequestException as exc:
        print(f"Network error communicating with Microsoft APIs: {exc}", file=sys.stderr)
        return 1

    if args.command_group == "workspace":
        output_rows = workspaces
    elif args.command_group == "item":
        output_rows = items
    elif args.command_group == "tenant":
        output_rows = (
            tenant_settings
            if args.command == "settings"
            else tenant_overrides
        )

    if args.output == "json":
        if args.command_group == "refreshable":
            output_rows = _refreshables_for_output(output_rows, args.time_zone)
        print(json.dumps(output_rows, indent=2))
    elif args.command_group == "workspace":
        _print_table(_format_workspace_table(workspaces))
    elif args.command_group == "item":
        _print_table(_format_item_table(items))
    elif args.command_group == "tenant":
        if args.command == "settings":
            _print_table(_format_tenant_settings_table(tenant_settings))
        else:
            _print_table(_format_tenant_overrides_table(tenant_overrides))
    elif args.command_group == "refreshable":
        _print_table(_format_refreshables_table(output_rows, args.time_zone))
    else:
        _print_table(_format_table(output_rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
