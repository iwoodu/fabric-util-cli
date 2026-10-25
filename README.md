# fabutil

A tutorial-style CLI for Microsoft Fabric and Power BI. Commands use this shape:

```text
fabutil [command-group] [command] [options]
```

## First command: list tenant capacities

```sh
fabutil capacity list
fabutil capacity list --output json
```

This read-only command uses the Power BI Admin API because Fabric does not
currently provide an equivalent tenant-wide capacity API. The signed-in user
must be a Fabric administrator, and the app needs delegated `Tenant.Read.All`
permission with admin consent. The API returns the tenant-wide capacity list.
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

## Configure interactive user sign-in

The Azure CLI login attempt fails with `AADSTS65002` because Azure CLI uses a
Microsoft-owned client application that isn't preauthorized to request Power
BI API tokens in your tenant. The CLI therefore uses its own Microsoft Entra
**public client app registration** for interactive sign-in. You still
authenticate as your own user; this is not a service principal, and no client
secret is created or used.

1. Create an app registration in Microsoft Entra ID, preferably restricted to
   your organization. Copy its **Application (client) ID** and your **Directory
   (tenant) ID**.
2. In **Authentication**, choose **Add a platform** > **Mobile and desktop
   applications**. Add the custom redirect URI exactly as:

   ```text
   http://localhost
   ```

   This is a desktop/public-client redirect, not a **Web** redirect. MSAL
   listens on a temporary localhost port during sign-in; register `http://localhost`
   without a port.
3. Under **API permissions**, add **Microsoft Fabric** >
   **Delegated permissions** > `Tenant.Read.All`.
   Also add **Power BI Service** > **Delegated permissions** >
   `Tenant.Read.All` to support capacity listing and capacity-name lookup.
   Have an administrator grant consent for these permissions.
4. Install Python 3.10 or later and fabutil:

   ```sh
   python -m venv .venv
   source .venv/bin/activate
   python -m pip install -e .
   ```

5. Provide the tenant and client IDs, then run the command:

   ```sh
   export FABUTIL_TENANT_ID="<your-tenant-id>"
   export FABUTIL_CLIENT_ID="<your-app-client-id>"
   fabutil capacity list
   ```

   Or pass the IDs directly:

   ```sh
   fabutil capacity list \
     --tenant-id "<your-tenant-id>" \
     --client-id "<your-app-client-id>"
   ```

The first run opens a browser for sign-in. On later runs, fabutil silently
reuses or refreshes the cached token when possible and opens a browser only if
interactive sign-in is needed again. When multiple accounts are cached, fabutil
asks you to select an account rather than silently choosing one. The cache is
stored under `~/.fabutil/token_cache.bin` and encrypted using the operating
system's secure storage (macOS Keychain, Windows DPAPI, or Linux Secret
Service); fabutil does not fall back to storing tokens in plaintext. On Linux,
a Secret Service provider must be available. Use your Fabric administrator
account. If sign-in or the API returns an authorization error, verify the
tenant, user role, delegated permission, and admin consent.

If sign-in fails with `AADSTS500113` (no reply address registered), check the
app's **Authentication** page and confirm that `http://localhost` is listed
under **Mobile and desktop applications**. Also confirm that
`FABUTIL_CLIENT_ID` (or `--client-id`) is the **Application (client) ID** for
that same registration, and that `FABUTIL_TENANT_ID` is its tenant. A redirect
URI added under **Web**, or a URI with a different host/path, does not match
this native-client sign-in.

## How this command works

- `cli.py` defines the `capacity list` command and its options.
- `auth.py` uses MSAL to sign in the current user through a browser and obtain a
  delegated access token, silently reusing an encrypted persistent cache when
  a single account is cached.
- `powerbi.py` sends that token to `GET /v1.0/myorg/admin/capacities`.

Filtering is left to a downstream pipe tool unless a future API operation
supports server-side filtering. Fabric REST APIs are preferred for operations
they support; the Power BI Admin API is used here because it supports this
tenant-wide capacity data.

## List workspaces assigned to a capacity

Use the capacity's name or ID:

```sh
fabutil workspace list --capacity "Finance"
fabutil workspace list --capacity "a0b1c2d3-e4f5-4678-9012-3456789abcde" \
  --output json
```

Capacity names are matched exactly, without regard to case. If more than one
capacity has that name, provide its ID instead. Name lookup uses the Power BI
Admin API; an ID is sent directly to the Fabric Admin API. Workspaces are
retrieved using Fabric's server-side `capacityId` filter and all response
pages are fetched automatically. The command requires the signed-in user to be
a Fabric administrator and the app to have delegated Fabric `Tenant.Read.All`
permission with admin consent. To resolve a name, the app also needs delegated
Power BI Service `Tenant.Read.All` permission.

## List refreshable items

List refreshable semantic models across the tenant, or narrow the displayed
results by workspace and/or capacity:

```sh
fabutil refreshable list
fabutil refreshable list --workspace "Finance"
fabutil refreshable list --capacity "Premium"
fabutil refreshable list --status Failed
fabutil refreshable list \
  --workspace "Finance" \
  --capacity "Premium" \
  --status Failed \
  --time-zone local \
  --output json
```

This uses the Power BI Admin [Get Refreshables API](https://learn.microsoft.com/en-us/rest/api/power-bi/admin/get-refreshables),
which requires the signed-in user to be a Fabric administrator and delegated
Power BI Service `Tenant.Read.All`. The command requests expanded workspace and
capacity context. The API documents OData filtering but does not specify
workspace- or capacity-filter expressions, so `--workspace` and `--capacity`
filter locally after the full tenant result is paginated. `--status` also
filters locally by the latest refresh status because server-side support for
the nested `lastRefresh.status` field is not documented. Supplying multiple
filters returns items matching all of them. Names and statuses are matched
case-insensitively; workspace and capacity IDs can also be used.

The API's `RefreshableKind` currently lists only `Dataset` (Power BI semantic
models). It returns models that have refreshed at least once or have a valid
refresh schedule; models meeting neither condition are omitted. Reports are
not refreshed independently, and this endpoint does not include dataflows.
Power BI retains seven days of refresh history, up to 60 refreshes per model.

The table includes the latest refresh status, start/end time, workspace, and
capacity. Timestamps default to UTC with a `Z` suffix. `--time-zone local`
converts timestamps to the computer's local time and includes its UTC offset;
it applies to table and JSON output.

## List Fabric items

List active items across the tenant, or filter by workspace, capacity, state,
and/or item type:

```sh
fabutil item list
fabutil item list --workspace "Finance"
fabutil item list --capacity "Premium" --state active
fabutil item list \
  --workspace "aaaaaaaa-0000-1111-2222-bbbbbbbbbbbb" \
  --capacity "a0b1c2d3-e4f5-4678-9012-3456789abcde" \
  --type Lakehouse --output json
```

`--workspace` and `--capacity` each accept an ID or an exact name (matched
without regard to case). Duplicate names are ambiguous; provide an ID instead.
Capacity names are resolved using the Power BI Admin API, so name lookup also
requires Power BI Service `Tenant.Read.All`. All filters are sent to the
Fabric Admin API, and pagination is handled automatically. Item names are
reported as `displayName` in CLI JSON output.

The command uses Fabric Admin [List Items](https://learn.microsoft.com/en-us/rest/api/fabric/admin/items/list-items),
which requires the signed-in user to be a Fabric administrator and delegated
Fabric `Tenant.Read.All` permission with admin consent. The endpoint is in
Preview, returns active items only, and is not recommended for production
workloads. Accordingly, `--state` currently accepts only `active`. The API
returns up to 10,000 items per page and signals rate limiting with HTTP 429 and
a `Retry-After` header. Item types are passed to the API as-is; Fabric
validates the type. See the official reference for
[supported item types](https://learn.microsoft.com/en-us/rest/api/fabric/core/items/list-items#itemtype).

## Development

Run the tests with:

```sh
python -m unittest discover -s tests
```
