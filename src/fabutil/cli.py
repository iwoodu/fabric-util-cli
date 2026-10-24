"""Command-line entry point."""

import argparse
import json
import os
import sys
from collections.abc import Sequence
from uuid import UUID

import requests

from fabutil.auth import (
    FABRIC_SCOPE,
    POWER_BI_SCOPE,
    AuthenticationError,
    acquire_access_token,
)
from fabutil.fabric import FabricAPIError, list_capacity_workspaces
from fabutil.powerbi import (
    PowerBIAPIError,
    list_tenant_capacities,
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
        if args.command_group == "capacity":
            access_token = acquire_access_token(
                args.tenant_id, args.client_id, POWER_BI_SCOPE
            )
            capacities = list_tenant_capacities(access_token)
            output_rows = capacities
        else:
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
    except AuthenticationError as exc:
        print(f"Authentication error: {exc}", file=sys.stderr)
        return 1
    except PowerBIAPIError as exc:
        print(f"Power BI API error: {exc}", file=sys.stderr)
        return 1
    except FabricAPIError as exc:
        print(f"Fabric API error: {exc}", file=sys.stderr)
        return 1
    except requests.RequestException as exc:
        print(f"Network error communicating with Microsoft APIs: {exc}", file=sys.stderr)
        return 1

    if args.command_group == "workspace":
        output_rows = workspaces

    if args.output == "json":
        print(json.dumps(output_rows, indent=2))
    elif args.command_group == "workspace":
        _print_table(_format_workspace_table(workspaces))
    else:
        _print_table(_format_table(output_rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
