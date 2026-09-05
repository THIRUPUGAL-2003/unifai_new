# UnifAI Governance & Plugins Master Deep-Dive Guide
## UnifAI Governance, Security & Plugins Amaippin Muzhumaiyana Manual

**Pillars Covered:** Plugins & Governance (Virtual Keys, Users, Teams, Business Units, Customers, SCIM, RBAC, Access Profiles, Audit Logs)  
**Target Audience:** Security Architects, CTOs, CFOs, Compliance Officers, Developers & System Admins  
**Language:** Bilingual (Thanglish - Tamil in English letters + Clean English)  
**Generated At:** 2026-09-05  

---

## Table of Contents
1. [Governance & Plugins Architecture Map](#1-governance--plugins-architecture-map)
2. [Detailed Feature Dissection (10 Core Features)](#2-detailed-feature-dissection)
   - [Plugins (Plugins (Gateway Extensions & Lifecycle Hooks)) (/workspace/plugins)](#plugins)
   - [Virtual Keys (Virtual Keys (Proxy API Keys & Granular Quotas)) (/workspace/governance/virtual-keys)](#virtual_keys)
   - [Users (Users (Platform User Directory & Identity Management)) (/workspace/governance/users)](#users)
   - [Teams (Teams (Departmental Squads & Shared Resource Pools)) (/workspace/governance/teams)](#teams)
   - [Business Units (Business Units (Enterprise Divisions & P&L Centers)) (/workspace/governance/business-units)](#business_units)
   - [Customers (Customers (B2B Client Tenants & External Accounts)) (/workspace/governance/customers)](#customers)
   - [User Provisioning (SCIM) (User Provisioning / SCIM (Automated Enterprise SSO & Lifecycle Sync)) (/workspace/scim)](#scim)
   - [Roles & Permissions (RBAC) (Roles & Permissions (RBAC Security & Granular Access Matrix)) (/workspace/governance/rbac)](#rbac)
   - [Access Profiles (Access Profiles (Reusable Policy Bundles & Guardrail Packs)) (/workspace/governance/access-profiles)](#access_profiles)
   - [Audit Logs (Audit Logs (Tamper-Proof Compliance & Activity Trail)) (/workspace/audit-logs)](#audit_logs)
3. [Cross-Feature Interconnections & Data Flow](#3-cross-feature-interconnections--data-flow)
4. [Tech vs Non-Tech Comparative Matrix](#4-tech-vs-non-tech-comparative-matrix)

---

# 1. Governance & Plugins Architecture Map
### Enterprise Identity, Security Boundaries & Request Lifecycle Flow

```
             [ ENTERPRISE IDENTITY (Okta / Entra ID / IdP) ]
                                   │
                    (SCIM v2 Sync) ▼
       ┌───────────────────────────────────────────────────────────┐
       │                USER PROVISIONING (SCIM)                   │
       │  • Auto-creates Users, Maps directory groups to Teams     │
       └───────────────────────────┬───────────────────────────────┘
                                   │
                                   ▼
       ┌───────────────────────────────────────────────────────────┐
       │             ENTERPRISE TENANT HIERARCHY                   │
       │                                                           │
       │   [ BUSINESS UNITS ] (Divisions / P&L Centers)            │
       │          │                                                │
       │          ▼                                                │
       │      [ TEAMS ] (Departments / Squads) ◄──► [ CUSTOMERS ]   │
       │          │                                                │
       │          ▼                                                │
       │      [ USERS ] (Developers / Admins / Viewers)             │
       └───────────────────────────┬───────────────────────────────┘
                                   │
                                   ▼ (Governed by RBAC Matrix)
       ┌───────────────────────────┐   ┌───────────────────────────┐
       │      ACCESS PROFILES      │──►│       VIRTUAL KEYS        │
       │  • Model Allowlists       │   │  • Cryptographic Tokens   │
       │  • Budget & Rate Limits   │   │  • Granular Cost Caps     │
       │  • Guardrails & MCP Tools │   │  • Instant Revocation     │
       └───────────────────────────┘   └─────────────┬─────────────┘
                                                     │ (Bearer uf-key-...)
                                                     ▼
       ┌───────────────────────────────────────────────────────────┐
       │               FastHTTP PROXY GATEWAY                      │
       │  • Token Auth, Budget check, IP verification              │
       └───────────────────────────┬───────────────────────────────┘
                                   │
                                   ▼
       ┌───────────────────────────────────────────────────────────┐
       │                      PLUGINS ENGINE                       │
       │  • Pre-Request Hooks: Custom Auth, Headers, Validation    │
       │  • Post-Request & Streaming Hooks: Billing, Scrubbing     │
       └───────────────────────────┬───────────────────────────────┘
                                   │
                                   ▼
       ┌───────────────────────────────────────────────────────────┐
       │                        AUDIT LOGS                         │
       │  • Immutable Record: Actor, Action, Target, Diff, IP      │
       └───────────────────────────────────────────────────────────┘
```

---

# 2. Detailed Feature Dissection (10 Core Features)
### Pathu Features-oda Aazhamana Vivaram (Thanglish + English)

<a name='plugins'></a>
## Plugins — Plugins (Gateway Extensions & Lifecycle Hooks)
**UI Route:** `/workspace/plugins`

### 👤 Non-Tech Perspective (Makkal Puriyura Mathiri Eliya Vilakkam)
- **Uruvagam (Analogy):** Chrome browser extensions allathu WordPress plugins mathiri.
- **Vilakkam (Explanation):** UnifAI AI Gateway-kulla ungalukku thevaiyana custom logic-ah (e.g. custom token counter, sentiment checking, internal billing webhook, proprietary data tagging) add panni gateway functionality-ah expand pandra extensible plugin engine. Gateway core code-ah maathaama plug-and-play-ah puthu features load pannikalam.
- **Business Value (Vaniga Payan):** Company-oda proprietary security, legal compliance, and custom billing rules-ah AI request flow-kulla zero friction-oda seamlessly integrate pannalam.

### 💻 Tech Perspective (Engineers-kaga Technical Architecture)
- **Backend Architecture:** WebAssembly (Wasm) and Go-based lifecycle interceptor pipeline. Hooks into 4 critical execution phases: `pre-request` (header validation, prompt enrichment), `post-request` (response manipulation), `response-streaming` (SSE chunk interception), and `error-handling`. Managed via dynamic plugin registry and ordered via execution sequence priority.
- **Backend Endpoints:**
  * `GET /api/v1/plugins`
  * `POST /api/v1/plugins`
  * `PATCH /api/v1/plugins/{plugin_id}`
  * `DELETE /api/v1/plugins/{plugin_id}`
  * `PUT /api/v1/plugins/sequence`

### 🖥️ Screen Layout & Interactive Elements (Thirai Koorugal & Buttons)
**1. Melpura Koorugal (Top Bar Controls):**
- Header Title with Puzzle Icon: Visual indicator of plugin management.
- Add New Plugin Button: Opens the plugin registration sheet.
- Plugin Sequence Button (ListOrdered): Opens visual re-ordering dialog to configure execution pipeline precedence.

**2. Mathiya Koorugal & Tables (Tabs & Views):**
- Plugins Sidebar: List of custom plugins with active selection highlight, icon, and plugin name.
- PluginsView: Main editor panel showing Plugin Name, Description, Version, Schema definition, and Active Toggle Switch.
- Execution Hook Selectors: Toggles for Pre-Request, Post-Request, Response-Streaming, and Error-Handling.

**3. Keezhpura Koorugal & Sheets (Bottom Elements & Slide-Overs):**
- AddNewPluginSheet: Slide-over form to register plugin name, code/URL, target hooks, and initial configuration parameters.
- PluginSequenceSheet: Drag-and-drop or order selector determining which plugin executes first, second, or last in the proxy chain.
- Delete Plugin Confirmation Dialog: Safeguard preventing accidental deletion of active production plugins.

### 🔗 Connections & Structure Map (Inaippugal)
- **Data-vai Perumidam (Receives From):** Intercepts raw incoming client requests in FastHTTP Proxy before Routing Rules.
- **Iyakkum Koorugal (Triggers & Affects):** Enriches request headers, modifies prompt payloads, triggers external webhooks, and logs execution traces to LLM Logs.

### 💡 Production Use Case: Adding an internal compliance plugin that intercepts all prompts, runs a custom legal disclaimer check, and injects billing tags before forwarding to OpenAI.

---

<a name='virtual_keys'></a>
## Virtual Keys — Virtual Keys (Proxy API Keys & Granular Quotas)
**UI Route:** `/workspace/governance/virtual-keys`

### 👤 Non-Tech Perspective (Makkal Puriyura Mathiri Eliya Vilakkam)
- **Uruvagam (Analogy):** Bank master account-ku multiple sub-debit cards kudukura mathiri (ovvoru card-kum thani thani limit & PIN).
- **Vilakkam (Explanation):** Unga unmaiyana master OpenAI / Anthropic API keys-ah developers kitta direct-ah kudukka thevaiye illa! Athukku bathila 'Virtual Key' create panni kudupom. Intha virtual key-la monthly $100 budget, specific models mattum use panra permission, and rate limit set pannalam. Oru key leak aanaalum single click-la revoke allathu rotate pannikalam, real keys safe-ah irukkum.
- **Business Value (Vaniga Payan):** Zero credential leakage risk; 100% granular cost attribution by team/app; instant security revocation without breaking other applications.

### 💻 Tech Perspective (Engineers-kaga Technical Architecture)
- **Backend Architecture:** High-throughput cryptographic API key gateway middleware. Keys are generated with cryptographically secure tokens (`uf-key-...`) and stored as one-way SHA-256 hashes in PostgreSQL/Redis. FastHTTP auth middleware validates tokens in < 1ms, loads associated Access Profiles, checks budget balances, and enforces RPM/TPM token rate limits before proxying.
- **Backend Endpoints:**
  * `GET /api/v1/governance/virtual-keys`
  * `POST /api/v1/governance/virtual-keys`
  * `PATCH /api/v1/governance/virtual-keys/{key_id}`
  * `DELETE /api/v1/governance/virtual-keys/{key_id}`
  * `POST /api/v1/governance/virtual-keys/rotate`
  * `POST /api/v1/governance/virtual-keys/bulk-rotate`

### 🖥️ Screen Layout & Interactive Elements (Thirai Koorugal & Buttons)
**1. Melpura Koorugal (Top Bar Controls):**
- Create Virtual Key Button: Opens key generation sheet.
- Bulk Rotate Keys Button: Triggers multi-key credential rotation dialog.
- Search & Filter Bar: Debounced search by key name, filter by Team, Customer, or Status (Active / Suspended).

**2. Mathiya Koorugal & Tables (Tabs & Views):**
- Virtual Keys Table: Columns for Key Name, Masked Secret Value (with copy button and eye toggle reveal), Team / Customer association, Budget Progress Bar (BudgetDisplay), Rate Limit badge (RateLimitDisplay), Status Toggle Switch (Active/Suspended), Actions Menu.
- Pinned Actions Column: Quick actions for Edit, Rotate Key, View Logs deep-link, and Delete.

**3. Keezhpura Koorugal & Sheets (Bottom Elements & Slide-Overs):**
- VirtualKeySheet (Slide-Over): Name, Description, Team assignment, Customer link, Access Profile attachment, Budget Cap ($), Rate Limits (Requests/min, Tokens/min), Model Allowlist/Denylist, IP Whitelist, Expiration Date.
- Key Secret Reveal Modal: One-time high-security display modal showing the full unmasked key upon creation with copy-to-clipboard button.

### 🔗 Connections & Structure Map (Inaippugal)
- **Data-vai Perumidam (Receives From):** Attached to Teams, Customers, and Access Profiles configured in Governance.
- **Iyakkum Koorugal (Triggers & Affects):** Authorizes incoming requests in FastHTTP Proxy; tracks spend into LLM Logs, Dashboard, and Budgets & Limits.

### 💡 Production Use Case: Issuing a virtual key with a $200/month cap and Gemini-only access to an external vendor development agency.

---

<a name='users'></a>
## Users — Users (Platform User Directory & Identity Management)
**UI Route:** `/workspace/governance/users`

### 👤 Non-Tech Perspective (Makkal Puriyura Mathiri Eliya Vilakkam)
- **Uruvagam (Analogy):** Company employee directory & staff ID register mathiri.
- **Vilakkam (Explanation):** UnifAI platform-la account irukkura ellam developers, team leads, finance managers, and admins list. Yaar yaar enna email, enna role (Admin, Member, Viewer), entha team-la irukaanga nu paathu manage pandra central user directory.
- **Business Value (Vaniga Payan):** Identity governance, frictionless employee onboarding, and automated access termination when personnel depart.

### 💻 Tech Perspective (Engineers-kaga Technical Architecture)
- **Backend Architecture:** User identity and authentication manager. Integrated with enterprise SSO (SAML 2.0 / OIDC / OAuth 2.0) and automated SCIM provisioning. Sessions are cryptographically signed using JWTs. Enforces multi-factor authentication (MFA) and maintains foreign key relations to Teams, Virtual Keys, and RBAC roles.
- **Backend Endpoints:**
  * `GET /api/v1/governance/users`
  * `POST /api/v1/governance/users/invite`
  * `PATCH /api/v1/governance/users/{user_id}`
  * `DELETE /api/v1/governance/users/{user_id}`
  * `POST /api/v1/governance/users/{user_id}/reset-mfa`

### 🖥️ Screen Layout & Interactive Elements (Thirai Koorugal & Buttons)
**1. Melpura Koorugal (Top Bar Controls):**
- Invite User Button: Opens email invitation dialog with role assignment.
- Search Bar: Search users by name, email, or role.
- Filter Dropdown: Filter by Role (Admin, Member, Viewer) or Status (Active, Invited, Suspended).

**2. Mathiya Koorugal & Tables (Tabs & Views):**
- Users Table: Columns for User Avatar & Name, Email Address, Assigned RBAC Role badge, Team Memberships, Last Active Timestamp, Account Status badge (Active/Pending), Actions Menu.
- User Activity Card: Summary of user's personal virtual keys, aggregate token consumption, and audit trail link.

**3. Keezhpura Koorugal & Sheets (Bottom Elements & Slide-Overs):**
- InviteUserDialog: Form for User Email, Full Name, Initial Role selection, and Assigned Teams.
- EditUserSheet: Slide-over form to update assigned roles, toggle admin privileges, change team assignments, or suspend user access.
- Deactivate User Confirmation Modal: Revokes all active user tokens and reassigns created virtual keys.

### 🔗 Connections & Structure Map (Inaippugal)
- **Data-vai Perumidam (Receives From):** Synced automatically from SCIM / SSO or manually invited by Admins.
- **Iyakkum Koorugal (Triggers & Affects):** Binds to Teams, Virtual Keys, and RBAC roles; logs all platform actions into Audit Logs.

### 💡 Production Use Case: Onboarding 50 new data science engineers simultaneously and assigning them to the 'AI Research Team' with Member-level permissions.

---

<a name='teams'></a>
## Teams — Teams (Departmental Squads & Shared Resource Pools)
**UI Route:** `/workspace/governance/teams`

### 👤 Non-Tech Perspective (Makkal Puriyura Mathiri Eliya Vilakkam)
- **Uruvagam (Analogy):** Company departments allathu project squads mathiri (e.g. Mobile App Squad, Core Search Team, AI Labs).
- **Vilakkam (Explanation):** Developers-ah project allathu department vaariya group panni team-ah pirikalam. Oru team-ku common monthly budget, shared virtual keys, and collaborative model access kudukalam. Team-la irukkura yaar token use panninaalum antha team budget-la irunthu கழிவு aagum.
- **Business Value (Vaniga Payan):** Departmental accountability; eliminates individual credential confusion; enables team-level AI spend tracking for CFO budget reviews.

### 💻 Tech Perspective (Engineers-kaga Technical Architecture)
- **Backend Architecture:** Multi-tenant team resource isolation layer. Aggregates usage across all member users and attached virtual keys. Enforces team-level budget limits in PostgreSQL, controls shared access profiles, and maps seamlessly to enterprise SCIM groups.
- **Backend Endpoints:**
  * `GET /api/v1/governance/teams`
  * `POST /api/v1/governance/teams`
  * `PATCH /api/v1/governance/teams/{team_id}`
  * `DELETE /api/v1/governance/teams/{team_id}`
  * `POST /api/v1/governance/teams/{team_id}/members`

### 🖥️ Screen Layout & Interactive Elements (Thirai Koorugal & Buttons)
**1. Melpura Koorugal (Top Bar Controls):**
- Create Team Button: Opens team creation dialog.
- Search Input: Search teams by name or business unit.
- Business Unit Filter: Filter teams by parent division.

**2. Mathiya Koorugal & Tables (Tabs & Views):**
- Teams Table: Columns for Team Name, Description, Members Count badge, Associated Virtual Keys count, Monthly Budget Progress Bar, Parent Business Unit, Actions Menu.
- Team Details Sheet: Comprehensive breakdown showing Team Leads, Active Members, Assigned Virtual Keys, and 30-day spend trajectory graph.

**3. Keezhpura Koorugal & Sheets (Bottom Elements & Slide-Overs):**
- CreateTeamDialog: Form specifying Team Name, Description, Parent Business Unit selection, Monthly Budget Allocation ($), and Initial Team Lead.
- ManageMembersSheet: Modal to add or remove members and adjust user team roles (Team Lead vs Member).

### 🔗 Connections & Structure Map (Inaippugal)
- **Data-vai Perumidam (Receives From):** Belongs to a parent Business Unit and groups multiple Users.
- **Iyakkum Koorugal (Triggers & Affects):** Owns shared Virtual Keys; feeds departmental spend rollups into Dashboard and Connectors (Datadog/Kafka).

### 💡 Production Use Case: Allocating a shared $3,000 monthly budget to the 'E-Commerce Recommendations Team' with 12 developers using 4 shared virtual keys.

---

<a name='business_units'></a>
## Business Units — Business Units (Enterprise Divisions & P&L Centers)
**UI Route:** `/workspace/governance/business-units`

### 👤 Non-Tech Perspective (Makkal Puriyura Mathiri Eliya Vilakkam)
- **Uruvagam (Analogy):** Periya corporate conglomerate-oda divisions mathiri (e.g. Retail Division, Banking Division, Healthcare Division).
- **Vilakkam (Explanation):** Teams-ku mela irukura periya enterprise division. CFO and executive leadership company-oda multiple business units-kulla AI budget分配 pannavum, P&L (Profit & Loss) tracking seiyavum use aagum. Oru division kulla 10 teams irukkalam.
- **Business Value (Vaniga Payan):** High-level corporate financial governance; automated chargebacks across major business divisions; strategic AI budget planning.

### 💻 Tech Perspective (Engineers-kaga Technical Architecture)
- **Backend Architecture:** Top-level organizational container in the multi-tenant governance tree (`BusinessUnit -> Teams -> Users -> Virtual Keys`). Aggregates financial consumption metrics via database rollups and provides master cost-allocation tags for corporate accounting systems (SAP, NetSuite).
- **Backend Endpoints:**
  * `GET /api/v1/governance/business-units`
  * `POST /api/v1/governance/business-units`
  * `PATCH /api/v1/governance/business-units/{bu_id}`
  * `DELETE /api/v1/governance/business-units/{bu_id}`

### 🖥️ Screen Layout & Interactive Elements (Thirai Koorugal & Buttons)
**1. Melpura Koorugal (Top Bar Controls):**
- Create Business Unit Button: Opens division registration sheet.
- Search Input: Search divisions by name or corporate code.

**2. Mathiya Koorugal & Tables (Tabs & Views):**
- Business Units Table: Columns for Unit Name, Corporate Cost Code, Description, Total Sub-Teams count, Aggregate Spend ($), Head of Business Unit, Actions Menu.
- Hierarchical Rollup View: Expandable accordion showing all teams, members, and keys nested under this business unit.

**3. Keezhpura Koorugal & Sheets (Bottom Elements & Slide-Overs):**
- BusinessUnitSheet: Form specifying Business Unit Name, Cost Center Code, Executive Owner email, Annual/Quarterly AI Budget Cap ($).
- Delete Confirmation Modal: Reassigns or archives child teams before division deletion.

### 🔗 Connections & Structure Map (Inaippugal)
- **Data-vai Perumidam (Receives From):** Configured by executive administrators and finance directors.
- **Iyakkum Koorugal (Triggers & Affects):** Contains multiple Teams; feeds top-level cost analytics into Executive Dashboards and Billing Connectors.

### 💡 Production Use Case: Tracking that the 'Global Wealth Management' division consumed $45,000 in AI tokens this quarter across its 8 engineering teams.

---

<a name='customers'></a>
## Customers — Customers (B2B Client Tenants & External Accounts)
**UI Route:** `/workspace/governance/customers`

### 👤 Non-Tech Perspective (Makkal Puriyura Mathiri Eliya Vilakkam)
- **Uruvagam (Analogy):** SaaS platform-la irukura external client accounts mathiri (B2B Multi-tenancy).
- **Vilakkam (Explanation):** Neenga unga software-ah vera external clients-ku AI features vachu SaaS product-ah vikkiringa na, ovvoru client-aiyum 'Customer'-ah add panni avanga usage-ku bill podalam. Oru customer innoru customer-oda data-vai paarka mudiyathu.
- **Business Value (Vaniga Payan):** Monetize AI applications; seamless B2B client isolation; automated billing invoices based on client consumption.

### 💻 Tech Perspective (Engineers-kaga Technical Architecture)
- **Backend Architecture:** External tenant isolation boundary. Associates virtual keys with external customer identifiers (`customer_id`). Enforces hard tenant isolation policies in PostgreSQL using Row-Level Security (RLS) and powers multi-tenant usage metering pipelines.
- **Backend Endpoints:**
  * `GET /api/v1/governance/customers`
  * `POST /api/v1/governance/customers`
  * `PATCH /api/v1/governance/customers/{customer_id}`
  * `DELETE /api/v1/governance/customers/{customer_id}`

### 🖥️ Screen Layout & Interactive Elements (Thirai Koorugal & Buttons)
**1. Melpura Koorugal (Top Bar Controls):**
- Create Customer Button: Opens customer onboarding modal.
- Search & Filter: Search by customer name, external company ID, or account tier.

**2. Mathiya Koorugal & Tables (Tabs & Views):**
- Customers Table: Columns for Customer Name, Account Status badge (Active/Trial/Suspended), Assigned Teams, Number of Virtual Keys, Cumulative Spend ($), Account Tier, Actions Menu.
- Usage Metering Panel: Detailed graph of customer's token consumption broken down by day and model.

**3. Keezhpura Koorugal & Sheets (Bottom Elements & Slide-Overs):**
- CustomerSheet: Form specifying Customer Name, External Account ID, Contact Email, Assigned Pricing Tier, and Hard Spend Quota.
- Suspend Customer Modal: Temporarily halts all virtual keys assigned to this customer during billing delinquency.

### 🔗 Connections & Structure Map (Inaippugal)
- **Data-vai Perumidam (Receives From):** Created by sales or synced from CRM (Salesforce, Stripe).
- **Iyakkum Koorugal (Triggers & Affects):** Scopes Virtual Keys and filters LLM Logs for customer-specific audit and billing exports.

### 💡 Production Use Case: Providing 100 enterprise B2B customers their own dedicated virtual keys with strictly metered billing for your AI-powered legal document review SaaS.

---

<a name='scim'></a>
## User Provisioning (SCIM) — User Provisioning / SCIM (Automated Enterprise SSO & Lifecycle Sync)
**UI Route:** `/workspace/scim`

### 👤 Non-Tech Perspective (Makkal Puriyura Mathiri Eliya Vilakkam)
- **Uruvagam (Analogy):** Automatic company ID card issuing & revoking machine mathiri (HR portal-la employee join aana automatic-ah account create aagum).
- **Vilakkam (Explanation):** Company HRMS allathu Identity Provider (Okta, Microsoft Entra ID / Azure AD, Keycloak)-la pudhu aal sertha automatic-ah UnifAI-layum login create aagum. Employee velaiya vittu ponavudane Okta-la offboard pannina, automatic-ah UnifAI access cut aagidum! Manual-ah user create panna thevaiye illa.
- **Business Value (Vaniga Payan):** Zero orphan accounts; 100% SOC-2 & ISO-27001 compliance for employee lifecycle security; automated enterprise IT operations.

### 💻 Tech Perspective (Engineers-kaga Technical Architecture)
- **Backend Architecture:** Standard SCIM v2.0 (RFC 7643 & RFC 7644) server implementation. Exposes `/scim/v2/Users`, `/scim/v2/Groups`, and `/scim/v2/ServiceProviderConfig`. Authenticated via cryptographically generated Bearer tokens. Parses incoming SCIM JSON payloads to automatically create, update, deactivate users, and synchronize directory group memberships to UnifAI Teams.
- **Backend Endpoints:**
  * `GET /scim/v2/Users`
  * `POST /scim/v2/Users`
  * `GET /scim/v2/Users/{id}`
  * `PUT /scim/v2/Users/{id}`
  * `PATCH /scim/v2/Users/{id}`
  * `DELETE /scim/v2/Users/{id}`
  * `GET /scim/v2/Groups`
  * `GET /api/v1/scim/config`
  * `PUT /api/v1/scim/config`

### 🖥️ Screen Layout & Interactive Elements (Thirai Koorugal & Buttons)
**1. Melpura Koorugal (Top Bar Controls):**
- Header Title with UserRoundCog Icon: Visual indicator of SCIM provisioning.
- SCIM Master Enable Switch: Instant activation/deactivation toggle.

**2. Mathiya Koorugal & Tables (Tabs & Views):**
- SCIM Endpoints Card: Copyable endpoint URLs for IdP configuration:
- • Base URL: `https://<domain>/scim/v2` (with Copy button)
- • Users Endpoint: `https://<domain>/scim/v2/Users` (with Copy button)
- • ServiceProviderConfig: `https://<domain>/scim/v2/ServiceProviderConfig`
- IdP Provider Selector: Toggle between Okta, Microsoft Entra ID (Azure AD), Keycloak, and Custom SCIM v2 Provider.

**3. Keezhpura Koorugal & Sheets (Bottom Elements & Slide-Overs):**
- Bearer Token Management: Secret token generator with copy button and rotation warning.
- Group Mapping Card: Rules mapping external directory groups (e.g. `okta-ai-engineers`) directly into UnifAI Teams and RBAC roles.
- Save SCIM Config Button: Commits configuration with toast confirmation.

### 🔗 Connections & Structure Map (Inaippugal)
- **Data-vai Perumidam (Receives From):** External Identity Providers (Okta, Microsoft Entra ID, PingIdentity).
- **Iyakkum Koorugal (Triggers & Affects):** Automatically provisions and deprovisions Users and synchronizes Team memberships.

### 💡 Production Use Case: Automatically creating UnifAI accounts for 2,000 corporate employees via Okta SCIM sync and immediately revoking access when an employee leaves the company.

---

<a name='rbac'></a>
## Roles & Permissions (RBAC) — Roles & Permissions (RBAC Security & Granular Access Matrix)
**UI Route:** `/workspace/governance/rbac`

### 👤 Non-Tech Perspective (Makkal Puriyura Mathiri Eliya Vilakkam)
- **Uruvagam (Analogy):** Office security access badge permissions mathiri (Receptionist lobby-ku mattum entry, Server room-ku Admin mattum entry).
- **Vilakkam (Explanation):** Yaaru platform-la enna seiyalaam nu kattu paduthum access control matrix. Super Admin-ku full control irukkum; Developer-ku API key create panna mattum permission; Finance Manager-ku logs and billing charts mattum paarka permission (read-only); Normal user-ku settings maatha permission irukaathu.
- **Business Value (Vaniga Payan):** Least-privilege security principle. Accidental deletions, unauthorized key tampering, and unauthorized configuration changes-ah 100% prevent pannum.

### 💻 Tech Perspective (Engineers-kaga Technical Architecture)
- **Backend Architecture:** Declarative Role-Based Access Control (RBAC) engine in Go and React. Enforces fine-grained resource-action pairs (`Resource: ModelProvider, VirtualKeys, RoutingRules, Settings, AuditLogs, Plugins, Governance` × `Action: View, Create, Update, Delete`). Evaluates permissions on every FastHTTP management endpoint and hides UI components conditionally via `useRbac()` hook.
- **Backend Endpoints:**
  * `GET /api/v1/governance/rbac/roles`
  * `POST /api/v1/governance/rbac/roles`
  * `PATCH /api/v1/governance/rbac/roles/{role_id}`
  * `DELETE /api/v1/governance/rbac/roles/{role_id}`
  * `GET /api/v1/governance/rbac/permissions`

### 🖥️ Screen Layout & Interactive Elements (Thirai Koorugal & Buttons)
**1. Melpura Koorugal (Top Bar Controls):**
- Create Custom Role Button: Opens role builder dialog.
- Role Filter: Filter by System Roles (Admin, Member, Read-Only) vs Custom Defined Roles.

**2. Mathiya Koorugal & Tables (Tabs & Views):**
- Roles Table: Columns for Role Name, Description, Assigned Users count badge, Role Type (System / Custom), Actions Menu.
- RBAC Permission Matrix Grid: Comprehensive grid displaying Resources on rows (Virtual Keys, Model Providers, Routing Rules, Budgets, Audit Logs) and Actions on columns (View, Create, Update, Delete) with interactive checkboxes.

**3. Keezhpura Koorugal & Sheets (Bottom Elements & Slide-Overs):**
- RoleBuilderSheet: Slide-over form to name custom role, define description, and toggle specific permission checkboxes.
- AssignUsersModal: Dialog to bulk-assign the role to specific users or teams.

### 🔗 Connections & Structure Map (Inaippugal)
- **Data-vai Perumidam (Receives From):** Assigned to Users and SCIM directory groups.
- **Iyakkum Koorugal (Triggers & Affects):** Enforces authorization gates across all UnifAI UI navigation, buttons, and backend REST APIs.

### 💡 Production Use Case: Creating a 'Finance Auditor' custom role that can View Dashboard, View LLM Logs, and View Pricing Overrides, but cannot Create, Edit, or Delete any keys or models.

---

<a name='access_profiles'></a>
## Access Profiles — Access Profiles (Reusable Policy Bundles & Guardrail Packs)
**UI Route:** `/workspace/governance/access-profiles`

### 👤 Non-Tech Perspective (Makkal Puriyura Mathiri Eliya Vilakkam)
- **Uruvagam (Analogy):** Pre-packaged security bundle allathu employee safety passport mathiri.
- **Vilakkam (Explanation):** Oru standard policy template create panni vachikalam. Example: 'Intern Security Profile'—ithula GPT-4o-mini mattum allow panni, $50 budget limit, sensitive PII data redaction guardrails, and office IP restriction potruppom. Pudhu virtual key create pannum pothu intha profile-ah select panna ella security rules-um automatic-ah apply aagidum!
- **Business Value (Vaniga Payan):** Massive administrative time savings; eliminates configuration mistakes; guarantees that no virtual key goes live without corporate security guardrails.

### 💻 Tech Perspective (Engineers-kaga Technical Architecture)
- **Backend Architecture:** Reusable policy entity bundling multiple governance constraints: Allowed Model Patterns, Allowed Providers, Budget Maximums & Reset Cadences, Request/Token Rate Limits (RPM/TPM), Attached MCP Tool Clients, and DLP Guardrail policies. Attached to Virtual Keys via relational join, allowing instant fleet-wide policy updates when a profile is edited.
- **Backend Endpoints:**
  * `GET /api/v1/governance/access-profiles`
  * `POST /api/v1/governance/access-profiles`
  * `PATCH /api/v1/governance/access-profiles/{profile_id}`
  * `DELETE /api/v1/governance/access-profiles/{profile_id}`
  * `POST /api/v1/governance/access-profiles/{profile_id}/clone`

### 🖥️ Screen Layout & Interactive Elements (Thirai Koorugal & Buttons)
**1. Melpura Koorugal (Top Bar Controls):**
- Create Access Profile Button: Opens profile builder dialog.
- Search & Tag Filter: Filter profiles by tag (e.g. `production`, `intern`, `customer-facing`).

**2. Mathiya Koorugal & Tables (Tabs & Views):**
- Access Profiles Table: Columns for Profile Name, Tags badges, Allowed Models summary, Attached Virtual Keys count, Budget & Rate Limit summary, Actions Menu.
- Quick Clone Button: Instantly duplicates an existing profile for fast customization.

**3. Keezhpura Koorugal & Sheets (Bottom Elements & Slide-Overs):**
- AccessProfileDialog: Comprehensive form configuring:
- • Profile Name, Description, and Categorization Tags.
- • Allowed Providers & Model Multiselect (or regex wildcard `gpt-4o-*`).
- • Budget Caps: Max Dollar Limit ($) & Reset Duration (Daily, Monthly).
- • Rate Limits: Max Requests per Minute (RPM) and Max Tokens per Minute (TPM).
- • MCP Client Permissions: Select which autonomous tools this profile can execute.
- • Attached Virtual Keys selector.

### 🔗 Connections & Structure Map (Inaippugal)
- **Data-vai Perumidam (Receives From):** Created by Security & Compliance administrators.
- **Iyakkum Koorugal (Triggers & Affects):** Governs Virtual Keys behavior, restricts Model Providers, and enforces MCP Gateway tool permissions.

### 💡 Production Use Case: Attaching a single 'Customer Facing Chatbot Profile' to 20 virtual keys, guaranteeing strict PII redaction and 50 RPM rate limits across all 20 keys simultaneously.

---

<a name='audit_logs'></a>
## Audit Logs — Audit Logs (Tamper-Proof Compliance & Activity Trail)
**UI Route:** `/workspace/audit-logs`

### 👤 Non-Tech Perspective (Makkal Puriyura Mathiri Eliya Vilakkam)
- **Uruvagam (Analogy):** Bank locker CCTV camera & register note mathiri.
- **Vilakkam (Explanation):** Platform-la yaaru yaaru entha nerathula enna maathinaanga nu maatha mudiyatha (tamper-proof) pathivu. Yaarachum API key delete pannalaam, budget limit maathinaalo, pudhu routing rule pottaalo exact timestamp, user name, and client IP address-oda capture aagum. 'Who did what and when' nu eppovum proof irukkum.
- **Business Value (Vaniga Payan):** 100% SOC-2, HIPAA, and GDPR audit readiness. Insider threat detection and rapid forensic debugging during system anomalies.

### 💻 Tech Perspective (Engineers-kaga Technical Architecture)
- **Backend Architecture:** Immutable, append-only security event audit trail. Intercepts all administrative REST mutations in middleware. Captures Actor User ID, Action Type (CREATE, UPDATE, DELETE), Target Resource, Resource ID, Timestamp, Origin Client IP address, User-Agent, and detailed before/after JSON diffs. Stored in partitioned, tamper-evident PostgreSQL tables with optional S3 Glacier write-once-read-many (WORM) archival.
- **Backend Endpoints:**
  * `GET /api/v1/audit-logs`
  * `GET /api/v1/audit-logs/{log_id}`
  * `GET /api/v1/audit-logs/export`

### 🖥️ Screen Layout & Interactive Elements (Thirai Koorugal & Buttons)
**1. Melpura Koorugal (Top Bar Controls):**
- Date Range Picker: Quick filters for 24h, 7d, 30d, 90d, and custom calendar range.
- Actor Search Input: Search by user email or user ID.
- Action Type Filter: Filter by CREATE, UPDATE, DELETE, ROTATE, LOGIN.
- Resource Filter: Filter by Virtual Keys, Routing Rules, Model Providers, Users, Teams, etc.
- Export Button: Download audit logs in CSV or JSON format for external auditors.

**2. Mathiya Koorugal & Tables (Tabs & Views):**
- Audit Logs Table: Columns for Timestamp (UTC/Local), Actor Name & Email, Action Badge (Create [green], Update [blue], Delete [red]), Resource Type, Target Resource Name/ID, Client IP Address, Details Button.
- Pagination Controls: Fast offset/cursor pagination handling hundreds of thousands of audit events.

**3. Keezhpura Koorugal & Sheets (Bottom Elements & Slide-Overs):**
- Audit Detail Drawer / Modal: Displays the complete before-and-after JSON delta diff highlighting exact fields that were modified during the administrative action.

### 🔗 Connections & Structure Map (Inaippugal)
- **Data-vai Perumidam (Receives From):** Automatically intercepts administrative operations across all Governance, Models, and Observability features.
- **Iyakkum Koorugal (Triggers & Affects):** Feeds security incident alerts into Alert Channels and provides evidence for external compliance auditors.

### 💡 Production Use Case: Forensic audit demonstrating to external SOC-2 auditors exactly who rotated the production Bedrock credentials on August 14th at 03:22 UTC.

---

# 3. Cross-Feature Interconnections & Data Flow
### Governance & Plugins Features Kulla Irukura Direct Connections

| Source Feature | Connected To | Data Flow & Trigger Action |
| :--- | :--- | :--- |
| **Plugins** | **FastHTTP Proxy** | Intercepts pre/post request payloads to run custom enterprise compliance logic. |
| **Virtual Keys** | **Access Profiles** | Inherits model restrictions, budget limits, and MCP tool permissions from assigned profiles. |
| **Users** | **Teams** | Organized into collaborative squads that share aggregate budgets and virtual keys. |
| **Teams** | **Business Units** | Rolls up departmental spend and resource counts into corporate division P&L centers. |
| **Customers** | **Virtual Keys** | Isolates external B2B client applications with dedicated credentials and usage tracking. |
| **SCIM** | **Users & Teams** | Automatically provisions users and syncs directory groups from Okta and Microsoft Entra ID. |
| **RBAC** | **All UI & Endpoints** | Enforces fine-grained View/Create/Update/Delete permissions on every button and API. |
| **Access Profiles** | **Virtual Keys** | Enforces model allowlists, token quotas, and rate-limits across fleets of keys. |
| **Audit Logs** | **All Features** | Immutably records every configuration change, key rotation, and administrative event. |

---

# 4. Tech vs Non-Tech Comparative Matrix
### Thozhilnutpam vs Vanigam Parvai Oppeedo

| Feature | Non-Tech View (Manager / CFO Parvai) | Tech View (DevOps / Architect Parvai) |
| :--- | :--- | :--- |
| **Plugins** | "Custom rules and company billing logic-ah gateway-kulla plug-and-play-ah add panna mudiyuma?" | "Wasm/Go lifecycle interceptor pipeline hooking into pre-request, post-request, and streaming chunks." |
| **Virtual Keys** | "Real OpenAI master keys-ah kudukama safe-ana dummy keys with budget limits kudukalama?" | "Cryptographic SHA-256 hashed API tokens with sub-millisecond FastHTTP auth and rate limiters." |
| **Users** | "Company-la irukkura ellam developers and staff directory-ah ore idathula manage pannalama?" | "Central identity directory integrated with enterprise SSO (OIDC/SAML) and JWT session tokens." |
| **Teams** | "Developers-ah group panni project teams-kaga shared budget and keys allocate pannalama?" | "Multi-tenant team resource isolation layer aggregating spend and managing shared virtual keys." |
| **Business Units** | "CFO and leadership periya divisions (Retail, Banking) vaariya AI spend track panna mudiyuma?" | "Top-level corporate cost center container rolling up child teams for SAP/NetSuite accounting." |
| **Customers** | "Vera external B2B clients-ku AI features vithu avangalukku thaniya bill poda mudiyuma?" | "External tenant isolation boundary enforcing RLS data separation and customer-metered billing." |
| **SCIM** | "Okta allathu Entra ID-la employee join aana automatic-ah account create aagi, leave aana cut aaguma?" | "RFC 7643/7644 SCIM v2.0 server handling automated user lifecycle and group synchronization." |
| **RBAC** | "Admin-ku mattum full rights, mathavangalukku view-only permission pottu security maintain pannalama?" | "Declarative resource-action permission matrix evaluating gates across all UI views and REST APIs." |
| **Access Profiles** | "Reusable standard security template create panni 20 keys-ku single click-la apply pannalama?" | "Bundled governance policy entity containing model allowlists, budget caps, rate limits, and MCP permissions." |
| **Audit Logs** | "Yaaru entha key-ah maathinaanga, eppo delete panninaanga nu maatha mudiyatha proof irukka?" | "Append-only immutable audit trail capturing actor, action, timestamp, IP, and before/after JSON diffs." |
