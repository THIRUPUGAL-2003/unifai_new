# UnifAI Models Pillar Master Deep-Dive Guide
## UnifAI Models Amaippin Muzhumaiyana Technical & Non-Technical Manual

**Pillar:** Models (AI Model Catalog, Providers, Limits, Routing, & Resilience)  
**Target Audience:** Developers, System Architects, CTOs, CFOs, Product Managers & Operations Teams  
**Language:** Bilingual (Thanglish - Tamil in English letters + Clean English)  
**Generated At:** 2026-09-05  

---

## Table of Contents
1. [Models System Architecture & Data Flow Map](#1-models-system-architecture--data-flow-map)
2. [Detailed Feature Dissection (8 Core Models Features)](#2-detailed-feature-dissection)
   - [Model Catalog (Model Catalog (AI Models Menu & Inventory)) (/workspace/model-catalog)](#model_catalog)
   - [Model Providers (Model Providers (AI Vendor Credentials & Gateway Settings)) (/workspace/providers)](#model_providers)
   - [Budgets & Limits (Budgets & Limits (Cost Caps & Token Rate Limits)) (/workspace/model-limits)](#model_limits)
   - [Routing Rules (Routing Rules (Intelligent Traffic Steering & Fallbacks)) (/workspace/routing-rules)](#routing_rules)
   - [Complexity Router (Complexity Router (AI Query Triage & Cost Optimizer)) (/workspace/complexity-router)](#complexity_router)
   - [Circuit Breaker (Circuit Breaker (Outage Protection & Auto-Failover)) (/workspace/circuit-breaker)](#circuit_breaker)
   - [Pricing Overrides (Pricing Overrides (Custom Enterprise Rates & Discounts)) (/workspace/custom-pricing/overrides)](#pricing_overrides)
   - [Model Settings (Model Settings (Master Catalog Sync & Recursion Guard)) (/workspace/custom-pricing)](#model_settings)
3. [Cross-Feature Interconnections & Data Flow](#3-cross-feature-interconnections--data-flow)
4. [Tech vs Non-Tech Comparative Matrix](#4-tech-vs-non-tech-comparative-matrix)

---

# 1. Models System Architecture & Data Flow Map
### Muzhumaiyana Models Control Plane & Traffic Steering Flow

```
                     [ INCOMING CLIENT AI REQUEST ]
                                   │
                                   ▼
       ┌───────────────────────────────────────────────────────────┐
       │               FastHTTP PROXY GATEWAY                      │
       │  • Header extraction, API Key validation, Auth checks     │
       └───────────────────────────┬───────────────────────────────┘
                                   │
                                   ▼
       ┌───────────────────────────────────────────────────────────┐
       │            BUDGETS & LIMITS ENFORCEMENT                   │
       │  • Atomic token rate check, Budget threshold verification │
       └─────────────┬───────────────────────────────┬─────────────┘
        (Within Quota)│                               │ (Exceeded)
                     ▼                               ▼
       ┌───────────────────────────┐   ┌───────────────────────────┐
       │    COMPLEXITY ROUTER      │   │  HTTP 429 / Cheaper Model │
       │  • Score: 0.0 - 1.0       │   └───────────────────────────┘
       │  • Simple/Med/Comp/Reason │
       └─────────────┬─────────────┘
                     │
                     ▼
       ┌───────────────────────────┐
       │      ROUTING RULES        │◄─────────────────────────────┐
       │  • CEL Expression Match   │                              │
       │  • Prioritized Target Pool│                              │
       └─────────────┬─────────────┘                              │
                     │                                            │
                     ▼                                            │
       ┌───────────────────────────┐   (Outage / 429 Trip)        │
       │      CIRCUIT BREAKER      │──────────────────────────────┘
       │  • Closed / Open / Half   │   (Instant Fallback Reroute)
       └─────────────┬─────────────┘
                     │ (Healthy)
                     ▼
       ┌───────────────────────────┐
       │      MODEL PROVIDERS      │◄─────── [ MODEL SETTINGS ]
       │  • FastHTTP Client Pool   │          • Live Pricing Sync
       │  • Vault Credentials      │          • Recursion Guard
       └─────────────┬─────────────┘
                     │
                     ▼
       ┌───────────────────────────┐
       │   UPSTREAM LLM VENDORS    │
       │  • OpenAI / Claude / AWS  │
       └─────────────┬─────────────┘
                     │
                     ▼
       ┌───────────────────────────┐
       │     PRICING OVERRIDES     │───────► [ MODEL CATALOG ]
       │  • Contracted Rates ($)   │          • 24h Spend & Usage
       └───────────────────────────┘
```

---

# 2. Detailed Feature Dissection (8 Core Models Features)
### Ettu Features-oda Aazhamana Vivaram (Thanglish + English)

<a name='model_catalog'></a>
## Model Catalog — Model Catalog (AI Models Menu & Inventory)
**UI Route:** `/workspace/model-catalog`

### 👤 Non-Tech Perspective (Makkal Puriyura Mathiri Eliya Vilakkam)
- **Uruvagam (Analogy):** Amazon / Flipkart e-commerce product catalog mathiri allathu restaurant menu card mathiri.
- **Vilakkam (Explanation):** Oru hotel-la menu card pathu enna items irukku, evlo price nu therinjukurathu mathiri, company-la irukkura ellam AI models (GPT-4o, Claude 3.5, Gemini, Llama 3) list, athoda context length, 24-hour traffic, total cost ellame ore idathula pakkalam. Entha model active-ah irukku, ethu custom model nu oru single screen-la paathu choose pannikalam.
- **Business Value (Vaniga Payan):** Team leads and developers entha model available-ah irukku nu therinjukalam. Duplicate and unnecessary models use panni cost waste aaguratha thadukkalam. Organization full-ah AI standardisation kondu varalam.

### 💻 Tech Perspective (Engineers-kaga Technical Architecture)
- **Backend Architecture:** FastHTTP model registry endpoint (`/api/v1/models/catalog`). TanStack Query client caching with real-time token metrics aggregation. Supports filtering by provider, capability flags (vision, audio, tool calling, reasoning), and custom model attributes. Ingests 24-hour aggregated traffic and cost metrics calculated from PostgreSQL telemetry tables.
- **Backend Endpoints:**
  * `GET /api/v1/models/catalog`
  * `GET /api/v1/models/attributes`
  * `PATCH /api/v1/models/{model_id}/attributes`

### 🖥️ Screen Layout & Interactive Elements (Thirai Koorugal & Buttons)
**1. Melpura Koorugal (Top Bar Controls):**
- Summary Cards (4 metrics): Total Providers count, Total Models count, Total Requests (24h), Total Cost (24h $).
- Provider Filter Dropdown: Quick filter by All Providers or specific providers (OpenAI, Anthropic, Bedrock, etc.).
- Tab Switcher: Toggle between 'Overview' tab and 'Attributes' tab.

**2. Mathiya Koorugal & Tables (Tabs & Views):**
- Overview Tab Table: Columns for Provider Name (with icon and custom badge), Models Used (badges with tooltips), Total Traffic 24h, Total Cost 24h ($).
- Attributes Tab Table: Columns for Provider, Model Identifier, Display Name, Description (with hover tooltip for truncated text), Pricing (input/output per 1M tokens), Context Window size (128k, 200k), Max Output Tokens, Actions.
- Search & Pagination: Debounced search input (300ms) across model names, Page offset controls (25 items per page).

**3. Keezhpura Koorugal & Sheets (Bottom Elements & Slide-Overs):**
- AttributeSheet (Slide-Over): Triggered by Edit button to update Display Name, Description, Context Window, Output Tokens, Modality Tags, and Custom Parameters.
- Custom Provider Indicators: Highlight badges for self-hosted or keyless providers.

### 🔗 Connections & Structure Map (Inaippugal)
- **Data-vai Perumidam (Receives From):** Receives provider lists from Model Providers and aggregated usage/cost data from LLM Logs & Dashboard telemetry.
- **Iyakkum Koorugal (Triggers & Affects):** Feeds model choices into Routing Rules, Complexity Router, and Circuit Breaker.

### 💡 Production Use Case: Company-wide AI catalog review to audit which teams are using expensive legacy models (e.g. GPT-4 32k) and migrate them to cost-efficient modern models (e.g. GPT-4o-mini).

---

<a name='model_providers'></a>
## Model Providers — Model Providers (AI Vendor Credentials & Gateway Settings)
**UI Route:** `/workspace/providers`

### 👤 Non-Tech Perspective (Makkal Puriyura Mathiri Eliya Vilakkam)
- **Uruvagam (Analogy):** Telecom SIM card & network provider switchboard mathiri (Airtel, Jio, Vodafone connections configure pandra switchboard).
- **Vilakkam (Explanation):** UnifAI platform vera vera AI vendors-oda (OpenAI, Anthropic, AWS Bedrock, Google Vertex AI, Azure OpenAI, Groq, Ollama) connect aaga thevaiyana API keys, secret credentials, network speed, timeout settings configure pandra control panel. Oru pudhu private AI server (vLLM/Ollama) add pannanum naalum inga simple-ah add pannikalam.
- **Business Value (Vaniga Payan):** Single pane of glass for all AI vendor contracts and credentials. Vendor lock-in thadukkum; enterprise security standards-ku etha mathiri API keys-ah mask panni manage pannalam.

### 💻 Tech Perspective (Engineers-kaga Technical Architecture)
- **Backend Architecture:** Multi-vendor credential management and FastHTTP transport connection pool. Manages custom base URLs, proxy tunnels, exponential backoff retries, request/response payload tracing flags (`send_back_raw_request`, `send_back_raw_response`), and keyless private deployments. Validates connections via instant ping test mutations.
- **Backend Endpoints:**
  * `GET /api/v1/providers`
  * `POST /api/v1/providers`
  * `GET /api/v1/providers/{provider_name}`
  * `PATCH /api/v1/providers/{provider_name}`
  * `DELETE /api/v1/providers/{provider_name}`
  * `POST /api/v1/providers/{provider_name}/keys/test`

### 🖥️ Screen Layout & Interactive Elements (Thirai Koorugal & Buttons)
**1. Melpura Koorugal (Top Bar Controls):**
- Provider Navigation Sidebar: Sorted alphabetical list of configured providers with status badges (Active, Warning, Error).
- Add Provider Dropdown: List of known providers (OpenAI, Anthropic, AWS Bedrock, Azure, Google, Mistral, Groq, Ollama) + 'Add Custom Provider' action.

**2. Mathiya Koorugal & Tables (Tabs & Views):**
- Provider Detail Header: Provider icon, display label, status badge, 'Edit Provider Config' button, and 'Delete Provider' button.
- ModelProviderKeysTableView: Table displaying API Key Name, Masked Key Secret, Quota Limit, Key Status, Connection Ping Test button, and Delete Key button.
- ProviderGovernanceTable: Governance rules and access policies tied specifically to this vendor.

**3. Keezhpura Koorugal & Sheets (Bottom Elements & Slide-Overs):**
- ProviderConfigSheet: Slide-over form configuring Concurrency Limits, Buffer Size, Network Config (Request Timeout ms, Max Retries, Retry Delay), Proxy URL, and Raw Payload Toggles.
- AddCustomProviderSheet: Form to configure custom / self-hosted provider names, base URL endpoints (e.g. `http://internal-vllm:8000/v1`), and Keyless Mode toggle.

### 🔗 Connections & Structure Map (Inaippugal)
- **Data-vai Perumidam (Receives From):** Receives API keys and network configurations from administrators.
- **Iyakkum Koorugal (Triggers & Affects):** Powers all outbound AI traffic through FastHTTP Proxy; supplies connection clients to Routing Rules and Circuit Breaker.

### 💡 Production Use Case: Zero-downtime rotation of compromised OpenAI production keys and setting up private on-premise Ollama instances for confidential internal documents.

---

<a name='model_limits'></a>
## Budgets & Limits — Budgets & Limits (Cost Caps & Token Rate Limits)
**UI Route:** `/workspace/model-limits`

### 👤 Non-Tech Perspective (Makkal Puriyura Mathiri Eliya Vilakkam)
- **Uruvagam (Analogy):** Credit card limit and bank daily withdrawal limit mathiri.
- **Vilakkam (Explanation):** AI use panna panna bill laatchakanakula aagira koodathu nu, ovvoru team-kum, user-kum, allathu ovvoru AI model-kum monthly budget ($500) allathu daily token limit set pandra edham. Limit reach aana udane automated warning email varum, allathu request-ah block panni bill shock varama thadukkum.
- **Business Value (Vaniga Payan):** 100% financial safety and budget predictability. Rogue scripts allathu infinite loop bugs naala laksha kanakkula bill varatha prevent pannum.

### 💻 Tech Perspective (Engineers-kaga Technical Architecture)
- **Backend Architecture:** High-throughput token bucket rate limiter and budget enforcer middleware. Atomic Redis / PostgreSQL counters (`INCRBY`). Evaluates requests against multi-tiered governance limits (Global, Virtual Key, User, Team). Supports sliding rolling windows and calendar-month alignments. Pre-flight evaluation rejects requests with HTTP 429 or routes to a cheaper fallback model.
- **Backend Endpoints:**
  * `GET /api/v1/governance/model-limits`
  * `POST /api/v1/governance/model-limits`
  * `PUT /api/v1/governance/model-limits/{limit_id}`
  * `DELETE /api/v1/governance/model-limits/{limit_id}`

### 🖥️ Screen Layout & Interactive Elements (Thirai Koorugal & Buttons)
**1. Melpura Koorugal (Top Bar Controls):**
- Create Model Limit Button: Opens the limit configuration sheet.
- Search Input: Quick search across model names and entity targets.
- Filter Dropdowns: Filter by Provider and by Governance Scope (Global, Virtual Key, User, Team/User Group).

**2. Mathiya Koorugal & Tables (Tabs & Views):**
- Model Limits Table: Columns for Scope Badge, Target Entity, Provider, Model, Budget Progress Bar (Current Spend $ vs Limit $), Token Progress Bar (Used vs Max Tokens), Reset Cadence, Actions Menu.
- Visual Progress Bars: Color-coded usage indicators (green < 70%, orange 70-90%, red > 90%).

**3. Keezhpura Koorugal & Sheets (Bottom Elements & Slide-Overs):**
- ModelLimitSheet (Modal/Slide-over): Configure Scope, Entity Target, Provider/Model, Max Budget ($), Max Tokens, Reset Duration (Daily, Weekly, Monthly, Rolling Window, Calendar-aligned).
- Threshold Alert Rules: Email/Slack webhook triggers on 80% warning and 100% hard limit block.

### 🔗 Connections & Structure Map (Inaippugal)
- **Data-vai Perumidam (Receives From):** Calculates spend using live rates from Pricing Overrides and real-time usage from LLM Logs.
- **Iyakkum Koorugal (Triggers & Affects):** Enforces rate-limits on Virtual Keys and blocks/reroutes calls in FastHTTP Proxy when budgets are exhausted.

### 💡 Production Use Case: Giving intern developers a strict $30/month budget cap while giving the production customer-facing app an elastic $5,000 budget.

---

<a name='routing_rules'></a>
## Routing Rules — Routing Rules (Intelligent Traffic Steering & Fallbacks)
**UI Route:** `/workspace/routing-rules`

### 👤 Non-Tech Perspective (Makkal Puriyura Mathiri Eliya Vilakkam)
- **Uruvagam (Analogy):** Railway track switcher mathiri (Train-ah thevaikku thagundha track-la thiruppi vidura mechanism).
- **Vilakkam (Explanation):** Oru customer request varum pothu, athu entha AI model-ku poganum nu rules poduvom. Example: Customer 'Enterprise User'-ah iruntha super-fast GPT-4o-ku poganum; 'Free User'-ah iruntha cheap Claude 3.5 Haiku-ku poganum. Oru model slow aana automatic-ah adutha model-ku route pannum.
- **Business Value (Vaniga Payan):** Customized user experience; customer tier-ku thagundha mathiri AI quality allocate pannalam; 100% dynamic load balancing.

### 💻 Tech Perspective (Engineers-kaga Technical Architecture)
- **Backend Architecture:** CEL (Common Expression Language) evaluation engine written in Go. Compiles and executes deterministic conditions against request headers (`x-uf-*`), prompt metadata, caller identity, and token lengths. Directs requests to target pools supporting priority weights, fallback arrays, and regional data residency constraints.
- **Backend Endpoints:**
  * `GET /api/v1/routing-rules`
  * `POST /api/v1/routing-rules`
  * `PATCH /api/v1/routing-rules/{rule_id}`
  * `DELETE /api/v1/routing-rules/{rule_id}`

### 🖥️ Screen Layout & Interactive Elements (Thirai Koorugal & Buttons)
**1. Melpura Koorugal (Top Bar Controls):**
- Create Routing Rule Button: Opens rule creation sheet.
- Search Input: Filter rules by name and condition.
- Priority Sort: Order rules by evaluation priority hierarchy.

**2. Mathiya Koorugal & Tables (Tabs & Views):**
- Routing Rules Table: Columns for Rule Name, Priority Badge (High/Med/Low), CEL Condition Expression (syntax highlighted), Target Model & Provider, Enabled Toggle Switch (instant activation without restart), Actions.
- Visual Rule Tree View: Interactive node graph showing incoming traffic splitting across matching condition branches to final destination targets.

**3. Keezhpura Koorugal & Sheets (Bottom Elements & Slide-Overs):**
- RoutingRuleSheet: Rule builder with Name, Priority slider (1-100), Visual Condition Builder / Raw CEL editor (e.g. `request.headers['x-tier'] == 'gold' && prompt.tokens > 500`), Target Provider/Model selection, and Fallback Chain priority list.
- RoutingRuleInfoSheet: Detailed execution metrics and audit history for individual rules.

### 🔗 Connections & Structure Map (Inaippugal)
- **Data-vai Perumidam (Receives From):** Evaluates incoming FastHTTP requests and integrates with Complexity Router tiers.
- **Iyakkum Koorugal (Triggers & Affects):** Selects the upstream provider connection from Model Providers and cooperates with Circuit Breaker during outages.

### 💡 Production Use Case: Routing all European customer requests (`request.headers['cf-ipcountry'] in ['DE', 'FR', 'UK']`) exclusively to EU-based Azure OpenAI endpoints for GDPR compliance.

---

<a name='complexity_router'></a>
## Complexity Router — Complexity Router (AI Query Triage & Cost Optimizer)
**UI Route:** `/workspace/complexity-router`

### 👤 Non-Tech Perspective (Makkal Puriyura Mathiri Eliya Vilakkam)
- **Uruvagam (Analogy):** Hospital Triage System mathiri (General fever-ku junior doctor, heart surgery-ku senior specialist kitta anuppura mathiri).
- **Vilakkam (Explanation):** Simple-ana kelvi ('Hi', 'What is the capital of India?') ketta romba costly-ana GPT-4o thevailla, athukku fast & cheap-ana GPT-4o-mini pothum. Aana periya complex coding allathu math problem ketta mattum o1 allathu Claude Opus-ku automatic-ah anupum. Ithanaala quality kuraama 70% AI bill automatic-ah micham aagum!
- **Business Value (Vaniga Payan):** Massive cost reduction (up to 70% savings) with zero compromise on accuracy. Cheap models handle 80% of volume, expensive models handle 20% complex tasks.

### 💻 Tech Perspective (Engineers-kaga Technical Architecture)
- **Backend Architecture:** Multi-factor prompt complexity analysis engine. Calculates a continuous complexity score (0.0 to 1.0) using token length heuristics, vocabulary entropy, code-syntax regex detectors (`def`, `class`, `import`, `function`), and keyword weighting. Maps the score into 4 discrete tiers: `SIMPLE`, `MEDIUM`, `COMPLEX`, `REASONING`.
- **Backend Endpoints:**
  * `GET /api/v1/governance/complexity-analyzer`
  * `PUT /api/v1/governance/complexity-analyzer`
  * `POST /api/v1/governance/complexity-analyzer/reset`

### 🖥️ Screen Layout & Interactive Elements (Thirai Koorugal & Buttons)
**1. Melpura Koorugal (Top Bar Controls):**
- Save Configuration Button: Commits threshold and keyword changes with active loading spinner.
- Reset to Defaults Button (RotateCcw): Restores factory recommended boundary scores.
- Docs Link: External link to complexity routing documentation.

**2. Mathiya Koorugal & Tables (Tabs & Views):**
- Progressive okLCH Palette Visualization: Interactive color-coded spectrum showing the 4 tiers: SIMPLE (faint primary), MEDIUM (medium primary), COMPLEX (strong primary), REASONING (full primary).
- Tier Boundary Inputs: Numerical score inputs for `Simple → Medium` (e.g. 0.25), `Medium → Complex` (e.g. 0.60), and `Complex → Reasoning` (e.g. 0.85).
- Keyword List Management (TagInput): Tag inputs for Code Keywords (sql, regex, docker), Reasoning Keywords (prove, theorem, analyze), and Simple Keywords (hello, summarize).

**3. Keezhpura Koorugal & Sheets (Bottom Elements & Slide-Overs):**
- Tier Target Model Selectors: Map each tier to a default provider & model (e.g., Simple -> GPT-4o-mini, Medium -> Claude 3.5 Haiku, Complex -> Sonnet, Reasoning -> o1).
- Test Prompt Sandbox: Real-time interactive prompt tester calculating live complexity scores.

### 🔗 Connections & Structure Map (Inaippugal)
- **Data-vai Perumidam (Receives From):** Intercepts incoming requests from FastHTTP proxy before Routing Rules evaluation.
- **Iyakkum Koorugal (Triggers & Affects):** Assigns target model tier, overrides requested models, and logs complexity classification into LLM Logs.

### 💡 Production Use Case: Customer support automation where 85% routine lookup queries are handled at 1/20th the cost by lightweight models, and 15% technical issues go to deep reasoning models.

---

<a name='circuit_breaker'></a>
## Circuit Breaker — Circuit Breaker (Outage Protection & Auto-Failover)
**UI Route:** `/workspace/circuit-breaker`

### 👤 Non-Tech Perspective (Makkal Puriyura Mathiri Eliya Vilakkam)
- **Uruvagam (Analogy):** Veetla irukkura Electric MCB / Fuse mathiri (High voltage allathu short circuit aana fuse off aagi appliances-ah kaapathum).
- **Vilakkam (Explanation):** OpenAI allathu Anthropic server crash aanaallathu rate limit aagi error vantha, user-ku error screen kaatama, automatic-ah fraction of second-la backup model-ku (e.g. AWS Bedrock allathu Azure)-ku traffic-ah switch panni system-ah 24x7 non-stop-ah run panna vaikkum.
- **Business Value (Vaniga Payan):** 99.99% Enterprise High Availability. Vendor downtime aanaalum business apps oru second kooda stop aagathu.

### 💻 Tech Perspective (Engineers-kaga Technical Architecture)
- **Backend Architecture:** Distributed Circuit Breaker finite state machine (Closed -> Open -> Half-Open). Monitored via real-time polling (`pollingInterval: 8000ms`). Detects provider rate-limit response headers (e.g. `x-ratelimit-remaining: 0`), HTTP 429/503 status codes, and network timeouts. When tripped, instantly redirects calls to secondary fallback provider with automated cooldown probing.
- **Backend Endpoints:**
  * `GET /api/v1/circuit-breaker/policies`
  * `POST /api/v1/circuit-breaker/policies`
  * `PUT /api/v1/circuit-breaker/policies/{name}`
  * `DELETE /api/v1/circuit-breaker/policies/{name}`
  * `GET /api/v1/circuit-breaker/state`
  * `POST /api/v1/circuit-breaker/policies/{name}/reset`

### 🖥️ Screen Layout & Interactive Elements (Thirai Koorugal & Buttons)
**1. Melpura Koorugal (Top Bar Controls):**
- Header Title with Shield Icon: Visual indicator of active failover protection.
- Create Policy Button: Opens the circuit breaker policy creation dialog.

**2. Mathiya Koorugal & Tables (Tabs & Views):**
- Circuit Breaker Policies Table: Columns for Policy Name, Primary Provider & Model, Fallback Provider & Model, Trigger Condition Signals, Cooldown Duration (e.g. 30s), Circuit State Badge (Closed [green], Open [red], Half-Open [yellow]), Actions Menu.
- Live State Indicators: Polled every 8 seconds displaying active tripped circuits and error counts.

**3. Keezhpura Koorugal & Sheets (Bottom Elements & Slide-Overs):**
- Circuit Policy Dialog: Form configuring Policy Name, Enabled Switch, Primary Provider/Model comboboxes, Fallback Provider/Model comboboxes, Response Header Signal matchers, and Cooldown Duration.
- Manual Circuit Reset Button (RotateCcw): Instantly resets a tripped circuit back to Closed status.

### 🔗 Connections & Structure Map (Inaippugal)
- **Data-vai Perumidam (Receives From):** Monitors HTTP response headers and error codes from FastHTTP Proxy during provider execution.
- **Iyakkum Koorugal (Triggers & Affects):** Reroutes failed requests to fallback providers and dispatches incident alerts to Alert Channels.

### 💡 Production Use Case: Preventing application outage when OpenAI experiences global HTTP 503 outage on Cyber Monday by instantly switching all traffic to Azure OpenAI.

---

<a name='pricing_overrides'></a>
## Pricing Overrides — Pricing Overrides (Custom Enterprise Rates & Discounts)
**UI Route:** `/workspace/custom-pricing/overrides`

### 👤 Non-Tech Perspective (Makkal Puriyura Mathiri Eliya Vilakkam)
- **Uruvagam (Analogy):** Special corporate discount allathu wholesale negotiated price contract mathiri.
- **Vilakkam (Explanation):** OpenAI website-la 1 million token-ku $5 nu official price irunthaalum, unga company-ku special enterprise discount allathu committed spend agreement iruntha, antha custom rate-ah inga enter pannikalam. Athuku thagundha mathiri unga internal dashboard-la exact real spend calculate aagum.
- **Business Value (Vaniga Payan):** 100% accurate financial chargeback and departmental billing. True profit margin calculations based on actual vendor contracts rather than list prices.

### 💻 Tech Perspective (Engineers-kaga Technical Architecture)
- **Backend Architecture:** Multi-tier hierarchical pricing resolution engine. Precedence hierarchy: (1) Virtual Key Override -> (2) User / Team Override -> (3) Provider Global Override -> (4) Default Provider Catalog. Calculates input token cost, cached prompt discount, output token cost, reasoning token multiplier, and fixed per-call fee.
- **Backend Endpoints:**
  * `GET /api/v1/pricing/overrides`
  * `POST /api/v1/pricing/overrides`
  * `PUT /api/v1/pricing/overrides/{override_id}`
  * `DELETE /api/v1/pricing/overrides/{override_id}`

### 🖥️ Screen Layout & Interactive Elements (Thirai Koorugal & Buttons)
**1. Melpura Koorugal (Top Bar Controls):**
- Add Pricing Override Button: Opens override creation sheet.
- Search Input: Search by model name or provider.
- Scope Filter: Filter by Global, Virtual Key, or User Group.

**2. Mathiya Koorugal & Tables (Tabs & Views):**
- Pricing Overrides Table: Columns for Scope Badge, Target Entity, Provider, Model, Input Cost (per 1M tokens), Cached Input Cost, Output Cost (per 1M tokens), Fixed Request Fee, Actions.
- Precision Display: Formats currency values up to 6 decimal places ($0.000000).

**3. Keezhpura Koorugal & Sheets (Bottom Elements & Slide-Overs):**
- PricingOverrideSheet (Slide-Over): Modal to configure Scope, Provider, Model, and granular token pricing via `PricingFieldSelector`.
- PricingFieldSelector: Dedicated inputs for Prompt Tokens ($/1M), Cached Input Tokens ($/1M), Output Tokens ($/1M), and Per-Request Invocation Surcharge.

### 🔗 Connections & Structure Map (Inaippugal)
- **Data-vai Perumidam (Receives From):** Configured by finance administrators based on legal contracts.
- **Iyakkum Koorugal (Triggers & Affects):** Supplies live pricing equations to Dashboard charts, LLM Logs cost calculation, and Budgets & Limits enforcer.

### 💡 Production Use Case: Applying AWS 25% EDP (Enterprise Discount Program) discount to Bedrock Claude models so billing matches actual monthly AWS invoices.

---

<a name='model_settings'></a>
## Model Settings — Model Settings (Master Catalog Sync & Recursion Guard)
**UI Route:** `/workspace/custom-pricing`

### 👤 Non-Tech Perspective (Makkal Puriyura Mathiri Eliya Vilakkam)
- **Uruvagam (Analogy):** Global system clock & master registry synchronizer mathiri.
- **Vilakkam (Explanation):** Market-la puthu puthu AI models varum pothu, athoda official pricing automatic-ah download aagi update aaga thevaiyana master website link, sync frequency (24 hours), mathum routing rules-la infinite loop vanthu server hang aagidama thadukkura max depth settings configure pandra edham.
- **Business Value (Vaniga Payan):** Zero-maintenance operations. New AI models and price reductions are synced automatically without engineering code changes or redeployments.

### 💻 Tech Perspective (Engineers-kaga Technical Architecture)
- **Backend Architecture:** Core system configuration manager. Manages `framework_config` and `client_config` tables in PostgreSQL. Orchestrates asynchronous cron workers to fetch remote pricing datasheets (CSV/JSON), parses token schemas, and invalidates in-memory caches. Enforces `routing_chain_max_depth` to prevent circular fallback loops in routing rules.
- **Backend Endpoints:**
  * `GET /api/v1/config/core`
  * `PUT /api/v1/config/core`
  * `POST /api/v1/config/pricing/sync`

### 🖥️ Screen Layout & Interactive Elements (Thirai Koorugal & Buttons)
**1. Melpura Koorugal (Top Bar Controls):**
- Header Title: Model Settings & Global Synchronization.
- Dirty State Tracker: Highlights unsaved changes with save prompt.

**2. Mathiya Koorugal & Tables (Tabs & Views):**
- ModelSettingsView Form:
- • Pricing Datasheet URL Input: Remote CSV/JSON endpoint for automatic pricing ingestion.
- • Pricing Sync Interval Input (Hours): Automated background sync cadence (default: 24h).
- • Model Parameters URL Input: Global repository link defining context sizes and modality capabilities.
- • Routing Chain Max Depth Slider/Input: Maximum recursive hops allowed across fallback chains (default: 5).

**3. Keezhpura Koorugal & Sheets (Bottom Elements & Slide-Overs):**
- Force Pricing Sync Now Button: Triggers immediate background worker ingestion with loading spinner.
- Save Configuration Button: Commits configuration updates to core PostgreSQL storage.

### 🔗 Connections & Structure Map (Inaippugal)
- **Data-vai Perumidam (Receives From):** Receives administrative inputs and connects to external UnifAI pricing telemetry feeds.
- **Iyakkum Koorugal (Triggers & Affects):** Updates foundational pricing data for Model Catalog and enforces maximum recursion depth across Routing Rules.

### 💡 Production Use Case: Instantly ingesting OpenAI's latest 50% price reduction across 30 enterprise models with a single click of 'Force Pricing Sync Now'.

---

# 3. Cross-Feature Interconnections & Data Flow
### Models Features Kulla Irukura Direct Connections

| Source Feature | Connected To | Data Flow & Trigger Action |
| :--- | :--- | :--- |
| **Model Catalog** | **Routing Rules** | Provides validated provider & model identifiers for rule destination targets. |
| **Model Providers** | **FastHTTP Proxy** | Supplies decrypted API keys, custom base URLs, and connection pools for HTTP calls. |
| **Budgets & Limits** | **Virtual Keys** | Enforces strict dollar and token quotas on client applications and API keys. |
| **Routing Rules** | **Circuit Breaker** | Cooperates during provider outages to bypass broken routes and execute fallbacks. |
| **Complexity Router** | **Model Providers** | Directs simple queries to lightweight models and complex queries to reasoning models. |
| **Circuit Breaker** | **Alert Channels** | Triggers immediate Slack/PagerDuty alerts when a primary provider circuit trips. |
| **Pricing Overrides** | **Dashboard & Logs** | Injects contracted enterprise prices into real-time spend calculations. |
| **Model Settings** | **Model Catalog** | Automatically syncs latest global model capabilities and prevents routing recursion loops. |

---

# 4. Tech vs Non-Tech Comparative Matrix
### Thozhilnutpam vs Vanigam Parvai Oppeedo

| Feature | Non-Tech View (Manager / CFO Parvai) | Tech View (DevOps / Architect Parvai) |
| :--- | :--- | :--- |
| **Model Catalog** | "Entha entha AI models namakku irukku? Ethu active-ah irukku?" | "Model metadata schema, capability flags (vision, audio), and 24h usage telemetry." |
| **Model Providers** | "AI companies-oda API keys and accounts ellam safe-ah connect aagiyirukka?" | "FastHTTP client pools, exponential retry backoffs, proxy tunnels, and raw payload tracing." |
| **Budgets & Limits** | "Entha team-kum excessive bill varama budget control-la irukka?" | "Atomic Redis/Postgres token bucket counters, sliding windows, and HTTP 429 rate limiters." |
| **Routing Rules** | "Customer tier-ku thagundha mathiri correct model-ku request pogutha?" | "CEL (Common Expression Language) engine evaluating request headers and metadata in Go." |
| **Complexity Router** | "Simple kelvikku cheap model, tough kelvikku matum costly model use panni 70% bill micham aagutha?" | "Heuristic multi-factor complexity scoring engine categorizing queries into 4 distinct tiers." |
| **Circuit Breaker** | "OpenAI crash aanaal kooda customer-ku error theriyaama backup model-ku switch aagutha?" | "Distributed finite state machine (Closed/Open/Half-Open) with automated header signal polling." |
| **Pricing Overrides** | "Namma negotiate panna special discount price-la dashboard calculate aagutha?" | "Multi-tier hierarchical pricing precedence engine applying custom token multipliers." |
| **Model Settings** | "Pudhu AI models and price cuts automatic-ah update aagutha?" | "Postgres core config manager with automated background sync workers and recursion guard." |
