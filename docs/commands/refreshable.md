# `refreshable` command group

## `list` command
List refreshable items across the Fabric tenant, or narrow the displayed results by workspace, capacity, and/or status.

By default, output is written to `stdout` in tabular format. The `--output json` option overrides this behavior.

```sh
fabutil refreshable list
```
List all refreshable items to `stdout` in tabular format.  The start and end refresh times are displayed int UTC.

```sh
fabutil refreshable list --workspace "Finance"
```
List refreshable items in the Finanace workspace.  The start and end refresh times are displayed int UTC.

```sh
fabutil refreshable list --capacity "Premium"
```
List refreshable items in workspaces assigned to the Premium capacity.  The start and end refresh times are displayed int UTC.

```sh
fabutil refreshable list --status Failed
```
List of refreshable items whose last refresh attempt failed.  The start and end refresh times are displayed int UTC.

```sh
fabutil refreshable list \
  --workspace "Finance" \
  --capacity "a0b1c2d3-e4f5-4678-9012-3456789abcde" \
  --status Failed \
  --time-zone local \
  --output json
```
List of refreshable items in the Finance workspace under the given capacity where the item's last refresh attempt failed. The start and end refresh times are given using the local time zone.


> WARNING
> Only datasets that have refreshed at least once or have a valid refresh schedule are returned.

> WARNING
> Dataflows are not supported by this command.

> WARNING
> Fabric retains seven days of refresh history and up to 60 refreshes per model.