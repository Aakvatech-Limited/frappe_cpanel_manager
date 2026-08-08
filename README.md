# Frappe Cpanel Manager — User Guide

A Frappe app that lets you provision cPanel hosting accounts, manage DNS zones, and administer mailboxes from inside the Frappe desk — without giving end users direct access to cPanel or WHM.

## 1. Concepts

| Doctype | Purpose |
|---|---|
| **cPanel Server** | A WHM server you connect to (hostname, ports, WHM username/API token). All provisioning happens against a server you define here. |
| **Hosted Domain** | One domain hosted on a cPanel Server — either a full new cPanel account or a DNS-only zone. Owns a child table of DNS records. |
| **Domain DNS Record** | A single DNS record (A/AAAA/CNAME/MX/NS/SRV/TXT) belonging to a Hosted Domain. |
| **Domain Email Account** | A mailbox on a Hosted Domain's cPanel account (create, change password, change quota, suspend/unsuspend). |
| **cPanel Integration Log** | Read-only audit trail of every API call made to WHM/cPanel, with secrets (passwords, tokens) redacted. |

## 2. Setup: connect a cPanel Server

1. Go to **cPanel Server → New**.
2. Fill in `Server Name`, `Hostname`, `WHM Port` (default 2087), `cPanel Port`, `WHM Username`, and `WHM API Token`.
3. Optionally set a `Default Hosting Package` and `Default IP Address` to pre-fill new domains, and toggle `Verify SSL`.
4. Save, then click **Test Connection**. This calls the WHM `version` endpoint and records the result in `Last Connection Status` / `Last Connection Test`.
5. Untick `Enabled` on a server to take it out of use without deleting it.

The WHM API Token is stored as a Password field and is never written to logs in plain text.

## 3. Provisioning a domain

1. Go to **Hosted Domain → New**.
2. Enter `Domain Name` and pick the `Server` to host it on.
3. Choose `Provisioning Type`:
   - **New cPanel Account** — creates a full cPanel account for the domain (needs `cPanel Username`, `Contact Email`, `Hosting Package`; `Initial cPanel Password` can be set or left for cPanel to generate).
   - **DNS Only** — just manages a DNS zone for a domain hosted elsewhere; no cPanel account is created.
4. Save the document (status starts as `Draft`), then click **Provision**.
5. Status moves through `Provisioning` → `Active`, or to `Failed` with details in `Error Message` if the WHM call fails. The raw (sanitized) API response is kept in `Last API Response` for troubleshooting.
6. Provisioning is idempotent — re-running it checks whether the account already exists on the server before attempting to create it again.

## 4. Managing DNS records

DNS records live in the `DNS Records` table on a Hosted Domain.

- **Sync DNS from Server** — pulls the current zone from cPanel/WHM and replaces the local table with it. Use this first, or whenever you suspect the local copy is stale.
- Add, edit, or delete rows in the table as needed (`Record Type`, `Record Name`, `Value`, `TTL`, and `Priority`/`Weight`/`Port` where relevant, e.g. MX/SRV).
- **Apply DNS Changes** — pushes new/edited rows to the server, then automatically re-syncs so the table reflects the server's actual line numbers.
- Deleting a row and applying changes removes that specific record on the server (deletions are explicit, not inferred from a diff).
- A domain can only have one CNAME per record name (enforced on save).

## 5. Managing mailboxes

Mailboxes are managed as **Domain Email Account** records, linked to a Hosted Domain.

> Only available for domains with `Provisioning Type = New cPanel Account` and `Status = Active` — DNS Only domains have no cPanel account to hold mailboxes.

1. Go to **Domain Email Account → New**, pick the `Hosted Domain`, and enter the `Mailbox` local-part (e.g. `sales` for `sales@example.com`). `Email Address` is computed automatically.
2. Set `Quota (MB)` — use `0` for unlimited.
3. Save, then click **Create Mailbox**. Status moves `Draft` → `Creating` → `Active` (or `Failed`).
4. From the form you can also:
   - **Change Password** — sets a new mailbox password; it's never stored on the document or written to logs.
   - **Edit Quota** — updates the mailbox quota.
   - **Suspend** / **Unsuspend** — toggles mailbox login access.
5. A shortcut **Email Accounts** button on the Hosted Domain list view jumps to the mailboxes for that domain.

> Note: deleting a Domain Email Account record in Frappe does **not** delete the mailbox on the server — there is currently no "delete on server" action.

## 6. Roles & permissions

Assign one of these roles to each user, based on what they should be able to do:

| Role | Access |
|---|---|
| **cPanel Manager Administrator** | Full control everywhere, including server credentials. |
| **cPanel Manager Operator** | Provisions/manages Hosted Domains and their DNS records; read-only on cPanel Server (to pick a target); no access to email accounts. |
| **cPanel Manager Email Administrator** | Full control over Domain Email Accounts only; read-only on Hosted Domain (to link one); no DNS/server access. |
| **cPanel Manager Support** | Read-only across servers, domains, and mailboxes for troubleshooting; no access to the integration log. |
| **cPanel Manager Auditor** | Read-only across servers, domains, mailboxes, and the integration log for compliance review; never sees secret fields (tokens/passwords). |

`System Manager` retains full access as the standard Frappe break-glass admin role. Secret fields (WHM API Token, initial passwords) are additionally restricted at the field level so they don't render for roles that don't need them.

## 7. Auditing

Every WHM/cPanel API call is recorded in **cPanel Integration Log**, showing the target server, timing, HTTP status, and success/failure, with a link back to the Hosted Domain or Domain Email Account that triggered it. Request and response payloads are sanitized before storage — passwords and tokens are redacted even if a provider response happens to echo them back.

## 8. Troubleshooting

- **Test Connection fails** — check hostname/port/WHM username/API token on the cPanel Server, and that `Enabled` is checked.
- **Provision / DNS / mailbox action fails** — check the `Error Message` field on the record, then open the matching **cPanel Integration Log** entry for the full sanitized request/response.
- **Email actions greyed out or erroring** — confirm the parent Hosted Domain is `Provisioning Type = New cPanel Account` and `Status = Active`.

---

### Frappe Cpanel Manager

The app is designed to provide a controlled interface for provisioning domains, managing DNS records, creating email accounts and administering mailbox quotas without requiring users to log directly into cPanel or WHM

### Installation

You can install this app using the [bench](https://github.com/frappe/bench) CLI:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO --branch version-16
bench install-app frappe_cpanel_manager
```

### Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/frappe_cpanel_manager
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade
### CI

This app can use GitHub Actions for CI. The following workflows are configured:

- CI: Installs this app and runs unit tests on every push to `develop` branch.
- Linters: Runs [Frappe Semgrep Rules](https://github.com/frappe/semgrep-rules) and [pip-audit](https://pypi.org/project/pip-audit/) on every pull request.


### License

mit

# frappe_cpanel_manager
