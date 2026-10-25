# Contributing to fabutil

Thanks for your interest in contributing. Issues and pull requests for bug
fixes, documentation improvements, and new Fabric or Power BI CLI capabilities
are welcome.

## Development setup

**fabutil** requires Python 3.10 or later. Clone the repository, create a virtual
environment, install the project in editable mode, and run the test suite:

```sh
git clone https://github.com/iwoodu/fabric-util-cli.git
cd fabric-util-cli
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
python -m unittest discover -s tests
```

On Windows PowerShell, activate the environment with:

```powershell
py -3.10 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
python -m unittest discover -s tests
```

## Configure interactive user sign-in

**fabutil** authenticates the current user with Microsoft Entra ID using MSAL's
public-client interactive sign-in flow. API calls use delegated permissions
and the signed-in user's access. Service-principal authentication and client
secrets are not used.

Register a public-client app for local development:

1. In Microsoft Entra ID, create an app registration. For a single-organization
   app, choose **Accounts in this organizational directory only**. Record the
   **Application (client) ID** and **Directory (tenant) ID**.

2. Under **Authentication**, select **Add a platform** >
   **Mobile and desktop applications** and register this custom redirect URI:

   ```text
   http://localhost
   ```

   Use the mobile/desktop platform, not the **Web** platform. Do not add a
   port; MSAL uses a temporary localhost port during interactive sign-in.

3. Under **API permissions**, add these delegated permissions:
   - **Power BI Service** > `Dataset.Read.All`, `SemanticModel.Read.All`, `Tenant.Read.All`, `Workspace.Read.All`

   Have an administrator grant consent for the permissions.

4. Provide the registration's IDs when running a command. For example:

   ```sh
   export FABUTIL_TENANT_ID="<your-tenant-id>"
   export FABUTIL_CLIENT_ID="<your-app-client-id>"
   fabutil capacity list
   ```

   Alternatively, pass `--tenant-id` and `--client-id` to a command.


The first run opens a browser for sign-in. The token cache is stored at
`~/.fabutil/token_cache.bin` and encrypted using operating-system secure
storage. On macOS this uses Keychain, on Windows DPAPI, and on Linux a Secret
Service provider must be available. When one account is cached, `fabutil` tries
silent token acquisition before prompting again. If multiple accounts are
cached, it asks the user to select an account.

Permission consent does not grant the user a Fabric or Power BI role. The
signed-in user must also have the role required by the API operation. See the
[command reference](docs/commands.md) for the requirements of each command.

If sign-in fails with `AADSTS500113` (no reply address registered), verify
that `http://localhost` is registered under **Mobile and desktop applications**
and that the configured client ID belongs to that app registration. A redirect
URI registered under **Web**, or with a different host or path, will not match
the native-client sign-in.

## Implementation notes

- Prefer Fabric REST APIs for operations they support. Power BI Admin APIs are
  used where the required tenant-wide operation is not available through
  Fabric.
- Use delegated user authentication. Do not add service-principal
  authentication or client secrets without first discussing the security and
  consent implications.
- Follow continuation tokens when an API supports pagination, and surface
  invalid or repeated continuation tokens as errors.
- Keep API behavior covered by tests. Mock network and authentication
  boundaries in unit tests; do not require tenant credentials to run the test
  suite.
- Update the relevant command documentation when CLI behavior or options
  change.
