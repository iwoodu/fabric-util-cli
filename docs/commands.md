# Command Reference

Commands use this shape:

```text
fabutil [command-group] [sub-command group] [command] [options]
```
## Usage Instructions

Commands by default output in console friendly, tabular format.

Commands support JSON output using the `--output json` option.

Use OS utilities, like `jq` to apply custom filtering, sorting, and other decorations. For example:

```sh
fabutil capacity list --output json | jq '[.[] | select(.sku == "PP3" and (.state | ascii_downcase) == "active")]'
```

## CLI Command Groups
The following command groups are supported by the CLI.

* [capacity](commands/capacity.md)
* [item](commands/item.md)
* [refreshable](commands/refreshable.md)
* [tenant](commands/tenant.md)
* [workspace](commands/workspace.md)

Usage instructions are available using the `--help` option.



To filter or transform results, request JSON and pipe it to a tool such as
[`jq`](https://jqlang.org/):

```sh
fabutil capacity list --output json | \
  jq '[.[] | select(.sku == "PP3" and (.state | ascii_downcase) == "active")]'
```

This example selects capacities with SKU `PP3` and state `Active`. `jq` is an
optional, separate user-installed dependency; fabutil itself does not require
it. Use `jq` expressions to filter by other returned fields, such as `id`,
`displayName` (capacity name), or `region`.

To display in table format instead of JSON:

**MacOS, Linux**
```sh
fabutil capacity list --output json | \
  jq -r '
    [.[] | select(.sku == "PP3" and (.state | ascii_downcase) == "active")] as $caps |
    (["NAME", "SKU", "STATE", "REGION", "ID"],
     ($caps[] | [.displayName // "-", .sku // "-", .state // "-", .region // "-", .id // "-"]))
    | @tsv
  ' | \
  column -t -s "$(printf '\t')"
```

**Windows PowerShell**
```powershell
fabutil capacity list --output json `
  | jq -c '[.[] | select(.sku == "PP3" and (.state | ascii_downcase) == "active")]' `
  | ConvertFrom-Json `
  | Format-Table displayName, sku, state, region, id -AutoSize
```




## How this command works

- `cli.py` defines the `capacity list` command and its options.
- `auth.py` uses MSAL to sign in the current user through a browser and obtain a
  delegated access token, silently reusing an encrypted persistent cache when
  a single account is cached.
- `powerbi.py` sends that token to `GET /v1.0/myorg/admin/capacities`.
- `fabric.py` sends the Fabric token to `GET /v1/admin/tenantsettings` for
  `tenant settings list`.

Filtering is left to a downstream pipe tool unless a future API operation
supports server-side filtering. Fabric REST APIs are preferred for operations
they support; the Power BI Admin API is used here because it supports this
tenant-wide capacity data.
