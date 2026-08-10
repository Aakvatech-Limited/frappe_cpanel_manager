# Frappe cPanel Manager

Frappe cPanel Manager is a Frappe Framework application for managing cPanel and WHM hosting resources directly from Frappe or ERPNext.

The app is designed to provide a controlled interface for provisioning domains, managing DNS records, creating email accounts and administering mailbox quotas without requiring users to log directly into cPanel or WHM.

> **Project status:** Initial development
> **Current scope:** Domain, DNS and email account provisioning

---

## Business Summary

Organizations that manage multiple websites, customer domains or hosted email accounts often perform repetitive work manually through cPanel and WHM.

Typical tasks include:

* Creating hosting accounts
* Adding customer domains
* Creating DNS zones
* Adding A, CNAME, TXT and MX records
* Creating email accounts
* Resetting email passwords
* Changing mailbox quotas
* Tracking which resources belong to each customer

Frappe cPanel Manager centralizes these operations inside Frappe and provides a structured, auditable and permission-controlled provisioning workflow.

---

## Business Problems This App Solves

| Business problem                                | How the app helps                                        |
| ----------------------------------------------- | -------------------------------------------------------- |
| Hosting resources are created manually          | Provides guided provisioning actions from Frappe         |
| Staff must log in directly to WHM or cPanel     | Uses secure server-side API integration                  |
| DNS changes are difficult to track              | Stores requested records, statuses and API responses     |
| Email accounts are created inconsistently       | Standardizes mailbox creation and quota allocation       |
| Password changes are handled informally         | Provides controlled password reset actions               |
| Customer domains are tracked in spreadsheets    | Links hosted domains to Frappe customers                 |
| Provisioning failures are difficult to diagnose | Stores sanitized errors and integration logs             |
| Excessive WHM access is given to support users  | Uses Frappe roles and permissions to restrict operations |

---

## Who This App Is For

Frappe cPanel Manager is suitable for:

* Web-hosting providers
* ERPNext and Frappe implementation companies
* Managed service providers
* IT support companies
* Domain and email administrators
* Organizations managing multiple customer websites
* Internal IT departments using cPanel or WHM
* Companies that want hosting provisioning linked to customer records

---

## Who This App Is Not For

The initial version is not intended to replace:

* WHM billing systems
* Complete hosting automation platforms
* Domain registrar APIs
* DNS providers outside cPanel or WHM
* Email clients such as Outlook or Thunderbird
* Full server monitoring platforms
* cPanel server administration itself

The application acts as a controlled provisioning and management layer on top of supported cPanel and WHM APIs.

---

## Business Benefits

| Benefit                       | Description                                                                     |
| ----------------------------- | ------------------------------------------------------------------------------- |
| Faster provisioning           | Common hosting actions can be completed from one Frappe document                |
| Improved accountability       | Every domain, email account and DNS change can be linked to a user and customer |
| Reduced administrative access | Support users do not need unrestricted WHM credentials                          |
| Standardized operations       | Quotas, naming rules and provisioning procedures can be enforced                |
| Better customer visibility    | Hosted services can be viewed against the relevant customer                     |
| Improved error handling       | Failed API operations can be logged and retried                                 |
| Future billing readiness      | Provisioned resources can later be connected to subscriptions and invoices      |

---

## Before and After

| Before                                         | After                                              |
| ---------------------------------------------- | -------------------------------------------------- |
| Staff log directly into WHM                    | Staff use approved Frappe actions                  |
| Domain information is stored separately        | Domains are linked to customers and servers        |
| DNS changes are recorded manually              | DNS records are stored in structured child tables  |
| Email quotas are applied inconsistently        | Default and maximum quota policies can be enforced |
| API credentials may be shared                  | Credentials remain encrypted on the Frappe server  |
| Provisioning history is incomplete             | Actions and outcomes are auditable                 |
| Failed operations require manual investigation | Sanitized API errors are recorded centrally        |

---

## Initial Scope

The first release focuses on four primary areas.

### 1. Domain Management

The app will support:

* Creating a complete cPanel hosting account
* Adding a primary domain during account creation
* Creating DNS-only zones
* Adding addon domains to existing cPanel accounts
* Linking domains to customers
* Assigning domains to cPanel servers
* Tracking domain provisioning status
* Preventing duplicate domain provisioning
* Recording remote account and zone identifiers

### 2. DNS Management

The app will support common DNS records, including:

* A
* AAAA
* CNAME
* TXT
* MX
* SRV
* CAA

Users will be able to:

* List current DNS records
* Add DNS records
* Modify supported DNS records
* Delete DNS records
* Set TTL values
* Set MX priorities
* track the status of each change
* View sanitized API errors

### 3. Email Account Management

The app will support:

* Creating email accounts
* Setting an initial password
* Generating secure passwords
* Resetting mailbox passwords
* Viewing configured mailbox quotas
* Changing mailbox quotas
* Linking email accounts to domains
* Disabling or deleting accounts in later phases

### 4. Mailbox Quota Management

The app will support:

* Setting quotas during mailbox creation
* Changing quotas after creation
* Applying server or package defaults
* Restricting quotas to approved limits
* Supporting unlimited quota where allowed
* Recording quota changes for audit purposes

---

## Typical Use Cases

### Customer Hosting Provisioning

A hosting administrator receives a request to create a website and email accounts for a new customer.

The administrator:

1. Creates or selects the customer in ERPNext.
2. Creates a Hosted Domain document.
3. Selects the cPanel server.
4. Chooses a hosting package.
5. Provisions the cPanel account.
6. Adds the required DNS records.
7. Creates the customer email accounts.
8. Assigns mailbox quotas.
9. Reviews the provisioning results.

### DNS Record Management

A customer needs to verify a cloud service using a TXT record.

The administrator:

1. Opens the Hosted Domain.
2. Adds a TXT record.
3. Enters the verification value.
4. Submits the DNS change.
5. Reviews the result returned by cPanel.
6. Confirms that the record is active.

### New Employee Email Account

A customer requests a mailbox for a new employee.

The administrator:

1. Opens the customer's Hosted Domain.
2. Adds an email account.
3. Generates or enters a password.
4. Assigns a mailbox quota.
5. Creates the mailbox through cPanel UAPI.
6. Shares the credentials through an approved secure channel.

---

## Example Business Workflow

```text
Customer
   |
   v
Hosted Domain
   |
   +--> cPanel Account
   |
   +--> DNS Zone
   |       |
   |       +--> A Records
   |       +--> CNAME Records
   |       +--> TXT Records
   |       +--> MX Records
   |
   +--> Email Accounts
           |
           +--> Password Management
           +--> Mailbox Quotas
```

---

## Application Mode

Frappe cPanel Manager is designed as a standalone Frappe application.

ERPNext may be installed optionally to provide additional integration with:

* Customer
* Contact
* Address
* Sales Invoice
* Subscription
* Item
* Project
* Issue
* Service Level Agreement

The initial cPanel integration should not require ERPNext unless customer or billing integration is enabled.

---

## Proposed Modules

The initial app structure should include the following modules:

```text
Frappe cPanel Manager
├── cPanel Configuration
├── Domain Management
├── DNS Management
├── Email Management
├── Integration Logs
└── Settings
```

---

## Proposed DocTypes

### cPanel Server

Stores the connection and authentication configuration for a WHM or cPanel server.

Suggested fields:

| Field                   | Type     | Description                          |
| ----------------------- | -------- | ------------------------------------ |
| Server Name             | Data     | Friendly server name                 |
| Hostname                | Data     | cPanel or WHM hostname               |
| WHM Port                | Int      | Default `2087`                       |
| cPanel Port             | Int      | Default `2083`                       |
| WHM Username            | Data     | WHM API username                     |
| WHM API Token           | Password | Encrypted WHM token                  |
| Verify SSL              | Check    | Enforce SSL certificate verification |
| Default IP Address      | Data     | Default account or zone IP           |
| Default Hosting Package | Data     | Default WHM package                  |
| Enabled                 | Check    | Allow API operations                 |
| Last Connection Test    | Datetime | Last successful test                 |
| Last Connection Status  | Select   | Success or failed                    |

### Hosted Domain

Represents a domain managed through the application.

Suggested fields:

| Field                  | Type     | Description                            |
| ---------------------- | -------- | -------------------------------------- |
| Domain Name            | Data     | Fully qualified domain name            |
| Customer               | Link     | Optional ERPNext customer              |
| cPanel Server          | Link     | Target server                          |
| Provisioning Type      | Select   | Account, addon domain or DNS only      |
| cPanel Username        | Data     | Associated cPanel account              |
| Hosting Package        | Data     | WHM package                            |
| Document Root          | Data     | Addon-domain document root             |
| IP Address             | Data     | Domain or DNS IP                       |
| Status                 | Select   | Provisioning status                    |
| Remote Account Created | Check    | Indicates successful account creation  |
| DNS Zone Created       | Check    | Indicates successful DNS-zone creation |
| Provisioned On         | Datetime | Successful provisioning time           |
| Last API Response      | Code     | Sanitized response data                |

Suggested statuses:

```text
Draft
Pending
Provisioning
Active
Failed
Suspended
Terminated
```

### Domain DNS Record

Child table containing DNS records belonging to a hosted domain.

Suggested fields:

| Field            | Type       | Description                         |
| ---------------- | ---------- | ----------------------------------- |
| Record Type      | Select     | A, AAAA, CNAME, TXT, MX, SRV or CAA |
| Record Name      | Data       | Record hostname                     |
| Record Value     | Small Text | Record destination or value         |
| TTL              | Int        | Time to live                        |
| Priority         | Int        | MX or SRV priority                  |
| Remote Record ID | Data       | Remote identifier, when available   |
| Status           | Select     | Pending, active, failed or deleted  |
| Error Message    | Small Text | Sanitized API error                 |

### Domain Email Account

Represents a mailbox belonging to a hosted domain.

Suggested fields:

| Field             | Type     | Description                                   |
| ----------------- | -------- | --------------------------------------------- |
| Email Username    | Data     | Local mailbox name                            |
| Domain            | Link     | Hosted domain                                 |
| Email Address     | Data     | Complete email address                        |
| Password          | Password | Temporary or managed password                 |
| Quota MB          | Int      | Mailbox quota                                 |
| Unlimited Quota   | Check    | Use unlimited quota where supported           |
| Status            | Select   | Pending, active, failed, suspended or deleted |
| Remote Created    | Check    | Indicates successful creation                 |
| Last API Response | Code     | Sanitized response                            |

### cPanel Integration Log

Records API operations without exposing passwords or tokens.

Suggested fields:

| Field              | Type         | Description              |
| ------------------ | ------------ | ------------------------ |
| Server             | Link         | cPanel server            |
| Reference DocType  | Link         | Source DocType           |
| Reference Name     | Dynamic Link | Source document          |
| Operation          | Data         | API operation            |
| API Layer          | Select       | WHM API 1 or cPanel UAPI |
| Request Time       | Datetime     | Request timestamp        |
| Completion Time    | Datetime     | Completion timestamp     |
| Status             | Select       | Success or failed        |
| HTTP Status        | Int          | HTTP response status     |
| Sanitized Request  | Code         | Request without secrets  |
| Sanitized Response | Code         | Response without secrets |
| Error Message      | Small Text   | User-readable error      |

---

## Proposed Roles

| Role                  | Responsibilities                             |
| --------------------- | -------------------------------------------- |
| cPanel Administrator  | Configure servers and perform all operations |
| cPanel Domain Manager | Provision and manage domains                 |
| cPanel DNS Manager    | Add, update and remove DNS records           |
| cPanel Email Manager  | Create mailboxes and manage quotas           |
| cPanel Viewer         | View configuration and provisioning status   |
| System Manager        | Full administrative oversight                |

Sensitive operations such as viewing credentials, changing passwords or deleting accounts must require explicit permissions.

---

## API Architecture

The application should use two cPanel API layers.

### WHM API 1

Use WHM API 1 for server-level operations such as:

* Creating cPanel accounts
* Creating DNS zones
* Managing accounts
* Accessing resources across multiple cPanel users
* Suspending or terminating accounts in future phases

### cPanel UAPI

Use cPanel UAPI for account-level operations such as:

* Adding addon domains
* Managing DNS records
* Creating email accounts
* Changing email passwords
* Changing mailbox quotas
* Listing email accounts

---

## Authentication

The app should support API-token authentication.

### WHM Authentication

```http
Authorization: whm USERNAME:API_TOKEN
```

Default secure port:

```text
2087
```

### cPanel Authentication

```http
Authorization: cpanel USERNAME:API_TOKEN
```

Default secure port:

```text
2083
```

API calls must only be performed from server-side Python code.

Tokens must never be sent to the browser.

---

## Security

Security is a core requirement because the application controls hosting, DNS and email resources.

The implementation should enforce the following controls:

* Store tokens in Frappe Password fields
* Retrieve secrets only on the server
* Require HTTPS
* Verify SSL certificates by default
* Never expose tokens through client scripts
* Never include passwords in API logs
* Never include authentication headers in Error Logs
* Sanitize request and response data
* Restrict operations by Frappe role
* Require explicit permission for destructive operations
* Validate domains and email usernames
* Prevent duplicate provisioning requests
* Apply API timeouts
* Record user, time and operation details
* Use background jobs for long-running operations
* Use idempotency checks before creating remote resources
* Use restricted API tokens wherever possible

Mailbox passwords should not be permanently retained unless there is a defined operational requirement.

Where passwords are temporarily stored, they should be cleared after successful provisioning or restricted to authorized roles.

---

## Password Handling

The application should support two password methods:

1. User-entered password
2. System-generated secure password

Recommended password rules:

* Minimum length of 14 characters
* Uppercase letters
* Lowercase letters
* Numbers
* Special characters
* No domain name
* No mailbox username
* No common passwords

Passwords must not appear in:

* Frappe timelines
* Integration logs
* Error logs
* Browser console output
* Background-job logs
* API response fields
* Notifications

---

## Domain Validation

Before provisioning, the app should validate:

* Domain is syntactically valid
* Domain is normalized to lowercase
* Domain does not contain a protocol
* Domain does not contain a path
* Domain is not already registered in Frappe
* Domain is not already provisioned on the selected server
* cPanel username follows server naming rules
* IP address is valid where required
* Hosting package exists where applicable

Example accepted domain:

```text
example.com
```

Examples that should be rejected or normalized:

```text
https://example.com
example.com/path
EXAMPLE.COM
```

---

## DNS Record Validation

The application should validate each DNS record type separately.

### A Record

The record value must be a valid IPv4 address.

```text
app.example.com -> 192.0.2.10
```

### AAAA Record

The record value must be a valid IPv6 address.

### CNAME Record

The value must be a valid hostname.

```text
www.example.com -> example.com
```

### TXT Record

The app must preserve record content and correctly handle quotation and escaping requirements.

Examples include:

```text
v=spf1 include:_spf.example.com ~all
```

```text
google-site-verification=verification-value
```

### MX Record

An MX record must include:

* Mail server hostname
* Priority
* TTL

Example:

```text
example.com -> mail.example.com
Priority: 10
```

---

## Quota Management

Mailbox quotas should be stored in megabytes.

The application should support:

* Default mailbox quota
* Minimum quota
* Maximum quota
* Package-based quota
* Manual quota override
* Unlimited quota where permitted

A dedicated Unlimited Quota checkbox should be used instead of assuming that a numeric value such as zero means unlimited across all cPanel versions.

---

## Installation

### Prerequisites

* Frappe Framework version 15 or later
* Python version supported by the installed Frappe version
* Redis
* MariaDB or PostgreSQL as supported by the Frappe deployment
* HTTPS access from the Frappe server to cPanel or WHM
* Valid WHM or cPanel API token

### Get the App

```bash
cd /path/to/frappe-bench
bench get-app https://github.com/aakvatech/frappe-cpanel-manager.git
```

### Install the App

```bash
bench --site your-site.example.com install-app frappe_cpanel_manager
```

### Run Migrations

```bash
bench --site your-site.example.com migrate
```

### Restart Services

```bash
bench restart
```

> Replace the repository URL with the final repository location before publishing.

---

## Initial Configuration

After installation:

1. Log in as System Manager.
2. Open **cPanel Server**.
3. Create a server record.
4. Enter the WHM or cPanel hostname.
5. Enter the secure ports.
6. Enter the API username.
7. Enter the API token.
8. Enable SSL verification.
9. Save the document.
10. Run **Test Connection**.
11. Assign the appropriate cPanel roles to users.

---

## Proposed Connection Test

The cPanel Server DocType should provide a **Test Connection** button.

The test should verify:

* Hostname can be reached
* SSL certificate is valid
* Authentication succeeds
* WHM or cPanel API responds
* API version is supported
* User has the required privileges

The test must not create or modify any remote resource.

---

## Proposed User Interface

### cPanel Server

Buttons:

* Test Connection
* Fetch Server Information
* View Integration Logs

### Hosted Domain

Buttons:

* Provision Domain
* Create DNS Zone
* Synchronize DNS Records
* Add DNS Record
* View Remote Account
* Retry Failed Provisioning
* Suspend Account
* Terminate Account

Destructive buttons should only be introduced after confirmation safeguards are implemented.

### Domain Email Account

Buttons:

* Create Mailbox
* Generate Password
* Change Password
* Change Quota
* Synchronize Mailbox
* Suspend Mailbox
* Delete Mailbox

---

## Background Jobs

Long-running provisioning operations should use Frappe background jobs.

Recommended queued operations:

* Create cPanel account
* Create multiple DNS records
* Create multiple mailboxes
* Synchronize domain information
* Synchronize DNS zones
* Fetch mailbox usage
* Retry failed provisioning actions

Suggested queues:

| Operation                 | Queue   |
| ------------------------- | ------- |
| Connection test           | Short   |
| Single DNS change         | Short   |
| Mailbox creation          | Short   |
| Full account provisioning | Default |
| Bulk synchronization      | Long    |

---

## Idempotency

Every creation operation should check whether the remote resource already exists.

Examples:

* Check whether a cPanel account already exists before creating it
* Check whether a DNS zone already exists
* Check whether a DNS record with the same name, type and value exists
* Check whether an email address already exists
* Avoid creating duplicate records when a background job is retried

Each provisioning document should have a unique operation identifier where appropriate.

---

## Error Handling

The app should convert cPanel API errors into clear Frappe messages.

Example:

```text
Unable to create accounts@example.com because the mailbox already exists.
```

Instead of:

```text
API request returned result 0.
```

Technical details may be stored in the Integration Log, provided secrets are removed.

Errors should be categorized as:

* Authentication error
* Permission error
* Validation error
* Duplicate resource
* Network error
* SSL error
* cPanel API error
* Timeout
* Unknown remote response

---

## Logging

The integration log should capture:

* Frappe user
* Server
* Domain
* Operation
* Request time
* Completion time
* Outcome
* HTTP status
* Sanitized request
* Sanitized response
* Retry count

The following must never be logged:

* API tokens
* Authentication headers
* Mailbox passwords
* cPanel account passwords
* Full secret values

---

## Permissions

Suggested permission model:

| DocType              | Administrator | Domain Manager |  DNS Manager | Email Manager | Viewer |
| -------------------- | ------------: | -------------: | -----------: | ------------: | -----: |
| cPanel Server        |          Full |           Read |         Read |          Read |   Read |
| Hosted Domain        |          Full |   Create/Write |         Read |          Read |   Read |
| Domain DNS Record    |          Full |           Read | Create/Write |          Read |   Read |
| Domain Email Account |          Full |           Read |         Read |  Create/Write |   Read |
| Integration Log      |          Full |           Read |         Read |          Read |   Read |

Password fields and server tokens must have additional field-level restrictions where applicable.

---

## Reports

The initial version may include the following reports:

### Hosted Domains

Columns:

* Domain
* Customer
* Server
* Provisioning Type
* cPanel Username
* Status
* Provisioned On

### Email Accounts

Columns:

* Email Address
* Domain
* Customer
* Server
* Quota
* Status
* Created On

### DNS Records

Columns:

* Domain
* Record Type
* Name
* Value
* TTL
* Status

### Failed cPanel Operations

Columns:

* Date
* Server
* Operation
* Reference Document
* Error Category
* Error Message
* Retry Count

---

## Dashboard Indicators

Suggested workspace indicators:

* Active hosted domains
* Pending domain provisioning
* Failed provisioning operations
* Active email accounts
* Email accounts approaching quota
* DNS changes pending synchronization
* cPanel servers with failed connection tests

---

## Compatibility

Planned compatibility:

| Component        | Supported version                |
| ---------------- | -------------------------------- |
| Frappe Framework | Version 15                       |
| ERPNext          | Version 15, optional             |
| cPanel           | To confirm during development    |
| WHM API          | WHM API 1                        |
| cPanel API       | UAPI                             |
| Python           | As required by Frappe version 15 |

Actual cPanel version compatibility must be verified against the target development and production servers.

---

## Developer Setup

```bash
cd /path/to/frappe-bench
bench get-app /path/to/frappe-cpanel-manager
bench --site development.localhost install-app frappe_cpanel_manager
bench --site development.localhost migrate
bench start
```

Enable developer mode:

```bash
bench set-config -g developer_mode 1
```

Clear cache after DocType or workspace changes:

```bash
bench --site development.localhost clear-cache
```

Export fixtures where applicable:

```bash
bench --site development.localhost export-fixtures
```

---

## Proposed Project Structure

```text
frappe_cpanel_manager/
├── frappe_cpanel_manager/
│   ├── __init__.py
│   ├── hooks.py
│   ├── modules.txt
│   ├── patches.txt
│   ├── api/
│   │   ├── domain.py
│   │   ├── dns.py
│   │   └── email.py
│   ├── integrations/
│   │   └── cpanel/
│   │       ├── client.py
│   │       ├── authentication.py
│   │       ├── domain.py
│   │       ├── dns.py
│   │       ├── email.py
│   │       ├── exceptions.py
│   │       └── utils.py
│   ├── cpanel_configuration/
│   │   └── doctype/
│   │       └── cpanel_server/
│   ├── domain_management/
│   │   └── doctype/
│   │       ├── hosted_domain/
│   │       └── domain_dns_record/
│   ├── email_management/
│   │   └── doctype/
│   │       └── domain_email_account/
│   ├── integration_logs/
│   │   └── doctype/
│   │       └── cpanel_integration_log/
│   └── public/
│       ├── js/
│       └── css/
├── pyproject.toml
├── license.txt
└── README.md
```

---

## Proposed Python Service Layer

The integration should use a centralized client class.

```python
from frappe_cpanel_manager.integrations.cpanel.client import CPanelClient
```

Example usage:

```python
client = CPanelClient(server="Hosting Server 01")

result = client.call_whm(
    function_name="createacct",
    params={
        "domain": "example.com",
        "username": "example",
        "password": generated_password,
        "pkgname": "standard",
    },
)
```

Account-level operations should use UAPI:

```python
result = client.call_uapi(
    cpanel_username="example",
    module="Email",
    function_name="add_pop",
    params={
        "email": "accounts",
        "domain": "example.com",
        "password": generated_password,
        "quota": 2048,
    },
)
```

All remote operations should pass through the service layer rather than calling the API directly from DocType controllers.

---

## Testing Strategy

The app should include:

### Unit Tests

Test:

* Domain validation
* Email validation
* IP address validation
* DNS-record validation
* Password sanitization
* API-response parsing
* Error classification
* Duplicate detection
* Quota rules

### Integration Tests

Test against a non-production cPanel server:

* Connection test
* Account creation
* DNS-zone creation
* A-record creation
* CNAME creation
* TXT-record creation
* MX-record creation
* Mailbox creation
* Password reset
* Quota update

### Security Tests

Verify:

* Tokens are not exposed in browser responses
* Passwords are not logged
* Unauthorized roles cannot execute API operations
* SSL verification is enabled
* Destructive operations require permission
* Error logs are sanitized

---

## Implementation Phases

### Phase 1 — Connection and Configuration

* cPanel Server DocType
* WHM API-token authentication
* cPanel UAPI authentication
* Connection test
* SSL verification
* Sanitized integration logging

### Phase 2 — Domain Provisioning

* Create cPanel account
* Create DNS-only zone
* Add addon domain
* List hosted domains
* Prevent duplicate provisioning
* Track provisioning status

### Phase 3 — DNS Management

* List DNS records
* Add A records
* Add AAAA records
* Add CNAME records
* Add TXT records
* Add MX records
* Update records
* Delete records
* Synchronize remote state

### Phase 4 — Email Management

* Create mailbox
* Generate password
* Change password
* Set quota
* Change quota
* List mailboxes
* Synchronize mailbox status

### Phase 5 — Operational Enhancements

* Background provisioning
* Retry framework
* Notifications
* Reports
* Dashboard
* Mailbox-usage monitoring
* Suspension and deletion controls

### Phase 6 — Commercial Integration

Potential future integration with:

* ERPNext Customer
* ERPNext Subscription
* Sales Invoice
* Hosting package Items
* Automated renewals
* Usage-based billing
* Customer self-service portal

---

## Future Roadmap

Potential future capabilities include:

* SSL certificate provisioning
* AutoSSL management
* Email forwarders
* Email autoresponders
* Mailing lists
* FTP account management
* Database provisioning
* Database-user management
* Subdomain management
* Redirect management
* Cron-job management
* Hosting-package management
* Account suspension
* Account termination
* Backup management
* Disk-usage monitoring
* Bandwidth monitoring
* Mailbox-usage alerts
* DNS templates
* Bulk domain migration
* Domain registrar integration
* Customer portal
* ERPNext billing integration
* Subscription renewal automation
* Service-expiry notifications

---

## Risks and Considerations

| Risk                                            | Mitigation                                           |
| ----------------------------------------------- | ---------------------------------------------------- |
| WHM token has excessive privileges              | Use restricted API tokens                            |
| Incorrect DNS records can interrupt services    | Add validation and confirmation controls             |
| Passwords may be exposed through logs           | Sanitize all requests and responses                  |
| Duplicate API requests may create conflicts     | Implement idempotency checks                         |
| cPanel versions may expose different functions  | Maintain compatibility checks                        |
| Network failures may leave partial provisioning | Track each step separately and support retries       |
| Mailbox quotas may use different conventions    | Confirm behaviour against the target server          |
| SSL verification may be disabled during testing | Default to enabled and clearly flag insecure servers |
| Destructive actions may remove customer data    | Require elevated permission and confirmation         |

---

## What Must Be Ready Before Implementation

Before development begins, confirm:

* Target cPanel and WHM versions
* Development or sandbox cPanel server
* API-token privilege requirements
* Hosting-package names
* cPanel username-generation rules
* Default DNS TTL
* Default mailbox quota
* Maximum mailbox quota
* Whether unlimited quota is permitted
* Whether Frappe will manage one or multiple servers
* Whether ERPNext Customer integration is required
* Whether passwords should be retained after provisioning
* Required audit-retention period
* Account suspension and deletion policies

---

## Decision Guide

Use Frappe cPanel Manager where:

* Several domains are managed regularly
* Hosting tasks need formal authorization
* Customer services need to be tracked centrally
* Direct WHM access should be restricted
* Domain and email provisioning should be auditable
* Hosting automation will later connect to ERPNext billing

Continue using cPanel directly where:

* Only one or two domains are managed
* No customer-service tracking is required
* No automation or audit trail is needed
* Administrators already have appropriate direct access

---

## Expected Business Outcomes

After implementation, the organization should be able to:

* Provision hosting resources from Frappe
* Reduce direct WHM access
* Standardize domain and email creation
* Link hosted services to customers
* Record provisioning failures and retries
* Apply consistent mailbox quotas
* Maintain a searchable inventory of hosted domains
* Prepare for automated hosting billing and renewals

Actual time savings and operational improvements should be measured after deployment.

---

## Frequently Asked Questions

### Does the app replace WHM?

No. It uses WHM and cPanel APIs to perform approved operations through Frappe.

### Is ERPNext required?

No. The planned core integration is a standalone Frappe app. ERPNext is optional for customer, billing and subscription integration.

### Can it manage multiple cPanel servers?

The proposed design supports multiple cPanel Server records.

### Can users see the WHM API token?

No. Tokens should be stored in encrypted Password fields and accessed only through server-side code.

### Can it create email accounts?

Yes. Email-account creation is part of the initial scope.

### Can it manage mailbox quotas?

Yes. Quotas can be set during mailbox creation and changed later.

### Can it manage DNS TXT records?

Yes. TXT records, including SPF and verification records, are part of the initial scope.

### Can it create complete cPanel accounts?

Yes. Complete account creation should use WHM API 1.

### Can it work with external DNS providers?

Not in the initial scope. The first version targets DNS zones managed by cPanel or WHM.

### Will it automatically bill customers?

Not in the initial scope. ERPNext billing and subscription integration may be added later.

---

## To Confirm Before Publishing

The following items must be confirmed after the repository and first implementation are available:

* Final license
* Supported Frappe versions
* Supported cPanel versions
* Supported WHM versions
* Final repository URL
* Maintainer contact
* Production installation procedure
* Required API-token privileges
* Exact DNS API functions used
* Unlimited-quota behaviour
* Screenshot examples
* Demonstration video
* ERPNext dependency mode
* Upgrade and migration process

---

## Contributing

Contributions should follow the standard Frappe development workflow.

Before submitting changes:

1. Create a feature branch.
2. Add or update tests.
3. Run the relevant test suite.
4. Confirm that secrets are not present in logs or fixtures.
5. Update the README where behaviour changes.
6. Submit a pull request with a clear description.

---

## Versioning

The project should use semantic versioning:

```text
MAJOR.MINOR.PATCH
```

Example:

```text
1.0.0
```

* **MAJOR** for incompatible changes
* **MINOR** for backward-compatible features
* **PATCH** for backward-compatible fixes

---

## License

License: **To confirm**

Recommended options:

* GNU General Public License v3.0
* MIT License
* GNU Affero General Public License v3.0

The selected license should be added to `license.txt` and declared in `pyproject.toml`.

---

## Maintainers

**Aakvatech Limited**

Frappe and ERPNext implementation, customization and integration services.

Maintainer details and support channels: **To confirm**

---

## Disclaimer

This project is not affiliated with, endorsed by or maintained by cPanel, L.L.C.

cPanel, WHM and related names are trademarks of their respective owners.

Use this application only with servers and accounts that you are authorized to administer.
