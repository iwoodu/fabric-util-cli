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
   **Delegated permissions** > `Tenant.Read.All`. Also add **Power BI Service**
   > **Delegated permissions** > `Tenant.Read.All` to support capacity listing
   and capacity-name lookup. Have an administrator grant consent for both.
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

## Development

Run the tests with:

```sh
python -m unittest discover -s tests
```
