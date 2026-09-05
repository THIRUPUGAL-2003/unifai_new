# UnifAI Complete Platform Master Deep-Dive Technical Manual
## UnifAI Muzhumaiyana Architecture, Features, Layout & Operations Guide

**Document Status:** Complete & Exhaustive (40 Core Features Across 9 Pillars)  
**Target Audience:** Developers, System Architects, CTOs, CFOs, DevSecOps, SREs & Product Managers  
**Language:** Bilingual (Thanglish - Tamil in English letters + Clean English)  
**Generated At:** 2026-09-05  

---

## Table of Contents
1. [UnifAI Master System Architecture Map](#1-unifai-master-system-architecture-map)
2. [Comprehensive Pillars & Features Inventory (All 40 Features)](#2-comprehensive-pillars--features-inventory)
   - **Observability & Telemetry (Observability (Kangaanippu & Seyalthiran Paguppaayvu))**
     * [Dashboard — Dashboard (Main Metrics & Analytics Cockpit) (/workspace/dashboard)](#obs_dashboard)
     * [LLM Logs — LLM Logs (AI Request & Response Transaction Ledger) (/workspace/logs)](#obs_llm_logs)
     * [MCP Logs — MCP Logs (Autonomous Agent Tool Call Audit) (/workspace/mcp-logs)](#obs_mcp_logs)
     * [Browser AI — Browser AI (Employee Web ChatGPT DLP Proxy) (/workspace/browser-ai)](#obs_browser_ai)
     * [Connectors — Connectors (External Observability & Telemetry Pipelines) (/workspace/observability)](#obs_connectors)
     * [Logs Settings — Logs Settings (Log Governance & Retention Policies) (/workspace/config/logging)](#obs_logs_settings)
   - **Models & Traffic Control (Models (AI Model Catalog, Routing & Resilience))**
     * [Model Catalog — Model Catalog (AI Models Inventory & Menu) (/workspace/model-catalog)](#mod_catalog)
     * [Model Providers — Model Providers (AI Vendor Credentials & Gateway Settings) (/workspace/providers)](#mod_providers)
     * [Budgets & Limits — Budgets & Limits (Cost Caps & Token Rate Limits) (/workspace/model-limits)](#mod_limits)
     * [Routing Rules — Routing Rules (Intelligent Traffic Steering & Fallbacks) (/workspace/routing-rules)](#mod_routing)
     * [Complexity Router — Complexity Router (AI Query Triage & Cost Optimizer) (/workspace/complexity-router)](#mod_complexity)
     * [Circuit Breaker — Circuit Breaker (Outage Protection & Auto-Failover) (/workspace/circuit-breaker)](#mod_circuit_breaker)
     * [Pricing Overrides — Pricing Overrides (Custom Enterprise Rates & Discounts) (/workspace/custom-pricing/overrides)](#mod_pricing_overrides)
     * [Model Settings — Model Settings (Master Catalog Sync & Recursion Guard) (/workspace/custom-pricing)](#mod_settings)
   - **MCP Gateway & Tool Execution (MCP Gateway (Model Context Protocol & Agent Tools))**
     * [MCP Catalog — MCP Catalog (Tool Registry & App Store) (/workspace/mcp-registry)](#mcp_catalog)
     * [Installed Servers — Installed Servers (Active MCP Instances & Health) (/workspace/mcp-gateway)](#mcp_servers)
     * [MCP Sessions — Sessions (Live Stateful Agent Connections) (/workspace/mcp-sessions)](#mcp_sessions)
     * [Tool Groups — Tool Groups (Permission Bundles & Tool Access Control) (/workspace/mcp-tool-groups)](#mcp_tool_groups)
     * [Auth Config — Auth Config (MCP Security & Client Tokens) (/workspace/mcp-auth-config)](#mcp_auth_config)
     * [Gateway Settings — Gateway Settings (MCP Engine Timeouts & Network Ports) (/workspace/mcp-settings)](#mcp_settings)
   - **Prompt Management & Playground (Prompt Management (Prompt Repo, Skills & Chat Playground))**
     * [Prompt Repo — Prompt Repo (Version Controlled Prompt Templates) (/workspace/prompt-repo)](#prompt_repo)
     * [Skills Repo — Skills Repo (Reusable Agent Competencies & Knowledge Packs) (/workspace/skills-repo)](#skills_repo)
     * [Chat / Playground — Playground (Multi-Model Testing & Comparison Sandbox) (/workspace/chat)](#chat_playground)
   - **Plugins & Extensibility (Plugins (Gateway Extensions & Custom Logic))**
     * [Plugins — Plugins (Gateway Extensions & Lifecycle Hooks) (/workspace/plugins)](#plg_plugins)
   - **Governance & Identity (Governance (Identity, RBAC, Virtual Keys & Security))**
     * [Virtual Keys — Virtual Keys (Proxy API Keys & Granular Quotas) (/workspace/governance/virtual-keys)](#gov_virtual_keys)
     * [Users — Users (Platform User Directory & Identity Management) (/workspace/governance/users)](#gov_users)
     * [Teams — Teams (Departmental Squads & Shared Resource Pools) (/workspace/governance/teams)](#gov_teams)
     * [Business Units — Business Units (Enterprise Divisions & P&L Centers) (/workspace/governance/business-units)](#gov_business_units)
     * [Customers — Customers (B2B Client Tenants & External Accounts) (/workspace/governance/customers)](#gov_customers)
     * [User Provisioning (SCIM) — User Provisioning / SCIM (Automated Enterprise SSO Lifecycle) (/workspace/scim)](#gov_scim)
     * [Roles & Permissions (RBAC) — Roles & Permissions (RBAC Security & Access Matrix) (/workspace/governance/rbac)](#gov_rbac)
     * [Access Profiles — Access Profiles (Reusable Policy Bundles & Guardrail Packs) (/workspace/governance/access-profiles)](#gov_access_profiles)
     * [Audit Logs — Audit Logs (Tamper-Proof Compliance & Activity Trail) (/workspace/audit-logs)](#gov_audit_logs)
   - **Security Guardrails (Guardrails (Content Safety & Attack Prevention))**
     * [Guardrail Rules — Guardrail Rules (AI Safety Policies & Screening) (/workspace/guardrails/configuration)](#grd_rules)
     * [Guardrail Providers — Guardrail Providers (Security Engines & Regex Scanners) (/workspace/guardrails/providers)](#grd_providers)
   - **High Availability & Infrastructure (Infrastructure (Cluster Mesh, Alerts & OAuth))**
     * [Cluster Config — Cluster Config (Distributed Mesh & High-Availability Sync) (/workspace/cluster)](#inf_cluster)
     * [Alert Channels — Alert Channels (Incident Notifications & Webhooks) (/workspace/alert-channels)](#inf_alerts)
     * [OAuth Grants — OAuth Grants (Third-Party App Authorizations) (/workspace/oauth-grants)](#inf_oauth)
   - **Adaptive Routing & Load Balancing (Adaptive Routing (Dynamic Latency & Score-Based Balancing))**
     * [Adaptive Routing Dashboard — Adaptive Routing Dashboard (Live Health Scoring & Traffic Steering) (/workspace/adaptive-routing)](#adp_dashboard)
     * [Adaptive Routing Settings — Adaptive Routing Settings (Load Balancing Policy & Pruning Rules) (/workspace/adaptive-routing/settings)](#adp_settings)
3. [Cross-Feature Interconnections & Data Flow Matrix](#3-cross-feature-interconnections--data-flow-matrix)
4. [Master Tech vs Non-Tech Comparative Matrix](#4-master-tech-vs-non-tech-comparative-matrix)

---

# 1. UnifAI Master System Architecture Map
### Muzhumaiyana 9 Pillars End-to-End Traffic Steering, Security & Observability Flow

```
             [ ENTERPRISE IDENTITY (Okta / Microsoft Entra ID / IdP) ]
                                        │
                         (SCIM v2 Sync) ▼
       ┌────────────────────────────────────────────────────────────────┐
       │     GOVERNANCE: USERS, TEAMS, BUSINESS UNITS & CUSTOMERS       │
       │  • Multi-tenant organizational hierarchy & RBAC security       │
       │  • Access Profiles: Reusable model allowlists, budgets, tools  │
       └────────────────────────────────┬───────────────────────────────┘
                                        │ (Generates uf-key-...)
                                        ▼
       ┌────────────────────────────────────────────────────────────────┐
       │                       VIRTUAL KEYS                             │
       │  • Cryptographic SHA-256 API tokens with strict dollar quotas  │
       └────────────────────────────────┬───────────────────────────────┘
                                        │ (Client Bearer Request)
                                        ▼
       ┌────────────────────────────────────────────────────────────────┐
       │              FastHTTP HIGH-PERFORMANCE PROXY GATEWAY           │
       │  • Sub-millisecond token auth, Rate limit bucket verification  │
       └───────┬────────────────────────────────────────────────┬───────┘
               │                                                │
   (Cluster)   ▼                                                ▼ (Extensions)
       ┌────────────────────────┐                      ┌────────────────────────┐
       │     CLUSTER CONFIG     │                      │     PLUGINS ENGINE     │
       │  • Mesh Gossip (:7946) │                      │  • Wasm/Go Pre-Request │
       │  • Global Bucket Sync  │                      │  • Post-Req / Stream   │
       └────────────────────────┘                      └───────────┬────────────┘
                                                                   │
                                                                   ▼
       ┌────────────────────────────────────────────────────────────────┐
       │                  SECURITY GUARDRAILS ENGINE                    │
       │  • Guardrail Rules (CEL expressions, Prompt Repo bindings)     │
       │  • Guardrail Providers (Presidio, RE2 Regex, Llama-Guard)      │
       └───────┬────────────────────────────────────────────────┬───────┘
        (Fail) │                                                │ (Pass)
               ▼                                                ▼
       ┌────────────────────────┐                      ┌────────────────────────┐
       │ HTTP 400/403 Security  │                      │   COMPLEXITY ROUTER    │
       │ Violation (PII / Attack│                      │  • Score: 0.0 to 1.0   │
       └────────────────────────┘                      │  • Simple/Med/Comp/Reas│
                                                       └───────────┬────────────┘
                                                                   │
                                                                   ▼
       ┌────────────────────────────────────────────────────────────────┐
       │             ROUTING RULES & ADAPTIVE LOAD BALANCER             │
       │  • CEL expression evaluation, Priority target pools            │
       │  • Adaptive Routing: Real-time Multi-Armed Bandit health scores│
       │  • Circuit Breaker: Outage protection & zero-downtime failover │
       └───────────────────────────────┬────────────────────────────────┘
                                       │
                                       ▼
       ┌────────────────────────────────────────────────────────────────┐
       │              MODEL PROVIDERS & MCP TOOL GATEWAY                │
       │  • OpenAI / Anthropic / AWS Bedrock / Google Vertex / Ollama   │
       │  • MCP Gateway: Autonomous Agent Tool Execution (stdio / SSE)  │
       └───────────────────────────────┬────────────────────────────────┘
                                       │
                                       ▼
       ┌────────────────────────────────────────────────────────────────┐
       │             UNIFIED OBSERVABILITY & AUDIT RECORDING            │
       │  • LLM Logs & MCP Logs: Full prompts, outputs, tokens, TTFT    │
       │  • Dashboard: Realtime latency percentiles (p95) & total spend │
       │  • Connectors: Streaming push to Datadog, Kafka, and BigQuery  │
       │  • Audit Logs: Immutable before/after JSON diffs of admin ops  │
       └────────────────────────────────────────────────────────────────┘
```

---

# 2. Comprehensive Pillars & Features Inventory
### All 40 Features Deep-Dive (Thanglish + English)

## Pillar: Observability & Telemetry — Observability (Kangaanippu & Seyalthiran Paguppaayvu)
*Company-la nadakkura ellam AI transactions, cost, latency, token spend, matrum error logs-ah real-time-la track panni external monitoring tools (Datadog, Kafka) kooda connect pandra control plane.*

<a name='obs_dashboard'></a>
### Dashboard — Dashboard (Main Metrics & Analytics Cockpit)
**UI Route:** `/workspace/dashboard`

#### 👤 Non-Tech Perspective (Makkal Puriyura Eliya Vilakkam)
- **Uruvagam (Analogy):** Vimanathoda Cockpit allathu luxury car speedometer dashboard mathiri.
- **Vilakkam (Explanation):** Car ottum pothu speed, petrol level, engine condition ore meter-la theriyura mathiri, company-oda total AI spend, ethana lakh requests vandhathu, entha AI model fast-ah irukku, entha team athigama spend pandranga nu ore glance-la real-time graphs vazhiya pakkalam.
- **Business Value (Vaniga Payan):** Immediate budget transparency, cost spike prevention, and executive performance reporting.

#### 💻 Tech Perspective (Technical Architecture)
- **Backend Architecture:** WebSocket connection (`useWebSocket`) synchronized with TanStack Query. FastHTTP lock-free atomic counters (sync/atomic) aggregate time-series buckets into PostgreSQL. Computes p50, p90, p95, p99 latencies and Time-To-First-Token (TTFT).
- **Backend Endpoints:**
  * `GET /api/v1/dashboard/stats`
  * `GET /api/v1/dashboard/histogram`
  * `WS /api/v1/ws/dashboard`

#### 🖥️ Screen Layout & Interactive Elements (Thirai Koorugal)
**1. Melpura Koorugal (Top Bar Controls):**
- Time Range Selector (1h, 24h, 7d, 30d, Custom)
- Timezone Toggle (UTC / Local)
- Export Popover (CSV/JSON/PNG)
- Filter Sidebar Toggle

**2. Mathiya Koorugal & Tables (Tabs & Views):**
- Overview Tab (Total Spend, Requests, Tokens, p95 Latency)
- Provider Usage Tab
- Model Rankings Tab
- Dimension Rankings (x-uf-dim-*)
- MCP Tool Metrics

**3. Keezhpura Koorugal & Sheets (Bottom Elements & Slide-Overs):**
- Line vs Bar Chart Toggle
- Model Performance Leaderboard
- Live WebSocket Status Indicator

#### 🔗 Connections & Structure Map (Inaippugal)
- **Data-vai Perumidam (Receives From):** Aggregates raw telemetry from LLM Logs and FastHTTP Proxy.
- **Iyakkum Koorugal (Triggers & Affects):** Alerts finance managers and provides data for Budget enforcement.

#### 💡 Production Use Case: CFO weekly review analyzing whether the company is staying within the $20,000 monthly AI budget.

---

<a name='obs_llm_logs'></a>
### LLM Logs — LLM Logs (AI Request & Response Transaction Ledger)
**UI Route:** `/workspace/logs`

#### 👤 Non-Tech Perspective (Makkal Puriyura Eliya Vilakkam)
- **Uruvagam (Analogy):** Bank passbook statement allathu CCTV footage log book mathiri.
- **Vilakkam (Explanation):** Customers and employees AI kitta enna kelvi kettanga, AI enna bathil sonnathu, ethana tokens aachu, evlo dollar bill aachu nu second-by-second capture seiyura complete transaction ledger.
- **Business Value (Vaniga Payan):** 100% auditability, prompt debugging, compliance evidence, and customer dispute resolution.

#### 💻 Tech Perspective (Technical Architecture)
- **Backend Architecture:** High-speed batch-insert pipeline into PostgreSQL `llm_logs` table. Stores prompt text, model response, TTFT, token usage, status codes, and virtual key tags with sub-millisecond overhead.
- **Backend Endpoints:**
  * `GET /api/v1/logs`
  * `GET /api/v1/logs/{id}`
  * `POST /api/v1/logs/export`

#### 🖥️ Screen Layout & Interactive Elements (Thirai Koorugal)
**1. Melpura Koorugal (Top Bar Controls):**
- Search Input (Prompt/Response query)
- Column Visibility Picker
- Export Button (CSV/JSON)
- Auto-Refresh Dropdown

**2. Mathiya Koorugal & Tables (Tabs & Views):**
- Logs Table: Status Code, Model, Latency ms, Total Tokens, Spend $, Virtual Key, User ID, Timestamp

**3. Keezhpura Koorugal & Sheets (Bottom Elements & Slide-Overs):**
- Log Detail Sheet: Formatted Message Tree, Raw Headers, Guardrail Verdicts, Raw JSON Copy Button

#### 🔗 Connections & Structure Map (Inaippugal)
- **Data-vai Perumidam (Receives From):** Intercepts all calls passing through FastHTTP Proxy Gateway.
- **Iyakkum Koorugal (Triggers & Affects):** Feeds live data into Dashboard, Connectors, and Budgets & Limits.

#### 💡 Production Use Case: Customer support team debugging why an AI agent gave an incorrect shipping estimate to a VIP customer.

---

<a name='obs_mcp_logs'></a>
### MCP Logs — MCP Logs (Autonomous Agent Tool Call Audit)
**UI Route:** `/workspace/mcp-logs`

#### 👤 Non-Tech Perspective (Makkal Puriyura Eliya Vilakkam)
- **Uruvagam (Analogy):** Factory supervisor duty register mathiri.
- **Vilakkam (Explanation):** AI Agent thaanaga mudiveduthu company database-ah paathucha, email anupucha, file-ah delete pannucha nu AI seitha ovvoru external action-aiyum monitor seiyura tool execution audit book.
- **Business Value (Vaniga Payan):** Autonomous agent accountability, security verification, and third-party API call monitoring.

#### 💻 Tech Perspective (Technical Architecture)
- **Backend Architecture:** Model Context Protocol (MCP) JSON-RPC 2.0 frame capture engine. Records tool names, arguments, execution duration, and stdout/stderr outputs across stdio and SSE transports.
- **Backend Endpoints:**
  * `GET /api/v1/mcp/logs`
  * `GET /api/v1/mcp/logs/{id}`

#### 🖥️ Screen Layout & Interactive Elements (Thirai Koorugal)
**1. Melpura Koorugal (Top Bar Controls):**
- Filter by MCP Server
- Tool Name Search
- Execution Status Filter (Success/Fail/Timeout)

**2. Mathiya Koorugal & Tables (Tabs & Views):**
- MCP Logs Table: Server Name, Tool Executed, Duration ms, Payload Size KB, Invocation Status

**3. Keezhpura Koorugal & Sheets (Bottom Elements & Slide-Overs):**
- Tool Execution Drawer: Input JSON Arguments, Tool Response JSON, Error Stack Trace

#### 🔗 Connections & Structure Map (Inaippugal)
- **Data-vai Perumidam (Receives From):** Intercepts tool calls executed in MCP Gateway.
- **Iyakkum Koorugal (Triggers & Affects):** Feeds tool reliability statistics into MCP Gateway and Dashboard.

#### 💡 Production Use Case: Verifying that an automated sales agent only searched the CRM database and did not modify any customer records.

---

<a name='obs_browser_ai'></a>
### Browser AI — Browser AI (Employee Web ChatGPT DLP Proxy)
**UI Route:** `/workspace/browser-ai`

#### 👤 Non-Tech Perspective (Makkal Puriyura Eliya Vilakkam)
- **Uruvagam (Analogy):** Office entrance security guard & bag scanner mathiri.
- **Vilakkam (Explanation):** Employees company laptop-la web ChatGPT allathu Claude use pannum pothu, company passwords, client details, allathu confidential code-ah copy-paste panni leak seiyatha mathiri thadukkura security wall.
- **Business Value (Vaniga Payan):** Prevents corporate data leaks to public web AI services without having to ban AI tools for employees.

#### 💻 Tech Perspective (Technical Architecture)
- **Backend Architecture:** Client-side mitmproxy daemon intercepting web traffic to `chatgpt.com` and `claude.ai`. Inspects clipboard paste events and file uploads using local regex and Presidio DLP algorithms.
- **Backend Endpoints:**
  * `GET /api/v1/browser-ai/sessions`
  * `GET /api/v1/browser-ai/violations`
  * `POST /api/v1/browser-ai/sync`

#### 🖥️ Screen Layout & Interactive Elements (Thirai Koorugal)
**1. Melpura Koorugal (Top Bar Controls):**
- Proxy Status Badge (Active/Inactive)
- Policy Switcher (Block / Redact / Audit)
- Extension Heartbeat

**2. Mathiya Koorugal & Tables (Tabs & Views):**
- Intercepted Sessions Tab
- DLP Violations Tab
- Attachment Scans Tab

**3. Keezhpura Koorugal & Sheets (Bottom Elements & Slide-Overs):**
- Violation Incident Viewer: Diff showing original confidential text vs redacted asterisk text

#### 🔗 Connections & Structure Map (Inaippugal)
- **Data-vai Perumidam (Receives From):** Employee browser extensions and local proxy daemons.
- **Iyakkum Koorugal (Triggers & Affects):** Blocks confidential pastes and logs security violations to Audit Logs.

#### 💡 Production Use Case: Employee accidentally copying a customer's credit card number into ChatGPT gets warned and the data is masked automatically.

---

<a name='obs_connectors'></a>
### Connectors — Connectors (External Observability & Telemetry Pipelines)
**UI Route:** `/workspace/observability`

#### 👤 Non-Tech Perspective (Makkal Puriyura Eliya Vilakkam)
- **Uruvagam (Analogy):** Water pipeline network mathiri (Thanniya thevaiyana tank-ku anuppura mathiri).
- **Vilakkam (Explanation):** UnifAI-la create aagura AI logs and metrics-ah company-oda main monitoring tools (Datadog, Splunk, Dynatrace, Apache Kafka, Google BigQuery)-ku automatic-ah push seiyura export pipelines.
- **Business Value (Vaniga Payan):** Zero data silos; seamless integration with enterprise security and billing infrastructure.

#### 💻 Tech Perspective (Technical Architecture)
- **Backend Architecture:** Async streaming telemetry push engine. Batches events into configurable queue workers with retry backoff and Dead Letter Queue (DLQ). Pushes via OpenTelemetry (OTel), HTTP webhooks, or Kafka producers.
- **Backend Endpoints:**
  * `GET /api/v1/observability/connectors`
  * `POST /api/v1/observability/connectors`
  * `DELETE /api/v1/observability/connectors/{id}`

#### 🖥️ Screen Layout & Interactive Elements (Thirai Koorugal)
**1. Melpura Koorugal (Top Bar Controls):**
- Add Connector Button
- Connector Type Filter (Datadog, Kafka, BigQuery, OTel)
- Health Indicator

**2. Mathiya Koorugal & Tables (Tabs & Views):**
- Connectors List Cards with endpoint URL, flush interval ms, and delivery status badge

**3. Keezhpura Koorugal & Sheets (Bottom Elements & Slide-Overs):**
- AddConnectorDialog: Endpoint URL, Bearer Token, Batch Size (100-5000), Send Test Ping Button

#### 🔗 Connections & Structure Map (Inaippugal)
- **Data-vai Perumidam (Receives From):** Subscribes to FastHTTP Proxy event stream and LLM Logs.
- **Iyakkum Koorugal (Triggers & Affects):** Streams enterprise telemetry to corporate BigQuery and Kafka topics.

#### 💡 Production Use Case: Streaming every AI transaction into corporate BigQuery for monthly automated billing invoices.

---

<a name='obs_logs_settings'></a>
### Logs Settings — Logs Settings (Log Governance & Retention Policies)
**UI Route:** `/workspace/config/logging`

#### 👤 Non-Tech Perspective (Makkal Puriyura Eliya Vilakkam)
- **Uruvagam (Analogy):** Office record room archival & paper shredding rules mathiri.
- **Vilakkam (Explanation):** Pazhaya AI logs-ah ethana naalaikku apram automatic-ah delete pannanum (e.g. 30 days retention), yaarachum PII data anupuna epdi mask pannanum, cold storage S3-ku epdi move pannanum nu set pandra control room.
- **Business Value (Vaniga Payan):** 100% GDPR, HIPAA, and SOC-2 data compliance; saves huge database storage costs.

#### 💻 Tech Perspective (Technical Architecture)
- **Backend Architecture:** Log lifecycle engine. Schedules automated PostgreSQL partition drops, triggers `VACUUM` maintenance, manages multi-part uploads to AWS S3 Glacier, and controls traffic sampling rates (1% to 100%).
- **Backend Endpoints:**
  * `GET /api/v1/config/logging`
  * `PUT /api/v1/config/logging`
  * `POST /api/v1/config/logging/purge`

#### 🖥️ Screen Layout & Interactive Elements (Thirai Koorugal)
**1. Melpura Koorugal (Top Bar Controls):**
- Master Logging Switch
- Data Retention Input (Days)
- Traffic Sampling Slider (0-100%)

**2. Mathiya Koorugal & Tables (Tabs & Views):**
- Privacy Controls: Mask PII Switch, Store Prompts Toggle, S3 Cold Storage Backup Bucket input

**3. Keezhpura Koorugal & Sheets (Bottom Elements & Slide-Overs):**
- Purge Expired Logs Now Button
- Save Logging Settings Button

#### 🔗 Connections & Structure Map (Inaippugal)
- **Data-vai Perumidam (Receives From):** Administrative configuration inputs.
- **Iyakkum Koorugal (Triggers & Affects):** Enforces storage cleanup in PostgreSQL and automated masking in LLM Logs.

#### 💡 Production Use Case: Setting a strict 30-day retention rule so user chat history is permanently wiped to comply with European privacy laws.

---

## Pillar: Models & Traffic Control — Models (AI Model Catalog, Routing & Resilience)
*Company-oda complete AI models inventory, vendor API keys, smart routing rules, cost triage, and zero-downtime failover systems.*

<a name='mod_catalog'></a>
### Model Catalog — Model Catalog (AI Models Inventory & Menu)
**UI Route:** `/workspace/model-catalog`

#### 👤 Non-Tech Perspective (Makkal Puriyura Eliya Vilakkam)
- **Uruvagam (Analogy):** Amazon product catalog allathu hotel menu card mathiri.
- **Vilakkam (Explanation):** Company-la configure panni irukkura ellam AI models (GPT-4o, Claude 3.5 Sonnet, Gemini 1.5, Llama 3) list, athoda context length, 24-hour traffic, total cost ellame ore idathula pakkalam.
- **Business Value (Vaniga Payan):** Eliminates duplicate model usage; standardizes AI models across teams; provides full pricing visibility.

#### 💻 Tech Perspective (Technical Architecture)
- **Backend Architecture:** FastHTTP model registry endpoint (`/api/v1/models/catalog`). TanStack Query client caching with real-time token metrics aggregation. Ingests 24h usage telemetry from PostgreSQL.
- **Backend Endpoints:**
  * `GET /api/v1/models/catalog`
  * `GET /api/v1/models/attributes`
  * `PATCH /api/v1/models/{id}/attributes`

#### 🖥️ Screen Layout & Interactive Elements (Thirai Koorugal)
**1. Melpura Koorugal (Top Bar Controls):**
- 4 Summary Cards (Total Providers, Total Models, Requests 24h, Cost 24h)
- Provider Filter Dropdown
- Overview vs Attributes Tabs

**2. Mathiya Koorugal & Tables (Tabs & Views):**
- Overview Table: Provider, Models Used, Traffic 24h, Cost 24h
- Attributes Table: Model ID, Display Name, Pricing, Context Window, Output Tokens

**3. Keezhpura Koorugal & Sheets (Bottom Elements & Slide-Overs):**
- AttributeSheet: Edit display name, description, context length, modality tags

#### 🔗 Connections & Structure Map (Inaippugal)
- **Data-vai Perumidam (Receives From):** Model Providers and LLM Logs.
- **Iyakkum Koorugal (Triggers & Affects):** Supplies model options to Routing Rules and Complexity Router.

#### 💡 Production Use Case: Auditing and deprecating older, expensive models like GPT-4 32k in favor of cheaper GPT-4o-mini.

---

<a name='mod_providers'></a>
### Model Providers — Model Providers (AI Vendor Credentials & Gateway Settings)
**UI Route:** `/workspace/providers`

#### 👤 Non-Tech Perspective (Makkal Puriyura Eliya Vilakkam)
- **Uruvagam (Analogy):** Telecom SIM card & network switchboard mathiri (Airtel, Jio, Vodafone connections).
- **Vilakkam (Explanation):** OpenAI, Anthropic, AWS Bedrock, Google Vertex AI, Azure OpenAI, Groq, Ollama aagiya companies-oda connect aaga thevaiyana API keys, secret credentials, network speed, timeout settings configure pandra control panel.
- **Business Value (Vaniga Payan):** Zero vendor lock-in; secure central key vault; support for private on-premise AI models.

#### 💻 Tech Perspective (Technical Architecture)
- **Backend Architecture:** Multi-vendor credential management and FastHTTP connection pool. Configures custom base URLs, proxy tunnels, exponential backoff retries, and raw payload flags. Instant connection ping testing.
- **Backend Endpoints:**
  * `GET /api/v1/providers`
  * `POST /api/v1/providers`
  * `PATCH /api/v1/providers/{name}`
  * `DELETE /api/v1/providers/{name}`

#### 🖥️ Screen Layout & Interactive Elements (Thirai Koorugal)
**1. Melpura Koorugal (Top Bar Controls):**
- Provider Sidebar with status badges (Active/Warning/Error)
- Add Provider Dropdown (+ Add Custom Provider)

**2. Mathiya Koorugal & Tables (Tabs & Views):**
- Provider Header: Icon, Name, Edit Provider Config button, Delete button
- ModelProviderKeysTableView: Key Name, Masked Key Secret, Quota Limit, Ping Test button

**3. Keezhpura Koorugal & Sheets (Bottom Elements & Slide-Overs):**
- ProviderConfigSheet: Concurrency limits, buffer size, network timeouts, retry delays, proxy settings
- AddCustomProviderSheet: Custom base URL and Keyless mode toggle

#### 🔗 Connections & Structure Map (Inaippugal)
- **Data-vai Perumidam (Receives From):** Admin inputs.
- **Iyakkum Koorugal (Triggers & Affects):** Powers outbound AI traffic in FastHTTP Proxy and feeds Routing Rules.

#### 💡 Production Use Case: Safely rotating production OpenAI keys and adding a local private Ollama instance for sensitive data.

---

<a name='mod_limits'></a>
### Budgets & Limits — Budgets & Limits (Cost Caps & Token Rate Limits)
**UI Route:** `/workspace/model-limits`

#### 👤 Non-Tech Perspective (Makkal Puriyura Eliya Vilakkam)
- **Uruvagam (Analogy):** Credit card daily & monthly spend limit mathiri.
- **Vilakkam (Explanation):** AI use panna panna bill laatchakanakula pogama irukka, ovvoru team-kum, user-kum, athavathu ovvoru AI model-kum monthly budget ($500) allathu daily token limit set pandra edham. Limit thanduna automatic-ah request stop aagidum.
- **Business Value (Vaniga Payan):** Eliminates bill shock; guarantees 100% budget compliance across departments.

#### 💻 Tech Perspective (Technical Architecture)
- **Backend Architecture:** High-throughput token bucket rate limiter and budget enforcer middleware. Atomic Redis/PostgreSQL counters (`INCRBY`). Pre-flight evaluation rejects requests with HTTP 429 or routes to a cheaper fallback.
- **Backend Endpoints:**
  * `GET /api/v1/governance/model-limits`
  * `POST /api/v1/governance/model-limits`
  * `DELETE /api/v1/governance/model-limits/{id}`

#### 🖥️ Screen Layout & Interactive Elements (Thirai Koorugal)
**1. Melpura Koorugal (Top Bar Controls):**
- Create Model Limit Button
- Search Bar
- Provider Filter
- Scope Filter (Global, Virtual Key, User, Team)

**2. Mathiya Koorugal & Tables (Tabs & Views):**
- Model Limits Table: Scope Badge, Target Entity, Provider, Model, Budget Progress Bar $, Token Progress Bar, Reset Duration

**3. Keezhpura Koorugal & Sheets (Bottom Elements & Slide-Overs):**
- ModelLimitSheet: Scope Selector, Target pickers, Max Budget $, Max Tokens, Reset Duration, Threshold Alert Rules (80% warning, 100% hard block)

#### 🔗 Connections & Structure Map (Inaippugal)
- **Data-vai Perumidam (Receives From):** Rates from Pricing Overrides and live spend from LLM Logs.
- **Iyakkum Koorugal (Triggers & Affects):** Blocks or reroutes calls in FastHTTP Proxy when quota is exhausted.

#### 💡 Production Use Case: Giving intern developers a strict $50/month cap while granting the production app an elastic $5,000 budget.

---

<a name='mod_routing'></a>
### Routing Rules — Routing Rules (Intelligent Traffic Steering & Fallbacks)
**UI Route:** `/workspace/routing-rules`

#### 👤 Non-Tech Perspective (Makkal Puriyura Eliya Vilakkam)
- **Uruvagam (Analogy):** Railway track switcher mathiri (Train-ah thevaikku etha track-la thiruppura mathiri).
- **Vilakkam (Explanation):** Oru customer request varum pothu, athu entha AI model-ku poganum nu rules poduvom. Example: Premium user-ku GPT-4o, Free user-ku Claude 3.5 Haiku nu condition base panni smart-ah route pandrathu.
- **Business Value (Vaniga Payan):** Custom user experience; cost optimization based on customer value; zero downtime via fallback chains.

#### 💻 Tech Perspective (Technical Architecture)
- **Backend Architecture:** CEL (Common Expression Language) evaluation engine written in Go. Evaluates conditions against request headers (`x-uf-*`), prompt metadata, user roles, and token counts to dispatch to prioritized target pools.
- **Backend Endpoints:**
  * `GET /api/v1/routing-rules`
  * `POST /api/v1/routing-rules`
  * `PATCH /api/v1/routing-rules/{id}`
  * `DELETE /api/v1/routing-rules/{id}`

#### 🖥️ Screen Layout & Interactive Elements (Thirai Koorugal)
**1. Melpura Koorugal (Top Bar Controls):**
- Create Routing Rule Button
- Search Input
- Priority Sort

**2. Mathiya Koorugal & Tables (Tabs & Views):**
- Routing Rules Table: Rule Name, Priority Badge, CEL Condition, Target Model/Provider, Enabled Switch, Actions
- Visual Rule Tree View

**3. Keezhpura Koorugal & Sheets (Bottom Elements & Slide-Overs):**
- RoutingRuleSheet: Rule Name, Priority slider (1-100), Visual/Raw CEL Condition Builder, Target Provider/Model, Fallback Priority list

#### 🔗 Connections & Structure Map (Inaippugal)
- **Data-vai Perumidam (Receives From):** FastHTTP Proxy requests and Complexity Router tiers.
- **Iyakkum Koorugal (Triggers & Affects):** Directs traffic to upstream Model Providers and triggers Circuit Breaker on failure.

#### 💡 Production Use Case: Routing all European requests to EU-hosted Azure OpenAI instances for strict GDPR data residency.

---

<a name='mod_complexity'></a>
### Complexity Router — Complexity Router (AI Query Triage & Cost Optimizer)
**UI Route:** `/workspace/complexity-router`

#### 👤 Non-Tech Perspective (Makkal Puriyura Eliya Vilakkam)
- **Uruvagam (Analogy):** Hospital Triage System mathiri (Fever-ku junior doctor, surgery-ku specialist mathiri).
- **Vilakkam (Explanation):** Simple-ana kelvi ('Hi', 'What is Python?') ketta costly GPT-4o thevailla, athukku fast & cheap-ana GPT-4o-mini pothum. Aana periya complex coding allathu math problem ketta mattum o1 allathu Claude Opus-ku automatic-ah anupum. Ithanaala 70% AI bill micham aagum!
- **Business Value (Vaniga Payan):** Saves up to 70% in monthly AI costs with zero compromise on quality.

#### 💻 Tech Perspective (Technical Architecture)
- **Backend Architecture:** Multi-factor prompt complexity analysis engine. Computes a continuous complexity score (0.0 to 1.0) using token length heuristics, vocabulary entropy, code regexes (`def`, `class`, `function`), and keyword weighting. Maps into 4 tiers: `SIMPLE`, `MEDIUM`, `COMPLEX`, `REASONING`.
- **Backend Endpoints:**
  * `GET /api/v1/governance/complexity-analyzer`
  * `PUT /api/v1/governance/complexity-analyzer`
  * `POST /api/v1/governance/complexity-analyzer/reset`

#### 🖥️ Screen Layout & Interactive Elements (Thirai Koorugal)
**1. Melpura Koorugal (Top Bar Controls):**
- Save Configuration Button
- Reset to Defaults Button (RotateCcw)
- Docs Link

**2. Mathiya Koorugal & Tables (Tabs & Views):**
- Progressive okLCH Palette Bar (Simple, Medium, Complex, Reasoning)
- Tier Boundary Inputs (Simple->Med, Med->Comp, Comp->Reason)
- Keyword Lists (TagInput for Code, Reasoning, Simple)

**3. Keezhpura Koorugal & Sheets (Bottom Elements & Slide-Overs):**
- Tier Target Model Mappings (Assign default model per tier)
- Interactive Prompt Test Sandbox

#### 🔗 Connections & Structure Map (Inaippugal)
- **Data-vai Perumidam (Receives From):** Intercepts incoming requests in FastHTTP Proxy before Routing Rules.
- **Iyakkum Koorugal (Triggers & Affects):** Selects appropriate model tier and logs classification in LLM Logs.

#### 💡 Production Use Case: Customer support bot where 85% routine queries go to lightweight models and 15% complex technical queries go to reasoning models.

---

<a name='mod_circuit_breaker'></a>
### Circuit Breaker — Circuit Breaker (Outage Protection & Auto-Failover)
**UI Route:** `/workspace/circuit-breaker`

#### 👤 Non-Tech Perspective (Makkal Puriyura Eliya Vilakkam)
- **Uruvagam (Analogy):** Veetla irukkura Electric MCB / Fuse mathiri.
- **Vilakkam (Explanation):** OpenAI allathu Anthropic server crash aanaallathu rate limit aagi error vantha, user-ku error screen kaatama, automatic-ah fraction of second-la backup model-ku (e.g. AWS Bedrock allathu Azure)-ku switch panni 24x7 non-stop-ah vela seiya vaikkum.
- **Business Value (Vaniga Payan):** 99.99% Enterprise High Availability; zero customer-facing downtime during AI vendor outages.

#### 💻 Tech Perspective (Technical Architecture)
- **Backend Architecture:** Distributed Circuit Breaker finite state machine (Closed -> Open -> Half-Open). Monitored via real-time polling every 8 seconds (`pollingInterval: 8000ms`). Detects response signals (HTTP 429/503, `x-ratelimit-remaining: 0`). Instantly redirects calls to fallback provider with automated cooldown probing.
- **Backend Endpoints:**
  * `GET /api/v1/circuit-breaker/policies`
  * `POST /api/v1/circuit-breaker/policies`
  * `PUT /api/v1/circuit-breaker/policies/{name}`
  * `GET /api/v1/circuit-breaker/state`
  * `POST /api/v1/circuit-breaker/policies/{name}/reset`

#### 🖥️ Screen Layout & Interactive Elements (Thirai Koorugal)
**1. Melpura Koorugal (Top Bar Controls):**
- Header with Shield Icon
- Create Policy Button

**2. Mathiya Koorugal & Tables (Tabs & Views):**
- Circuit Breaker Table: Policy Name, Primary Provider/Model, Fallback Provider/Model, Trigger Condition, Cooldown, State Badge (Closed/Open/Half-Open), Actions

**3. Keezhpura Koorugal & Sheets (Bottom Elements & Slide-Overs):**
- Circuit Policy Dialog: Policy Name, Primary/Fallback comboboxes, Response Header Signal matchers, Cooldown duration
- Manual Circuit Reset Button (RotateCcw)

#### 🔗 Connections & Structure Map (Inaippugal)
- **Data-vai Perumidam (Receives From):** Monitors HTTP response headers and errors from FastHTTP Proxy.
- **Iyakkum Koorugal (Triggers & Affects):** Reroutes failed requests and notifies Alert Channels.

#### 💡 Production Use Case: During peak hours, when OpenAI returns HTTP 429 Too Many Requests, traffic automatically pivots to AWS Bedrock with zero disruption.

---

<a name='mod_pricing_overrides'></a>
### Pricing Overrides — Pricing Overrides (Custom Enterprise Rates & Discounts)
**UI Route:** `/workspace/custom-pricing/overrides`

#### 👤 Non-Tech Perspective (Makkal Puriyura Eliya Vilakkam)
- **Uruvagam (Analogy):** Special corporate discount allathu wholesale negotiated price contract mathiri.
- **Vilakkam (Explanation):** OpenAI website-la 1 million token-ku $5 nu irunthaalum, unga company-ku special enterprise discount allathu committed spend agreement iruntha, antha custom rate-ah inga enter pannikalam. Athuku thagundha mathiri unga internal dashboard-la exact real spend calculate aagum.
- **Business Value (Vaniga Payan):** 100% accurate financial chargeback and departmental billing based on actual negotiated contracts.

#### 💻 Tech Perspective (Technical Architecture)
- **Backend Architecture:** Multi-tier hierarchical pricing precedence engine: (1) Virtual Key Override -> (2) User/Team Override -> (3) Provider Global Override -> (4) Default Provider Catalog. Calculates prompt tokens, cached input tokens, output tokens, reasoning tokens, and fixed invocation fees.
- **Backend Endpoints:**
  * `GET /api/v1/pricing/overrides`
  * `POST /api/v1/pricing/overrides`
  * `PUT /api/v1/pricing/overrides/{id}`
  * `DELETE /api/v1/pricing/overrides/{id}`

#### 🖥️ Screen Layout & Interactive Elements (Thirai Koorugal)
**1. Melpura Koorugal (Top Bar Controls):**
- Add Pricing Override Button
- Scope Filter (Global, Virtual Key, Team)
- Search Input

**2. Mathiya Koorugal & Tables (Tabs & Views):**
- Pricing Overrides Table: Scope Badge, Target Entity, Provider, Model, Input Cost $/1M, Cached Input Cost, Output Cost $/1M, Request Fee, Actions

**3. Keezhpura Koorugal & Sheets (Bottom Elements & Slide-Overs):**
- PricingOverrideSheet: Scope, Provider, Model, and PricingFieldSelector inputs for granular token pricing

#### 🔗 Connections & Structure Map (Inaippugal)
- **Data-vai Perumidam (Receives From):** Finance administrators.
- **Iyakkum Koorugal (Triggers & Affects):** Feeds real-time spend calculations into Dashboard, LLM Logs, and Budgets & Limits.

#### 💡 Production Use Case: Applying an AWS 20% committed spend discount to Bedrock Claude models so internal reporting matches cloud invoices.

---

<a name='mod_settings'></a>
### Model Settings — Model Settings (Master Catalog Sync & Recursion Guard)
**UI Route:** `/workspace/custom-pricing`

#### 👤 Non-Tech Perspective (Makkal Puriyura Eliya Vilakkam)
- **Uruvagam (Analogy):** Global system clock & master registry synchronizer mathiri.
- **Vilakkam (Explanation):** Market-la puthu puthu AI models varum pothu, athoda official pricing automatic-ah download aagi update aaga thevaiyana master website link, sync frequency (24 hours), mathum routing rules-la infinite loop vanthu server hang aagidama thadukkura max depth settings configure pandra edham.
- **Business Value (Vaniga Payan):** Zero-maintenance operations; automated price drop ingestion without code deployments.

#### 💻 Tech Perspective (Technical Architecture)
- **Backend Architecture:** Core configuration manager in PostgreSQL (`framework_config`, `client_config`). Orchestrates asynchronous cron workers to fetch remote pricing datasheets (CSV/JSON). Enforces `routing_chain_max_depth` to prevent circular fallback loops.
- **Backend Endpoints:**
  * `GET /api/v1/config/core`
  * `PUT /api/v1/config/core`
  * `POST /api/v1/config/pricing/sync`

#### 🖥️ Screen Layout & Interactive Elements (Thirai Koorugal)
**1. Melpura Koorugal (Top Bar Controls):**
- Header Title
- Dirty State Tracker highlighting unsaved changes

**2. Mathiya Koorugal & Tables (Tabs & Views):**
- ModelSettingsView: Pricing Datasheet URL, Pricing Sync Interval (Hours), Model Parameters URL, Routing Chain Max Depth (slider/input)

**3. Keezhpura Koorugal & Sheets (Bottom Elements & Slide-Overs):**
- Force Pricing Sync Now Button (with loading spinner)
- Save Configuration Button

#### 🔗 Connections & Structure Map (Inaippugal)
- **Data-vai Perumidam (Receives From):** Admin inputs and remote pricing feeds.
- **Iyakkum Koorugal (Triggers & Affects):** Updates foundational pricing for Model Catalog and prevents routing recursion loops.

#### 💡 Production Use Case: Instantly ingesting OpenAI's latest price reduction across 30 enterprise models with a single click of 'Force Pricing Sync Now'.

---

## Pillar: MCP Gateway & Tool Execution — MCP Gateway (Model Context Protocol & Agent Tools)
*Autonomous AI Agents company-oda internal databases, APIs, codebases, and external SaaS tools kooda interact panna thevaiyana standardized gateway.*

<a name='mcp_catalog'></a>
### MCP Catalog — MCP Catalog (Tool Registry & App Store)
**UI Route:** `/workspace/mcp-registry`

#### 👤 Non-Tech Perspective (Makkal Puriyura Eliya Vilakkam)
- **Uruvagam (Analogy):** App Store allathu Google Play Store mathiri.
- **Vilakkam (Explanation):** AI Agents use panna koodiya ellam certified tools (GitHub MCP, PostgreSQL MCP, Slack MCP, Google Drive MCP, Puppeteer Web Scraper) list irukkura marketplace. Single click-la puthu tool install pannikalam.
- **Business Value (Vaniga Payan):** Fast-tracks AI agent deployment; verified secure tool marketplace; zero boilerplate integration.

#### 💻 Tech Perspective (Technical Architecture)
- **Backend Architecture:** Curated MCP registry client. Fetches certified tool schemas, version tags, environment variable templates, and execution commands (stdio binary or Docker container) from central repositories.
- **Backend Endpoints:**
  * `GET /api/v1/mcp/registry`
  * `POST /api/v1/mcp/registry/install`

#### 🖥️ Screen Layout & Interactive Elements (Thirai Koorugal)
**1. Melpura Koorugal (Top Bar Controls):**
- Search Catalog Input
- Category Filter (Databases, Version Control, Communication, DevTools)
- Installed vs Available Filter

**2. Mathiya Koorugal & Tables (Tabs & Views):**
- Tool Cards Grid: Icon, Tool Name, Description, Verified Badge, Version, 'Install' button

**3. Keezhpura Koorugal & Sheets (Bottom Elements & Slide-Overs):**
- InstallToolDialog: Environment variable inputs (API keys, connection strings) and transport mode selector

#### 🔗 Connections & Structure Map (Inaippugal)
- **Data-vai Perumidam (Receives From):** External MCP package repositories.
- **Iyakkum Koorugal (Triggers & Affects):** Deploys tools into Installed Servers.

#### 💡 Production Use Case: Installing the PostgreSQL MCP tool to let internal analytics AI query corporate sales data safely.

---

<a name='mcp_servers'></a>
### Installed Servers — Installed Servers (Active MCP Instances & Health)
**UI Route:** `/workspace/mcp-gateway`

#### 👤 Non-Tech Perspective (Makkal Puriyura Eliya Vilakkam)
- **Uruvagam (Analogy):** Computer-la install aana software apps dashboard mathiri.
- **Vilakkam (Explanation):** Company-kulla ippo active-ah run aagikittu irukura MCP tool servers list. Entha server online-la irukku, ethu crashed, ethana tools antha server tharuthu nu paathu restart allathu configure pandra idham.
- **Business Value (Vaniga Payan):** Tool availability monitoring; instant recovery from crashed tool daemons; lifecycle control.

#### 💻 Tech Perspective (Technical Architecture)
- **Backend Architecture:** MCP Server lifecycle daemon supervisor. Manages child OS processes (`stdio`) or HTTP Server-Sent Events (`SSE`) endpoints. Performs automatic process health checks, restarts crashed servers, and registers exported tool schemas.
- **Backend Endpoints:**
  * `GET /api/v1/mcp/servers`
  * `POST /api/v1/mcp/servers/{id}/restart`
  * `DELETE /api/v1/mcp/servers/{id}`

#### 🖥️ Screen Layout & Interactive Elements (Thirai Koorugal)
**1. Melpura Koorugal (Top Bar Controls):**
- Add Server Button
- Search Servers
- Health Filter (Running, Degraded, Stopped)

**2. Mathiya Koorugal & Tables (Tabs & Views):**
- Installed Servers Table: Server Name, Transport (stdio/SSE), Status Badge, Tool Count, Memory Usage, Actions (Restart, Edit, Delete)

**3. Keezhpura Koorugal & Sheets (Bottom Elements & Slide-Overs):**
- ServerConfigSheet: Command arguments, working directory, environment variables, timeout limits

#### 🔗 Connections & Structure Map (Inaippugal)
- **Data-vai Perumidam (Receives From):** MCP Catalog installations.
- **Iyakkum Koorugal (Triggers & Affects):** Exposes tools to Tool Groups and logs calls to MCP Logs.

#### 💡 Production Use Case: Restarting the GitHub MCP server daemon after generating a new personal access token.

---

<a name='mcp_sessions'></a>
### MCP Sessions — Sessions (Live Stateful Agent Connections)
**UI Route:** `/workspace/mcp-sessions`

#### 👤 Non-Tech Perspective (Makkal Puriyura Eliya Vilakkam)
- **Uruvagam (Analogy):** Active phone calls allathu live chat sessions list mathiri.
- **Vilakkam (Explanation):** Ippo entha entha AI agents live-ah company tools kooda connect panni vela senjukittu irukku nu kaatara active connection monitor. Thevaillatha session-ah force-ah terminate pannalam.
- **Business Value (Vaniga Payan):** Prevents runaway autonomous agents; immediate containment of malfunctioning automation scripts.

#### 💻 Tech Perspective (Technical Architecture)
- **Backend Architecture:** Stateful session tracker for SSE and WebSocket MCP connections. Tracks session ID, client IP, connected agent identity, active context windows, and tool execution lock state.
- **Backend Endpoints:**
  * `GET /api/v1/mcp/sessions`
  * `DELETE /api/v1/mcp/sessions/{id}`

#### 🖥️ Screen Layout & Interactive Elements (Thirai Koorugal)
**1. Melpura Koorugal (Top Bar Controls):**
- Active Sessions Count Badge
- Kill All Sessions Emergency Button

**2. Mathiya Koorugal & Tables (Tabs & Views):**
- Sessions Table: Session ID, Connected Agent/User, Duration, Tools Invoked Count, Memory State, Actions (Terminate)

**3. Keezhpura Koorugal & Sheets (Bottom Elements & Slide-Overs):**
- Session Trace Modal: Live stream of JSON-RPC tool frames exchanged in this session

#### 🔗 Connections & Structure Map (Inaippugal)
- **Data-vai Perumidam (Receives From):** Live incoming agent connections.
- **Iyakkum Koorugal (Triggers & Affects):** Can terminate active sessions to protect downstream infrastructure.

#### 💡 Production Use Case: Killing an agent session that entered an infinite loop repeatedly calling the Slack notification tool.

---

<a name='mcp_tool_groups'></a>
### Tool Groups — Tool Groups (Permission Bundles & Tool Access Control)
**UI Route:** `/workspace/mcp-tool-groups`

#### 👤 Non-Tech Perspective (Makkal Puriyura Eliya Vilakkam)
- **Uruvagam (Analogy):** Security clearance badge groups mathiri (Junior dev-ku read-only tools, Senior dev-ku write tools).
- **Vilakkam (Explanation):** Multiple tools-ah onna sethu bundle pannalam. Example: 'Read-Only Tools' bundle (view database, read files) allathu 'Production Tools' bundle (write database, send email). Virtual key-ku etha mathiri intha groups-ah assign pannikalam.
- **Business Value (Vaniga Payan):** Least-privilege security for autonomous AI; prevents AI from executing dangerous destructive commands.

#### 💻 Tech Perspective (Technical Architecture)
- **Backend Architecture:** Access control abstraction layer over MCP tool schemas. Maps Virtual Keys to permitted Tool Groups. Gateway filters out unpermitted tool definitions from the LLM prompt's system message dynamically.
- **Backend Endpoints:**
  * `GET /api/v1/mcp/tool-groups`
  * `POST /api/v1/mcp/tool-groups`
  * `PATCH /api/v1/mcp/tool-groups/{id}`

#### 🖥️ Screen Layout & Interactive Elements (Thirai Koorugal)
**1. Melpura Koorugal (Top Bar Controls):**
- Create Tool Group Button
- Search Groups

**2. Mathiya Koorugal & Tables (Tabs & Views):**
- Tool Groups Cards: Group Name, Description, Included Tools count, Assigned Virtual Keys count, Actions

**3. Keezhpura Koorugal & Sheets (Bottom Elements & Slide-Overs):**
- ToolGroupSheet: Group Name, Description, Interactive Tool Selector Checkboxes across all installed servers

#### 🔗 Connections & Structure Map (Inaippugal)
- **Data-vai Perumidam (Receives From):** Installed Servers tools.
- **Iyakkum Koorugal (Triggers & Affects):** Binds to Virtual Keys and Access Profiles.

#### 💡 Production Use Case: Restricting an intern's chatbot to only search internal documentation while preventing it from modifying the production database.

---

<a name='mcp_auth_config'></a>
### Auth Config — Auth Config (MCP Security & Client Tokens)
**UI Route:** `/workspace/mcp-auth-config`

#### 👤 Non-Tech Perspective (Makkal Puriyura Eliya Vilakkam)
- **Uruvagam (Analogy):** Security passport & digital signature verification mathiri.
- **Vilakkam (Explanation):** External agents and client software MCP Gateway-kulla connect aaga thevaiyana OAuth 2.0, Bearer token, and mutual TLS authentication settings configure pandra edham.
- **Business Value (Vaniga Payan):** Prevents unauthorized agents from connecting to internal enterprise tools.

#### 💻 Tech Perspective (Technical Architecture)
- **Backend Architecture:** MCP Gateway authentication middleware. Validates incoming connection credentials against OAuth 2.0 introspection endpoints, API keys, or mTLS client certificates before allowing tool execution.
- **Backend Endpoints:**
  * `GET /api/v1/mcp/auth-config`
  * `PUT /api/v1/mcp/auth-config`

#### 🖥️ Screen Layout & Interactive Elements (Thirai Koorugal)
**1. Melpura Koorugal (Top Bar Controls):**
- Master Auth Enforcement Toggle
- Save Auth Config Button

**2. Mathiya Koorugal & Tables (Tabs & Views):**
- Auth Settings Form: Allowed Auth Types (Bearer, mTLS, OAuth2), Token Expiration Duration, Whitelisted Client IPs

**3. Keezhpura Koorugal & Sheets (Bottom Elements & Slide-Overs):**
- Client Token Generator: Create dedicated secure connection tokens for trusted agent processes

#### 🔗 Connections & Structure Map (Inaippugal)
- **Data-vai Perumidam (Receives From):** Security administrators.
- **Iyakkum Koorugal (Triggers & Affects):** Authorizes or rejects incoming connections to MCP Gateway.

#### 💡 Production Use Case: Requiring mutual TLS certificates for all agent connections originating from external cloud environments.

---

<a name='mcp_settings'></a>
### Gateway Settings — Gateway Settings (MCP Engine Timeouts & Network Ports)
**UI Route:** `/workspace/mcp-settings`

#### 👤 Non-Tech Perspective (Makkal Puriyura Eliya Vilakkam)
- **Uruvagam (Analogy):** Factory master electricity & network switch settings mathiri.
- **Vilakkam (Explanation):** MCP Gateway-oda core engine settings: Oru tool call maximum ethana seconds run aagalam (timeout), maximum payload size evlo irukkalam, background worker threads ethana nu configure pandra control panel.
- **Business Value (Vaniga Payan):** Prevents slow tools from hanging server resources; guarantees gateway stability.

#### 💻 Tech Perspective (Technical Architecture)
- **Backend Architecture:** Core runtime configuration for the MCP Gateway subsystem. Manages maximum concurrent sessions, global execution timeouts, SSE heartbeat intervals, and payload size limits.
- **Backend Endpoints:**
  * `GET /api/v1/mcp/settings`
  * `PUT /api/v1/mcp/settings`

#### 🖥️ Screen Layout & Interactive Elements (Thirai Koorugal)
**1. Melpura Koorugal (Top Bar Controls):**
- Header Title
- Save Settings Button

**2. Mathiya Koorugal & Tables (Tabs & Views):**
- Settings Form: Global Tool Timeout ms, Max Payload Size MB, Max Concurrent Sessions, SSE Heartbeat Seconds

**3. Keezhpura Koorugal & Sheets (Bottom Elements & Slide-Overs):**
- Reset to Recommended Defaults Button

#### 🔗 Connections & Structure Map (Inaippugal)
- **Data-vai Perumidam (Receives From):** System Administrators.
- **Iyakkum Koorugal (Triggers & Affects):** Governs the execution environment of all Installed Servers and Sessions.

#### 💡 Production Use Case: Setting a strict 15-second timeout on all tool calls so a slow database query doesn't freeze the AI user experience.

---

## Pillar: Prompt Management & Playground — Prompt Management (Prompt Repo, Skills & Chat Playground)
*Enterprise prompt templates version control, reusable agent skills, and multi-model testing playground.*

<a name='prompt_repo'></a>
### Prompt Repo — Prompt Repo (Version Controlled Prompt Templates)
**UI Route:** `/workspace/prompt-repo`

#### 👤 Non-Tech Perspective (Makkal Puriyura Eliya Vilakkam)
- **Uruvagam (Analogy):** Software code-kaga irukkura GitHub repository mathiri, prompts-kaga irukkura Git repository.
- **Vilakkam (Explanation):** Developers application-la use pandra prompt templates-ah hardcode pannama, inga central-ah store panni version control (v1, v2, v3) pannalam. Code redeploy pannama prompt-ah change panni A/B test pannalam.
- **Business Value (Vaniga Payan):** Decouples prompt engineering from backend deployments; enables non-technical domain experts to optimize prompts safely.

#### 💻 Tech Perspective (Technical Architecture)
- **Backend Architecture:** Prompt template versioning engine with variable interpolation (`{{user_name}}`, `{{account_id}}`). Supports commit messages, semantic diffing, rollback to previous versions, and production release tagging.
- **Backend Endpoints:**
  * `GET /api/v1/prompts`
  * `POST /api/v1/prompts`
  * `GET /api/v1/prompts/{id}/versions`
  * `POST /api/v1/prompts/{id}/deploy`

#### 🖥️ Screen Layout & Interactive Elements (Thirai Koorugal)
**1. Melpura Koorugal (Top Bar Controls):**
- Create Prompt Button
- Search Prompts
- Tag Filter (Sales, Support, Code, Legal)

**2. Mathiya Koorugal & Tables (Tabs & Views):**
- Prompts Table: Prompt Name, Latest Version, Production Tag, Variables count, Last Updated, Actions
- Visual Diff Viewer: Side-by-side comparison of v1 vs v2

**3. Keezhpura Koorugal & Sheets (Bottom Elements & Slide-Overs):**
- PromptEditorSheet: Template textarea, Variable detector, Model parameter settings (temperature, top_p)

#### 🔗 Connections & Structure Map (Inaippugal)
- **Data-vai Perumidam (Receives From):** Prompt engineers and developers.
- **Iyakkum Koorugal (Triggers & Affects):** Supplies production templates to client apps via FastHTTP Proxy and Guardrail Rules.

#### 💡 Production Use Case: Updating the company's customer support prompt to include holiday return policies instantly without touching backend server code.

---

<a name='skills_repo'></a>
### Skills Repo — Skills Repo (Reusable Agent Competencies & Knowledge Packs)
**UI Route:** `/workspace/skills-repo`

#### 👤 Non-Tech Perspective (Makkal Puriyura Eliya Vilakkam)
- **Uruvagam (Analogy):** Specialized employee training certificates & skills handbook mathiri.
- **Vilakkam (Explanation):** AI Agent seiya koodiya complex multi-step workflows-ah 'Skill'-ah define panni store pannalam (e.g. 'Generate SQL Query', 'Summarize Financial PDF', 'Draft Legal Contract'). Entha agent venumnaalum intha skill-ah borrow pannikalam.
- **Business Value (Vaniga Payan):** Massive reuse of engineered AI workflows across multiple company applications.

#### 💻 Tech Perspective (Technical Architecture)
- **Backend Architecture:** Modular skill definition registry. Packages system instructions, few-shot demonstration examples, required MCP tool bindings, and validation schemas into an executable skill bundle.
- **Backend Endpoints:**
  * `GET /api/v1/skills`
  * `POST /api/v1/skills`
  * `PATCH /api/v1/skills/{id}`

#### 🖥️ Screen Layout & Interactive Elements (Thirai Koorugal)
**1. Melpura Koorugal (Top Bar Controls):**
- Create Skill Button
- Search Skills
- Category Filter

**2. Mathiya Koorugal & Tables (Tabs & Views):**
- Skills Grid: Skill Name, Version, Attached Tools count, Few-Shot Examples count, Actions Menu

**3. Keezhpura Koorugal & Sheets (Bottom Elements & Slide-Overs):**
- SkillBuilderSheet: System instructions, Required tool bindings, Demonstration input/output pairs

#### 🔗 Connections & Structure Map (Inaippugal)
- **Data-vai Perumidam (Receives From):** AI Engineers.
- **Iyakkum Koorugal (Triggers & Affects):** Enriches agent context during chat and automated agent workflows.

#### 💡 Production Use Case: Creating a standard 'Summarize Earnings Call' skill that automatically invokes financial tools and formats outputs consistently.

---

<a name='chat_playground'></a>
### Chat / Playground — Playground (Multi-Model Testing & Comparison Sandbox)
**UI Route:** `/workspace/chat`

#### 👤 Non-Tech Perspective (Makkal Puriyura Eliya Vilakkam)
- **Uruvagam (Analogy):** Test drive track mathiri (Car vaangurathukku munnadi test drive panni pakkura mathiri).
- **Vilakkam (Explanation):** Different AI models-ah (GPT-4o vs Claude 3.5 Sonnet vs Gemini 1.5) side-by-side compare panni, speed, answer quality, and cost-ah live-ah test panni pakkura interactive testing playground.
- **Business Value (Vaniga Payan):** Fast experimentation; empirical model evaluation before committing to production deployments.

#### 💻 Tech Perspective (Technical Architecture)
- **Backend Architecture:** Interactive multi-model streaming sandbox. Dispatches concurrent SSE requests to multiple providers simultaneously. Displays real-time Time-To-First-Token (TTFT), tokens per second (TPS), and dollar cost per response.
- **Backend Endpoints:**
  * `POST /api/v1/chat/completions`
  * `GET /api/v1/models`

#### 🖥️ Screen Layout & Interactive Elements (Thirai Koorugal)
**1. Melpura Koorugal (Top Bar Controls):**
- Model Selector Dropdowns (Multi-Model Split Screen)
- Temperature & Max Tokens Sliders
- System Prompt Input

**2. Mathiya Koorugal & Tables (Tabs & Views):**
- Split-Screen Chat View: Compare Model A vs Model B side-by-side in real time
- Live Latency & Cost Counter under each bubble

**3. Keezhpura Koorugal & Sheets (Bottom Elements & Slide-Overs):**
- Export Chat to Prompt Repo Button
- Parameter Configuration Sheet

#### 🔗 Connections & Structure Map (Inaippugal)
- **Data-vai Perumidam (Receives From):** Direct user prompts and templates from Prompt Repo.
- **Iyakkum Koorugal (Triggers & Affects):** Executes calls across Model Providers and displays telemetry.

#### 💡 Production Use Case: Testing whether Claude 3.5 Sonnet writes better SQL queries than GPT-4o on proprietary company database schemas.

---

## Pillar: Plugins & Extensibility — Plugins (Gateway Extensions & Custom Logic)
*Gateway functionality-ah expand panna custom logic, billing webhooks, and proprietary headers inject pandra extensible engine.*

<a name='plg_plugins'></a>
### Plugins — Plugins (Gateway Extensions & Lifecycle Hooks)
**UI Route:** `/workspace/plugins`

#### 👤 Non-Tech Perspective (Makkal Puriyura Eliya Vilakkam)
- **Uruvagam (Analogy):** Chrome extensions allathu WordPress plugins mathiri.
- **Vilakkam (Explanation):** Gateway core code-ah maathaama, ungalukku thevaiyana custom rules (e.g. proprietary token counter, custom headers, billing webhooks) add panna thevaiyana extensible plugin store.
- **Business Value (Vaniga Payan):** Zero friction integration of custom enterprise logic and legal policies directly into the proxy request pipeline.

#### 💻 Tech Perspective (Technical Architecture)
- **Backend Architecture:** WebAssembly (Wasm) and Go-based lifecycle interceptor pipeline. Hooks into `pre-request`, `post-request`, `response-streaming`, and `error-handling` execution phases with ordered priority.
- **Backend Endpoints:**
  * `GET /api/v1/plugins`
  * `POST /api/v1/plugins`
  * `PUT /api/v1/plugins/sequence`
  * `DELETE /api/v1/plugins/{id}`

#### 🖥️ Screen Layout & Interactive Elements (Thirai Koorugal)
**1. Melpura Koorugal (Top Bar Controls):**
- Add New Plugin Button
- Plugin Sequence Button (ListOrdered)

**2. Mathiya Koorugal & Tables (Tabs & Views):**
- Plugins Sidebar with status badges
- PluginsView: Name, Description, Version, Schema, Active Toggle

**3. Keezhpura Koorugal & Sheets (Bottom Elements & Slide-Overs):**
- AddNewPluginSheet: Name, Code/URL, Hook selectors
- PluginSequenceSheet: Visual drag-and-drop execution ordering

#### 🔗 Connections & Structure Map (Inaippugal)
- **Data-vai Perumidam (Receives From):** FastHTTP Proxy raw request.
- **Iyakkum Koorugal (Triggers & Affects):** Enriches headers, mutates payloads, and logs traces to LLM Logs.

#### 💡 Production Use Case: Injecting an enterprise compliance plugin that validates legal disclaimers on every financial advice prompt.

---

## Pillar: Governance & Identity — Governance (Identity, RBAC, Virtual Keys & Security)
*Multi-tenant enterprise hierarchy, synthetic Virtual Keys, automated SCIM provisioning, RBAC permissions, and immutable audit trails.*

<a name='gov_virtual_keys'></a>
### Virtual Keys — Virtual Keys (Proxy API Keys & Granular Quotas)
**UI Route:** `/workspace/governance/virtual-keys`

#### 👤 Non-Tech Perspective (Makkal Puriyura Eliya Vilakkam)
- **Uruvagam (Analogy):** Bank master account-ku sub-debit cards mathiri (ovvoru card-kum thani limit).
- **Vilakkam (Explanation):** Master OpenAI keys-ah developers kitta direct-ah tharama, dummy Virtual Key create panni tharuvom. Monthly $100 limit, specific models permission potruppom. Key leak aanaalum single click-la revoke pannikalam, real keys safe-ah irukkum.
- **Business Value (Vaniga Payan):** Zero credential leakage risk; 100% cost attribution by application; instant security revocation.

#### 💻 Tech Perspective (Technical Architecture)
- **Backend Architecture:** High-throughput cryptographic API key gateway middleware. Keys are generated with cryptographically secure tokens (`uf-key-...`) and stored as SHA-256 hashes. FastHTTP middleware validates tokens in < 1ms, checks budget balances, and enforces RPM/TPM limits.
- **Backend Endpoints:**
  * `GET /api/v1/governance/virtual-keys`
  * `POST /api/v1/governance/virtual-keys`
  * `POST /api/v1/governance/virtual-keys/rotate`

#### 🖥️ Screen Layout & Interactive Elements (Thirai Koorugal)
**1. Melpura Koorugal (Top Bar Controls):**
- Create Virtual Key Button
- Bulk Rotate Keys Button
- Search & Filter Bar

**2. Mathiya Koorugal & Tables (Tabs & Views):**
- Virtual Keys Table: Name, Masked Secret (copy/eye toggle), Team, Customer, BudgetDisplay progress bar, RateLimitDisplay badge, Status switch, Actions

**3. Keezhpura Koorugal & Sheets (Bottom Elements & Slide-Overs):**
- VirtualKeySheet: Team, Access Profile, Budget Cap $, Rate Limits, Model Allowlist, Expiration Date
- One-Time Secret Reveal Modal

#### 🔗 Connections & Structure Map (Inaippugal)
- **Data-vai Perumidam (Receives From):** Teams, Customers, and Access Profiles.
- **Iyakkum Koorugal (Triggers & Affects):** Authorizes incoming requests in FastHTTP Proxy and tracks spend into LLM Logs.

#### 💡 Production Use Case: Issuing a virtual key with a $150/month cap and Gemini-only access to an external vendor development squad.

---

<a name='gov_users'></a>
### Users — Users (Platform User Directory & Identity Management)
**UI Route:** `/workspace/governance/users`

#### 👤 Non-Tech Perspective (Makkal Puriyura Eliya Vilakkam)
- **Uruvagam (Analogy):** Company employee directory & staff ID register mathiri.
- **Vilakkam (Explanation):** UnifAI platform-la account irukkura ellam developers, team leads, finance managers, and admins list. Yaar yaar enna email, enna role, entha team-la irukaanga nu manage pandra central user directory.
- **Business Value (Vaniga Payan):** Centralized identity governance; seamless onboarding and automated access termination when staff leave.

#### 💻 Tech Perspective (Technical Architecture)
- **Backend Architecture:** User identity and authentication manager integrated with enterprise SSO (SAML 2.0 / OIDC) and automated SCIM provisioning. Sessions are signed via JWTs with mandatory MFA support.
- **Backend Endpoints:**
  * `GET /api/v1/governance/users`
  * `POST /api/v1/governance/users/invite`
  * `PATCH /api/v1/governance/users/{id}`

#### 🖥️ Screen Layout & Interactive Elements (Thirai Koorugal)
**1. Melpura Koorugal (Top Bar Controls):**
- Invite User Button
- Search Users
- Filter by Role / Status

**2. Mathiya Koorugal & Tables (Tabs & Views):**
- Users Table: Avatar, Name, Email, Assigned RBAC Role badge, Team Memberships, Last Active, Status badge, Actions

**3. Keezhpura Koorugal & Sheets (Bottom Elements & Slide-Overs):**
- InviteUserDialog: Email, Full Name, Initial Role, Assigned Teams
- EditUserSheet: Role adjust, Suspend user toggle

#### 🔗 Connections & Structure Map (Inaippugal)
- **Data-vai Perumidam (Receives From):** SCIM / SSO or Admin invites.
- **Iyakkum Koorugal (Triggers & Affects):** Binds to Teams, Virtual Keys, and RBAC roles; actions logged to Audit Logs.

#### 💡 Production Use Case: Inviting 25 software engineers to the platform with Member-level permissions assigned to the Search Squad.

---

<a name='gov_teams'></a>
### Teams — Teams (Departmental Squads & Shared Resource Pools)
**UI Route:** `/workspace/governance/teams`

#### 👤 Non-Tech Perspective (Makkal Puriyura Eliya Vilakkam)
- **Uruvagam (Analogy):** Company project squads allathu departments mathiri (e.g. Mobile Squad, Search Team).
- **Vilakkam (Explanation):** Developers-ah group panni team-ah pirikalam. Oru team-ku common monthly budget, shared virtual keys, and collaborative model access kudukalam.
- **Business Value (Vaniga Payan):** Departmental accountability; team-level AI spend tracking for CFO budget reviews.

#### 💻 Tech Perspective (Technical Architecture)
- **Backend Architecture:** Multi-tenant team resource isolation layer. Aggregates usage across all member users and attached virtual keys. Enforces team-level budget caps in PostgreSQL.
- **Backend Endpoints:**
  * `GET /api/v1/governance/teams`
  * `POST /api/v1/governance/teams`
  * `PATCH /api/v1/governance/teams/{id}`

#### 🖥️ Screen Layout & Interactive Elements (Thirai Koorugal)
**1. Melpura Koorugal (Top Bar Controls):**
- Create Team Button
- Search Teams
- Business Unit Filter

**2. Mathiya Koorugal & Tables (Tabs & Views):**
- Teams Table: Team Name, Description, Members count badge, Virtual Keys count, Monthly Budget Progress Bar, Parent Business Unit

**3. Keezhpura Koorugal & Sheets (Bottom Elements & Slide-Overs):**
- CreateTeamDialog: Name, Description, Parent Business Unit, Monthly Budget $, Team Lead
- ManageMembersSheet

#### 🔗 Connections & Structure Map (Inaippugal)
- **Data-vai Perumidam (Receives From):** Belongs to a Business Unit; groups Users.
- **Iyakkum Koorugal (Triggers & Affects):** Owns shared Virtual Keys; feeds spend into Dashboard.

#### 💡 Production Use Case: Allocating a shared $4,000 monthly budget to the 'Mobile App Team' with 15 engineers.

---

<a name='gov_business_units'></a>
### Business Units — Business Units (Enterprise Divisions & P&L Centers)
**UI Route:** `/workspace/governance/business-units`

#### 👤 Non-Tech Perspective (Makkal Puriyura Eliya Vilakkam)
- **Uruvagam (Analogy):** Corporate conglomerate divisions mathiri (Retail Division, Banking Division).
- **Vilakkam (Explanation):** Teams-ku mela irukura periya enterprise division. CFO and executive leadership company-oda multiple business units-kulla AI budget分配 pannavum, P&L tracking seiyavum use aagum.
- **Business Value (Vaniga Payan):** High-level corporate financial governance; automated chargebacks across major business divisions.

#### 💻 Tech Perspective (Technical Architecture)
- **Backend Architecture:** Top-level container in the multi-tenant governance tree (`BusinessUnit -> Teams -> Users -> Virtual Keys`). Aggregates financial consumption for corporate ERP systems (SAP, NetSuite).
- **Backend Endpoints:**
  * `GET /api/v1/governance/business-units`
  * `POST /api/v1/governance/business-units`

#### 🖥️ Screen Layout & Interactive Elements (Thirai Koorugal)
**1. Melpura Koorugal (Top Bar Controls):**
- Create Business Unit Button
- Search Divisions

**2. Mathiya Koorugal & Tables (Tabs & Views):**
- Business Units Table: Unit Name, Cost Code, Total Sub-Teams count, Aggregate Spend $, Head of Division

**3. Keezhpura Koorugal & Sheets (Bottom Elements & Slide-Overs):**
- BusinessUnitSheet: Unit Name, Cost Center Code, Owner Email, Quarterly Budget Cap $

#### 🔗 Connections & Structure Map (Inaippugal)
- **Data-vai Perumidam (Receives From):** Executive management.
- **Iyakkum Koorugal (Triggers & Affects):** Contains multiple Teams; feeds top-level cost analytics into Executive Dashboards.

#### 💡 Production Use Case: Tracking that the 'Healthcare Services' division consumed $60,000 in AI tokens across its 10 engineering teams.

---

<a name='gov_customers'></a>
### Customers — Customers (B2B Client Tenants & External Accounts)
**UI Route:** `/workspace/governance/customers`

#### 👤 Non-Tech Perspective (Makkal Puriyura Eliya Vilakkam)
- **Uruvagam (Analogy):** SaaS B2B client accounts mathiri.
- **Vilakkam (Explanation):** Neenga unga software-ah vera external clients-ku AI features vachu SaaS product-ah vikkiringa na, ovvoru client-aiyum 'Customer'-ah add panni avanga usage-ku bill podalam. Oru customer innoru customer-oda data-vai paarka mudiyathu.
- **Business Value (Vaniga Payan):** Monetize AI applications; seamless B2B client isolation; automated billing invoices based on client consumption.

#### 💻 Tech Perspective (Technical Architecture)
- **Backend Architecture:** External tenant isolation boundary. Associates virtual keys with external customer identifiers (`customer_id`). Enforces hard tenant isolation policies in PostgreSQL using Row-Level Security (RLS).
- **Backend Endpoints:**
  * `GET /api/v1/governance/customers`
  * `POST /api/v1/governance/customers`

#### 🖥️ Screen Layout & Interactive Elements (Thirai Koorugal)
**1. Melpura Koorugal (Top Bar Controls):**
- Create Customer Button
- Search & Filter Bar

**2. Mathiya Koorugal & Tables (Tabs & Views):**
- Customers Table: Customer Name, Status badge, Assigned Teams, Virtual Keys count, Cumulative Spend $, Tier, Actions

**3. Keezhpura Koorugal & Sheets (Bottom Elements & Slide-Overs):**
- CustomerSheet: Customer Name, External Account ID, Contact Email, Assigned Pricing Tier, Hard Spend Quota

#### 🔗 Connections & Structure Map (Inaippugal)
- **Data-vai Perumidam (Receives From):** Sales/CRM sync.
- **Iyakkum Koorugal (Triggers & Affects):** Scopes Virtual Keys and filters LLM Logs for customer-specific billing.

#### 💡 Production Use Case: Giving 50 B2B enterprise clients their own dedicated virtual keys with strictly metered billing for your AI legal review software.

---

<a name='gov_scim'></a>
### User Provisioning (SCIM) — User Provisioning / SCIM (Automated Enterprise SSO Lifecycle)
**UI Route:** `/workspace/scim`

#### 👤 Non-Tech Perspective (Makkal Puriyura Eliya Vilakkam)
- **Uruvagam (Analogy):** Automatic company ID card issuing & revoking machine mathiri.
- **Vilakkam (Explanation):** Okta, Microsoft Entra ID / Azure AD, Keycloak-la pudhu aal sertha automatic-ah UnifAI-layum login create aagum. Employee velaiya vittu ponavudane Okta-la offboard pannina, automatic-ah UnifAI access cut aagidum!
- **Business Value (Vaniga Payan):** Zero orphan accounts; 100% SOC-2 compliance for employee lifecycle security; automated enterprise IT operations.

#### 💻 Tech Perspective (Technical Architecture)
- **Backend Architecture:** Standard SCIM v2.0 (RFC 7643 & RFC 7644) server. Handles `/scim/v2/Users` and `/scim/v2/Groups` with Bearer Token auth. Automatically creates, updates, deactivates users, and maps directory groups to Teams.
- **Backend Endpoints:**
  * `GET /scim/v2/Users`
  * `POST /scim/v2/Users`
  * `GET /scim/v2/Groups`
  * `GET /api/v1/scim/config`

#### 🖥️ Screen Layout & Interactive Elements (Thirai Koorugal)
**1. Melpura Koorugal (Top Bar Controls):**
- SCIM Master Enable Switch
- IdP Provider Selector (Okta, Entra ID, Keycloak)

**2. Mathiya Koorugal & Tables (Tabs & Views):**
- SCIM Endpoints Card: Base URL, Users endpoint, ServiceProviderConfig (with copy buttons)
- Group Mapping Card

**3. Keezhpura Koorugal & Sheets (Bottom Elements & Slide-Overs):**
- Bearer Token Generator with copy button and rotation warning
- Save SCIM Config Button

#### 🔗 Connections & Structure Map (Inaippugal)
- **Data-vai Perumidam (Receives From):** External Identity Providers (Okta, Entra ID).
- **Iyakkum Koorugal (Triggers & Affects):** Provisions and deprovisions Users and synchronizes Teams.

#### 💡 Production Use Case: Auto-provisioning UnifAI accounts for 1,500 corporate employees via Okta SCIM sync.

---

<a name='gov_rbac'></a>
### Roles & Permissions (RBAC) — Roles & Permissions (RBAC Security & Access Matrix)
**UI Route:** `/workspace/governance/rbac`

#### 👤 Non-Tech Perspective (Makkal Puriyura Eliya Vilakkam)
- **Uruvagam (Analogy):** Office security access badge permissions mathiri.
- **Vilakkam (Explanation):** Yaaru platform-la enna seiyalaam nu kattu paduthum access control matrix. Super Admin-ku full control; Developer-ku API key create panna mattum permission; Finance-ku logs and billing charts mattum paarka permission (read-only).
- **Business Value (Vaniga Payan):** Least-privilege security principle. Prevents accidental deletions and unauthorized key tampering.

#### 💻 Tech Perspective (Technical Architecture)
- **Backend Architecture:** Declarative Role-Based Access Control (RBAC) engine in Go and React. Enforces fine-grained resource-action pairs (`Resource: ModelProvider, VirtualKeys, RoutingRules, Settings, AuditLogs, Plugins` × `Action: View, Create, Update, Delete`).
- **Backend Endpoints:**
  * `GET /api/v1/governance/rbac/roles`
  * `POST /api/v1/governance/rbac/roles`
  * `GET /api/v1/governance/rbac/permissions`

#### 🖥️ Screen Layout & Interactive Elements (Thirai Koorugal)
**1. Melpura Koorugal (Top Bar Controls):**
- Create Custom Role Button
- Role Filter (System vs Custom)

**2. Mathiya Koorugal & Tables (Tabs & Views):**
- Roles Table: Role Name, Description, Assigned Users count, Type badge, Actions
- RBAC Permission Matrix Grid: Resources on rows, Actions on columns with checkboxes

**3. Keezhpura Koorugal & Sheets (Bottom Elements & Slide-Overs):**
- RoleBuilderSheet: Role Name, Description, Permission checkboxes
- AssignUsersModal

#### 🔗 Connections & Structure Map (Inaippugal)
- **Data-vai Perumidam (Receives From):** Assigned to Users and Teams.
- **Iyakkum Koorugal (Triggers & Affects):** Controls authorization on every API and UI view.

#### 💡 Production Use Case: Creating a 'Finance Auditor' role that can View Dashboard and View LLM Logs, but cannot create or delete any keys or models.

---

<a name='gov_access_profiles'></a>
### Access Profiles — Access Profiles (Reusable Policy Bundles & Guardrail Packs)
**UI Route:** `/workspace/governance/access-profiles`

#### 👤 Non-Tech Perspective (Makkal Puriyura Eliya Vilakkam)
- **Uruvagam (Analogy):** Pre-packaged security passport allathu policy bundle mathiri.
- **Vilakkam (Explanation):** Oru standard policy template create panni vachikalam (e.g. 'Intern Profile': GPT-4o-mini mattum allow panni, $50 budget limit, PII redaction ON). Pudhu virtual key create pannum pothu intha profile-ah select panna ella security rules-um automatic-ah apply aagidum!
- **Business Value (Vaniga Payan):** Administrative time savings; eliminates configuration mistakes; guarantees that no virtual key goes live without security guardrails.

#### 💻 Tech Perspective (Technical Architecture)
- **Backend Architecture:** Reusable policy entity bundling Allowed Models, Allowed Providers, Budget Caps, Rate Limits (RPM/TPM), MCP Tool Groups, and Guardrails. Attached to Virtual Keys via relational join.
- **Backend Endpoints:**
  * `GET /api/v1/governance/access-profiles`
  * `POST /api/v1/governance/access-profiles`
  * `POST /api/v1/governance/access-profiles/{id}/clone`

#### 🖥️ Screen Layout & Interactive Elements (Thirai Koorugal)
**1. Melpura Koorugal (Top Bar Controls):**
- Create Access Profile Button
- Search & Tag Filter

**2. Mathiya Koorugal & Tables (Tabs & Views):**
- Access Profiles Table: Profile Name, Tags badges, Allowed Models, Attached Keys count, Budget/Rate limit summary, Actions

**3. Keezhpura Koorugal & Sheets (Bottom Elements & Slide-Overs):**
- AccessProfileDialog: Allowed Models multiselect, Budget Caps $, RPM/TPM Rate limits, MCP Tool Client pickers
- Quick Clone Button

#### 🔗 Connections & Structure Map (Inaippugal)
- **Data-vai Perumidam (Receives From):** Security administrators.
- **Iyakkum Koorugal (Triggers & Affects):** Governs Virtual Keys behavior and restricts Model Providers and MCP tools.

#### 💡 Production Use Case: Attaching a single 'Customer Chatbot Profile' to 30 virtual keys, guaranteeing PII redaction and 60 RPM limits across all 30 keys simultaneously.

---

<a name='gov_audit_logs'></a>
### Audit Logs — Audit Logs (Tamper-Proof Compliance & Activity Trail)
**UI Route:** `/workspace/audit-logs`

#### 👤 Non-Tech Perspective (Makkal Puriyura Eliya Vilakkam)
- **Uruvagam (Analogy):** Bank locker CCTV camera & register note mathiri.
- **Vilakkam (Explanation):** Platform-la yaaru yaaru entha nerathula enna maathinaanga nu maatha mudiyatha (tamper-proof) pathivu. Yaarachum API key delete pannalaam, budget limit maathinaalo, pudhu routing rule pottaalo exact timestamp, user name, and client IP address-oda capture aagum.
- **Business Value (Vaniga Payan):** 100% SOC-2, HIPAA, and GDPR audit readiness; insider threat detection; rapid forensic debugging.

#### 💻 Tech Perspective (Technical Architecture)
- **Backend Architecture:** Immutable, append-only security event audit trail. Captures Actor User ID, Action Type (CREATE, UPDATE, DELETE), Target Resource, Timestamp, Client IP address, User-Agent, and before/after JSON diffs in PostgreSQL.
- **Backend Endpoints:**
  * `GET /api/v1/audit-logs`
  * `GET /api/v1/audit-logs/{id}`
  * `GET /api/v1/audit-logs/export`

#### 🖥️ Screen Layout & Interactive Elements (Thirai Koorugal)
**1. Melpura Koorugal (Top Bar Controls):**
- Date Range Picker
- Actor Search
- Action Type Filter (CREATE, UPDATE, DELETE)
- Resource Filter
- Export Button (CSV/JSON)

**2. Mathiya Koorugal & Tables (Tabs & Views):**
- Audit Logs Table: Timestamp, Actor Name & Email, Action Badge, Resource Type, Target ID, Client IP, Details Button

**3. Keezhpura Koorugal & Sheets (Bottom Elements & Slide-Overs):**
- Audit Detail Drawer: Displays complete before-and-after JSON delta diff highlighting modified fields

#### 🔗 Connections & Structure Map (Inaippugal)
- **Data-vai Perumidam (Receives From):** Intercepts administrative mutations across all Governance, Models, and Observability features.
- **Iyakkum Koorugal (Triggers & Affects):** Feeds security alerts and provides compliance proof for auditors.

#### 💡 Production Use Case: Demonstrating to external SOC-2 auditors exactly who rotated the production AWS Bedrock credentials on July 10th.

---

## Pillar: Security Guardrails — Guardrails (Content Safety & Attack Prevention)
*Prompt injection prevention, PII redaction, toxicity filtering, and multi-engine security scanners.*

<a name='grd_rules'></a>
### Guardrail Rules — Guardrail Rules (AI Safety Policies & Screening)
**UI Route:** `/workspace/guardrails/configuration`

#### 👤 Non-Tech Perspective (Makkal Puriyura Eliya Vilakkam)
- **Uruvagam (Analogy):** Airport baggage scanner & security checkpoint mathiri.
- **Vilakkam (Explanation):** Customer allathu employee AI kitta bad words, company secrets, credit card numbers, allathu jailbreak / prompt injection attacks seiyatha mathiri thadukkura security rules. Rules meera patta udane request-ah block pannum allathu PII data-vai asterisk (*) pottu mask pannum.
- **Business Value (Vaniga Payan):** Zero data leakage (PII/Secrets); regulatory compliance (HIPAA/GDPR); brand reputation protection.

#### 💻 Tech Perspective (Technical Architecture)
- **Backend Architecture:** Pre-request and post-completion content security policy engine in Go. Evaluates prompt scope (`all`, specific Prompt Repo IDs, or custom CEL expressions). Rejects violations with HTTP 400/403 with verdict codes (`PII_DETECTED`, `PROMPT_INJECTION`).
- **Backend Endpoints:**
  * `GET /api/v1/guardrails/config`
  * `PUT /api/v1/guardrails/config`
  * `POST /api/v1/guardrails/test`

#### 🖥️ Screen Layout & Interactive Elements (Thirai Koorugal)
**1. Melpura Koorugal (Top Bar Controls):**
- Header with ShieldAlert Icon
- Add Rule Button
- Active Rules Count Badge

**2. Mathiya Koorugal & Tables (Tabs & Views):**
- Guardrail Rules Table: Rule Name, Active Toggle, Prompt Scope, Linked Providers, Evaluation Action, Actions

**3. Keezhpura Koorugal & Sheets (Bottom Elements & Slide-Overs):**
- GuardrailRuleDialog: Rule Name, Linked Providers multiselect, Prompt Scope Selector (All, Selected Prompts, Custom CEL), CEL Editor

#### 🔗 Connections & Structure Map (Inaippugal)
- **Data-vai Perumidam (Receives From):** FastHTTP Proxy and Prompt Repository.
- **Iyakkum Koorugal (Triggers & Affects):** Blocks attacks, redacts sensitive text, triggers Alert Channels, and logs incidents to LLM Logs.

#### 💡 Production Use Case: Preventing chatbot users from extracting system prompts or submitting SQL injection payloads into AI text fields.

---

<a name='grd_providers'></a>
### Guardrail Providers — Guardrail Providers (Security Engines & Regex Scanners)
**UI Route:** `/workspace/guardrails/providers`

#### 👤 Non-Tech Perspective (Makkal Puriyura Eliya Vilakkam)
- **Uruvagam (Analogy):** Security inspection scanner machinery brands mathiri.
- **Vilakkam (Explanation):** Security rules run aagurathukku thevaiyana scanning engines (Presidio PII Engine, Llama-Guard Toxicity Engine, Lakera Prompt Injection Scanner, AWS Bedrock Guardrails, allathu Custom Regex Pattern matching engines) configure pandra edham.
- **Business Value (Vaniga Payan):** Customizable data defense; multi-layered scanning capability; adaptability to enterprise-specific regex patterns.

#### 💻 Tech Perspective (Technical Architecture)
- **Backend Architecture:** Multi-engine security scanner registry. Supports local RE2 regex matching, lightweight embeddings classifiers, and external gRPC/HTTP safety microservices (Microsoft Presidio, Meta Llama-Guard). Concurrent Go worker execution (< 15ms).
- **Backend Endpoints:**
  * `GET /api/v1/guardrails/config`
  * `PUT /api/v1/guardrails/config`

#### 🖥️ Screen Layout & Interactive Elements (Thirai Koorugal)
**1. Melpura Koorugal (Top Bar Controls):**
- Add Provider Button
- Navigation Tabs (Rules vs Providers)

**2. Mathiya Koorugal & Tables (Tabs & Views):**
- Guardrail Providers Table: Provider ID, Policy Name, Engine Type (Regex/Presidio/Bedrock), Pattern Count badge, Linked Rules count badge, Actions

**3. Keezhpura Koorugal & Sheets (Bottom Elements & Slide-Overs):**
- GuardrailProviderDialog: Provider ID, Policy Name, Engine Type, Multi-line Regex Patterns textarea, Pattern Syntax Validator

#### 🔗 Connections & Structure Map (Inaippugal)
- **Data-vai Perumidam (Receives From):** DevSecOps engineers.
- **Iyakkum Koorugal (Triggers & Affects):** Supplies scanning algorithms and regex patterns to Guardrail Rules.

#### 💡 Production Use Case: Configuring custom regex patterns to detect and mask proprietary internal project code names before prompts reach public models.

---

## Pillar: High Availability & Infrastructure — Infrastructure (Cluster Mesh, Alerts & OAuth)
*Multi-region cluster synchronization, Slack/PagerDuty alert channels, and third-party OAuth access grants.*

<a name='inf_cluster'></a>
### Cluster Config — Cluster Config (Distributed Mesh & High-Availability Sync)
**UI Route:** `/workspace/cluster`

#### 👤 Non-Tech Perspective (Makkal Puriyura Eliya Vilakkam)
- **Uruvagam (Analogy):** Multi-aircraft flight formation allathu multi-branch bank network mathiri.
- **Vilakkam (Explanation):** Multiple UnifAI servers (USA, Europe, India regions) run aagum pothu, antha ellam servers-um onnukonnu pesikittu, rate limits, virtual key balances, and circuit breaker states instant-ah sync aaguratha uruthi seiyura master cluster control panel.
- **Business Value (Vaniga Payan):** Zero single point of failure; multi-region active-active deployment; global consistency.

#### 💻 Tech Perspective (Technical Architecture)
- **Backend Architecture:** Distributed Mesh / Gossip protocol (HashiCorp Memberlist / Serf). Nodes communicate via TCP/UDP peer gossip over port 7946. Synchronizes in-memory rate-limit buckets and circuit breaker states (< 50ms) across regions.
- **Backend Endpoints:**
  * `GET /api/v1/cluster/config`
  * `PUT /api/v1/cluster/config`
  * `GET /api/v1/cluster/nodes`

#### 🖥️ Screen Layout & Interactive Elements (Thirai Koorugal)
**1. Melpura Koorugal (Top Bar Controls):**
- Header with Network Icon
- Cluster Master Enable Switch

**2. Mathiya Koorugal & Tables (Tabs & Views):**
- Cluster Topology Card: Cluster Type (Mesh/Gossip), Region ID, Peer Seed List textarea (host:port, e.g. 10.0.0.12:7946)
- Node Info Card: Node ID, Bind Address, Role, Active Peers count

**3. Keezhpura Koorugal & Sheets (Bottom Elements & Slide-Overs):**
- Peer Syntax Validator with inline warnings
- Save Configuration Button

#### 🔗 Connections & Structure Map (Inaippugal)
- **Data-vai Perumidam (Receives From):** DevOps / SRE teams.
- **Iyakkum Koorugal (Triggers & Affects):** Synchronizes Virtual Key rate limits and Circuit Breaker states across all gateway pods.

#### 💡 Production Use Case: Deploying 10 UnifAI gateway pods in Kubernetes, ensuring a user's 60 RPM rate limit is enforced globally rather than allowing 600 requests.

---

<a name='inf_alerts'></a>
### Alert Channels — Alert Channels (Incident Notifications & Webhooks)
**UI Route:** `/workspace/alert-channels`

#### 👤 Non-Tech Perspective (Makkal Puriyura Eliya Vilakkam)
- **Uruvagam (Analogy):** Emergency fire alarm & automated SMS siren mathiri.
- **Vilakkam (Explanation):** AI provider crash aanaalo, budget 90% reach aanaalo, allathu prompt injection attack nadanthalo, on-duty engineers-ku instant-ah Slack, PagerDuty, Microsoft Teams, allathu Email alert anuppura emergency notification hub.
- **Business Value (Vaniga Payan):** Rapid incident response; minimizes downtime; prevents surprise cloud billing spikes.

#### 💻 Tech Perspective (Technical Architecture)
- **Backend Architecture:** Multi-channel incident notification dispatcher. Formats structured alerts into Slack webhook blocks, PagerDuty Events v2 JSON, or SMTP email alerts. Implements notification de-duplication and rate dampening.
- **Backend Endpoints:**
  * `GET /api/v1/alert-channels`
  * `POST /api/v1/alert-channels`
  * `POST /api/v1/alert-channels/{id}/test`

#### 🖥️ Screen Layout & Interactive Elements (Thirai Koorugal)
**1. Melpura Koorugal (Top Bar Controls):**
- Add Alert Channel Button
- Channel Type Filter (Slack, PagerDuty, Email, Webhook)

**2. Mathiya Koorugal & Tables (Tabs & Views):**
- Alert Channels Table: Channel Name, Type badge, Webhook Endpoint, Subscribed Events badges, Health Status, Actions

**3. Keezhpura Koorugal & Sheets (Bottom Elements & Slide-Overs):**
- AddChannelDialog: Channel Name, Type selector, Webhook URL, Event Subscriptions checkboxes, Send Test Notification button

#### 🔗 Connections & Structure Map (Inaippugal)
- **Data-vai Perumidam (Receives From):** Triggered by Circuit Breaker trips, Budgets & Limits warnings, and Guardrail violations.
- **Iyakkum Koorugal (Triggers & Affects):** Dispatches messages to corporate Slack and PagerDuty.

#### 💡 Production Use Case: Triggering a high-urgency PagerDuty incident when OpenAI fails and Circuit Breaker activates the backup Azure route.

---

<a name='inf_oauth'></a>
### OAuth Grants — OAuth Grants (Third-Party App Authorizations)
**UI Route:** `/workspace/oauth-grants`

#### 👤 Non-Tech Perspective (Makkal Puriyura Eliya Vilakkam)
- **Uruvagam (Analogy):** Mobile phone-la 'Allow app to access camera/contacts' permission screen mathiri.
- **Vilakkam (Explanation):** External software and AI developer tools (Cursor IDE, Continue.dev, internal apps) UnifAI gateway-kulla login panni access kettu varum pothu, antha third-party app-ku permission grant pandra OAuth 2.0 authorization center.
- **Business Value (Vaniga Payan):** Standardized, secure enterprise developer tool integration without sharing permanent secret keys.

#### 💻 Tech Perspective (Technical Architecture)
- **Backend Architecture:** OAuth 2.0 / OIDC Authorization Server. Manages OAuth client IDs, client secrets, redirect URIs, authorization code exchanges, and refresh token rotation. Issues scoped access tokens.
- **Backend Endpoints:**
  * `GET /api/v1/oauth/grants`
  * `POST /api/v1/oauth/clients`
  * `DELETE /api/v1/oauth/grants/{id}`

#### 🖥️ Screen Layout & Interactive Elements (Thirai Koorugal)
**1. Melpura Koorugal (Top Bar Controls):**
- Register OAuth Client Button
- Search Grants

**2. Mathiya Koorugal & Tables (Tabs & Views):**
- Active Grants Table: Client App Name, User, Scopes Granted badges, Issued At, Expires At, Revoke Access Button

**3. Keezhpura Koorugal & Sheets (Bottom Elements & Slide-Overs):**
- RegisterClientDialog: App Name, Redirect URIs, Allowed Grant Types, Requested Scopes

#### 🔗 Connections & Structure Map (Inaippugal)
- **Data-vai Perumidam (Receives From):** External developer tools (Cursor, LangChain apps).
- **Iyakkum Koorugal (Triggers & Affects):** Issues scoped Virtual Key equivalent tokens for API access.

#### 💡 Production Use Case: Authorizing developer Cursor IDE instances to route requests through UnifAI via OAuth 2.0 login.

---

## Pillar: Adaptive Routing & Load Balancing — Adaptive Routing (Dynamic Latency & Score-Based Balancing)
*Multi-Armed Bandit real-time latency scoring, automated key weighting, and unhealthy route pruning.*

<a name='adp_dashboard'></a>
### Adaptive Routing Dashboard — Adaptive Routing Dashboard (Live Health Scoring & Traffic Steering)
**UI Route:** `/workspace/adaptive-routing`

#### 👤 Non-Tech Perspective (Makkal Puriyura Eliya Vilakkam)
- **Uruvagam (Analogy):** Google Maps Live Traffic Navigation mathiri.
- **Vilakkam (Explanation):** Oru AI model (OpenAI GPT-4o) ippo slow aagiduchuna allathu error adikkithu na, system live-ah detect panni, automatically athe tharam konda innoru fast-ana provider-ku (Azure OpenAI allathu Anthropic) traffic-ah thiruppi vittu user-ku semma fast response tharum.
- **Business Value (Vaniga Payan):** Guarantees lowest possible latency; automated self-healing routing during vendor slowdowns.

#### 💻 Tech Perspective (Technical Architecture)
- **Backend Architecture:** Multi-Armed Bandit (MAB) reinforcement learning load balancer. Evaluates provider directions and individual API key routes based on live p50/p95 latency and error rates. Polled every 8 seconds (`pollingInterval: 8000ms`). Dynamically assigns routing weights.
- **Backend Endpoints:**
  * `GET /api/v1/load-balancer/routes`
  * `PUT /api/v1/load-balancer/config`
  * `GET /api/v1/load-balancer/metrics`

#### 🖥️ Screen Layout & Interactive Elements (Thirai Koorugal)
**1. Melpura Koorugal (Top Bar Controls):**
- Header with Gauge Icon
- Settings Button deep-link

**2. Mathiya Koorugal & Tables (Tabs & Views):**
- 3 Summary Metric Cards: Load Balancer Switch, Live Scoring Strategy, Active Dynamic Routes
- Live Adaptive Routes Table: Provider/Direction, Model Name, Health Score (0-100 color badge), p50/p95 Latency ms, Error Rate %, Traffic Weight %, Status

**3. Keezhpura Koorugal & Sheets (Bottom Elements & Slide-Overs):**
- 8-second background auto-refresh poller reflecting live shifting traffic weights

#### 🔗 Connections & Structure Map (Inaippugal)
- **Data-vai Perumidam (Receives From):** Latency and error telemetry from FastHTTP Proxy and Model Providers.
- **Iyakkum Koorugal (Triggers & Affects):** Dynamically overrides Routing Rules traffic weights.

#### 💡 Production Use Case: When OpenAI latency spikes from 800ms to 4,500ms, adaptive routing automatically shifts 85% of traffic to Azure OpenAI maintaining 650ms p95 latency.

---

<a name='adp_settings'></a>
### Adaptive Routing Settings — Adaptive Routing Settings (Load Balancing Policy & Pruning Rules)
**UI Route:** `/workspace/adaptive-routing/settings`

#### 👤 Non-Tech Perspective (Makkal Puriyura Eliya Vilakkam)
- **Uruvagam (Analogy):** Car cruise control & autopilot driving preference settings mathiri.
- **Vilakkam (Explanation):** Adaptive load balancer eppadi nadanthukanum nu rules poduvom: Slow-ana vendor-ah automatic-ah ignore pannanuma? Oru vendor fail aana automatic-ah adutha vendor-ku reroute pannanuma? Multi-key balancing on pannanuma nu control pandra settings page.
- **Business Value (Vaniga Payan):** Predictable routing behavior; fine-grained engineering control over automated failovers.

#### 💻 Tech Perspective (Technical Architecture)
- **Backend Architecture:** Load balancer configuration and policy persistence engine in PostgreSQL (`LoadBalancerConfig`). Controls direction selection algorithms, key-level round-robin weighting, failed direction rerouting, and fallback pruning.
- **Backend Endpoints:**
  * `GET /api/v1/load-balancer/config`
  * `PUT /api/v1/load-balancer/config`

#### 🖥️ Screen Layout & Interactive Elements (Thirai Koorugal)
**1. Melpura Koorugal (Top Bar Controls):**
- Header Title
- Back Button to Dashboard
- Save Settings Button

**2. Mathiya Koorugal & Tables (Tabs & Views):**
- Settings Card with 5 Policy Toggle Rows: (1) Enable adaptive load balancing, (2) Direction selection, (3) Route selection, (4) Reroute failed directions, (5) Prune failed fallbacks

**3. Keezhpura Koorugal & Sheets (Bottom Elements & Slide-Overs):**
- Save Configuration Button with instant toast confirmation

#### 🔗 Connections & Structure Map (Inaippugal)
- **Data-vai Perumidam (Receives From):** DevOps / Infrastructure leads.
- **Iyakkum Koorugal (Triggers & Affects):** Governs the algorithmic behavior of Adaptive Routing Dashboard.

#### 💡 Production Use Case: Enabling 'Reroute failed directions' ensuring critical production apps never suffer timeouts from degraded upstream vendors.

---

# 3. Cross-Feature Interconnections & Data Flow Matrix
### UnifAI Platform Features Kulla Irukura Master Connections

| Source Feature | Connected To | Category | Data Flow & Trigger Action |
| :--- | :--- | :--- | :--- |
| **Dashboard** | **LLM Logs** | `Observability` | Visualizes real-time request volume, token usage, latencies, and costs. |
| **LLM Logs** | **Connectors** | `Observability` | Streams structured transaction events to Datadog, Kafka, and BigQuery. |
| **MCP Logs** | **MCP Gateway** | `MCP` | Records JSON-RPC arguments, tool execution traces, and stdout/stderr outputs. |
| **Browser AI** | **Audit Logs** | `Security` | Intercepts employee web AI paste events and logs confidential DLP violations. |
| **Model Catalog** | **Routing Rules** | `Models` | Provides verified model identifiers and context parameters for routing targets. |
| **Model Providers** | **FastHTTP Proxy** | `Core` | Supplies decrypted API keys, custom base URLs, and connection pools. |
| **Budgets & Limits** | **Virtual Keys** | `Governance` | Enforces strict dollar quotas and token rate limits on API keys. |
| **Complexity Router** | **Routing Rules** | `Models` | Scores query complexity (0-1) and assigns model tier (Simple to Reasoning). |
| **Circuit Breaker** | **Alert Channels** | `Infrastructure` | Triggers high-priority PagerDuty alerts when a primary provider fails. |
| **Pricing Overrides** | **Dashboard & Billing** | `Finance` | Calculates real dollar spend using negotiated corporate discount rates. |
| **MCP Gateway** | **Tool Groups** | `MCP` | Organizes certified tools into permission groups for Virtual Key assignment. |
| **Prompt Repo** | **Guardrail Rules** | `Security` | Links prompt templates to content screening and jailbreak detection rules. |
| **Plugins** | **FastHTTP Proxy** | `Extensibility` | Executes Wasm/Go pre-request, post-request, and streaming lifecycle hooks. |
| **Virtual Keys** | **Access Profiles** | `Governance` | Inherits model restrictions, budget limits, and MCP permissions. |
| **SCIM** | **Users & Teams** | `Identity` | Auto-provisions users and syncs directory groups from Okta and Entra ID. |
| **RBAC** | **All UI & APIs** | `Security` | Enforces declarative View/Create/Update/Delete permissions on every endpoint. |
| **Audit Logs** | **All Features** | `Compliance` | Immutably records every configuration change, key rotation, and admin action. |
| **Guardrail Rules** | **Guardrail Providers** | `Security` | Executes RE2 regex, Presidio, or Bedrock scanner engines on prompt text. |
| **Cluster Config** | **Virtual Keys & Circuit** | `Infrastructure` | Synchronizes rate-limit buckets and circuit trip states globally (:7946). |
| **Adaptive Routing** | **Model Providers** | `Performance` | Continuously scores provider latencies (ms) and shifts traffic dynamically. |

---

# 4. Master Tech vs Non-Tech Comparative Matrix
### Thozhilnutpam vs Vanigam Parvai Master Oppeedo

| Feature | Non-Tech View (Manager / CFO Parvai) | Tech View (DevOps / Architect Parvai) |
| :--- | :--- | :--- |
| **Dashboard** | "AI spend evlo aaguthu, budget control-la irukka nu ore screen-la pakkalam." | "WebSocket telemetry & atomic counters aggregating p95 latencies and TTFT into Postgres." |
| **LLM Logs** | "Yaaru enna kelvi kettanga, AI enna bathil sonnathu nu passbook mathiri check pannalam." | "Sub-millisecond PostgreSQL batch-insert ledger capturing raw payloads, tokens, and status codes." |
| **MCP Logs** | "AI Agent company database-la enna vela senjithu nu inspect pannalam." | "JSON-RPC 2.0 tool execution tracing across stdio and SSE agent transport protocols." |
| **Browser AI** | "Employees company secrets-ah web ChatGPT-la copy-paste pannama thadukkalam." | "Client-side mitmproxy daemon intercepting web AI pastes with Presidio DLP regexes." |
| **Connectors** | "AI spend and logs automatic-ah namma corporate BigQuery/Datadog-ku poiduma?" | "Async streaming queue worker pushing events via OpenTelemetry, Kafka, and HTTP webhooks." |
| **Model Catalog** | "Entha entha AI models namakku irukku? Ethu active-ah irukku nu menu card mathiri pakkalam." | "FastHTTP model registry with capability filtering (vision, tool calling) and 24h usage metrics." |
| **Model Providers** | "OpenAI, Anthropic, Bedrock API keys safe-ah connect aagi run aagutha?" | "Multi-vendor credential vault, FastHTTP client connection pools, and exponential retry backoffs." |
| **Budgets & Limits** | "Excessive bill varama ovvoru team-kum monthly budget cap potu stop panna mudiyuma?" | "Atomic Redis/Postgres token bucket rate limiters evaluating multi-tiered limits with HTTP 429." |
| **Complexity Router** | "Simple kelvikku cheap model, tough kelvikku matum costly model use panni 70% bill micham aagutha?" | "Heuristic multi-factor scoring engine categorizing queries into Simple, Med, Complex, Reasoning." |
| **Circuit Breaker** | "OpenAI crash aanaal kooda customer-ku error theriyaama backup model-ku switch aaguma?" | "Distributed finite state machine (Closed/Open/Half-Open) monitoring response header signals." |
| **MCP Catalog** | "AI agent-ku thevaiyana tools (GitHub, SQL, Slack) app store mathiri install pannalama?" | "Curated MCP registry client fetching validated schemas and execution configurations." |
| **Prompt Repo** | "Prompt templates-ah code mathiri GitHub style-la version control panni release pannalama?" | "Prompt template engine with variable interpolation (`{{var}}`), semantic diffs, and release tags." |
| **Plugins** | "Custom company rules and billing webhooks gateway-kulla plug-and-play-ah poda mudiyuma?" | "Wasm/Go lifecycle interceptor pipeline hooking into pre-request, post-request, and streaming chunks." |
| **Virtual Keys** | "Real OpenAI master keys-ah tharama safe-ana dummy keys with budget limits tharalama?" | "Cryptographic SHA-256 hashed API tokens with sub-millisecond FastHTTP auth and rate limiters." |
| **SCIM** | "Okta-la employee join aana automatic-ah account create aagi, leave aana cut aaguma?" | "RFC 7643/7644 SCIM v2.0 server handling automated user lifecycle and group synchronization." |
| **RBAC** | "Admin-ku mattum full rights, mathavangalukku view-only permission pottu lock pannalama?" | "Declarative resource-action permission matrix evaluating gates across all UI views and REST APIs." |
| **Access Profiles** | "Reusable standard security template create panni 20 keys-ku single click-la apply pannalama?" | "Bundled governance policy entity containing model allowlists, budget caps, rate limits, and MCP tools." |
| **Audit Logs** | "Yaaru entha key-ah maathinaanga, eppo delete panninaanga nu maatha mudiyatha proof irukka?" | "Append-only immutable audit trail capturing actor, action, timestamp, IP, and before/after JSON diffs." |
| **Guardrail Rules** | "Prompt injection, bad words, and company secrets AI kitta pogama thadukkuma?" | "CEL conditional content security engine scanning prompts/responses and returning 400/403 on violation." |
| **Cluster Config** | "Multiple servers run aanaalum budget and rate limits correct-ah sync aaguma?" | "Distributed Mesh/Gossip consensus protocol (port 7946) synchronizing state across multi-region nodes." |
| **Adaptive Routing** | "Oru AI vendor slow aana automatic-ah fastest backup vendor-ku reroute aaguma?" | "Real-time Multi-Armed Bandit load balancer calculating live health scores (0-100) from p95 latency." |
