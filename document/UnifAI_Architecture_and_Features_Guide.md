# UnifAI Enterprise Architecture, Headers & Features Master Guide
## விரிவான கணினி கட்டமைப்பு, ஹெடர்ஸ் மற்றும் 38 அம்சங்களின் முழுமையான கையேடு (Tamil & English Technical Manual)

**Document Version:** 2.0 (Enterprise Edition)  
**Classification:** Complete Technical Architecture & System Engineering Manual  
**Generated At:** 2026-09-05  
**Platform:** UnifAI Unified AI Gateway & Governance Control Plane  

---

## Table of Contents (பொருளடக்கம்)
1. [Executive Summary & Platform Overview (செயல் சுருக்கம்)](#1-executive-summary--platform-overview)
2. [End-to-End Request Lifecycle & System Architecture (கோரிக்கை வாழ்க்கைச் சுழற்சி)](#2-end-to-end-request-lifecycle--system-architecture)
3. [Exhaustive HTTP Headers Reference Guide (ஹெடர்ஸ் முழு விவரக் கையேடு)](#3-exhaustive-http-headers-reference-guide)
   - Authentication & Identity Headers (அடையாளம் & பாதுகாப்பு)
   - Intelligent Routing & Model Steering Headers (ரூட்டிங் & மாடல் தேர்வு)
   - Semantic Caching & Performance Headers (கேச்சிங் & லேடன்சி குறைப்பு)
   - MCP (Model Context Protocol) & Tool Headers (டூல்ஸ் பயன்பாடு)
   - Observability, Tracing & Debugging Headers (கண்காணிப்பு & பிழைத்திருத்தம்)
   - Gateway Response Headers (UnifAI திருப்பி அனுப்பும் Headers)
4. [In-Depth Feature Catalog (7 Core Pillars - 38 Features)](#4-in-depth-feature-catalog)
   - Pillar 1: Observability (முழுமையான கண்காணிப்பு & செயல்திறன்)
     * Dashboard (`/workspace/dashboard`)
     * LLM Logs (`/workspace/logs`)
     * MCP Logs (`/workspace/mcp-logs`)
     * Browser AI (`/workspace/browser-ai`)
     * Connectors (`/workspace/observability`)
     * Logs Settings (`/workspace/config/logging`)
   - Pillar 2: Models & Intelligent Routing (மாடல் மேலாண்மை & ரூட்டிங்)
     * Model Catalog (`/workspace/model-catalog`)
     * Model Providers (`/workspace/providers`)
     * Budgets & Limits (`/workspace/model-limits`)
     * Routing Rules (`/workspace/routing-rules`)
     * Complexity Router (`/workspace/complexity-router`)
     * Circuit Breaker (`/workspace/circuit-breaker`)
     * Pricing Overrides (`/workspace/custom-pricing/overrides`)
     * Model Settings (`/workspace/custom-pricing`)
   - Pillar 3: MCP Gateway (டூல்ஸ் & ஏஜென்ட்கள் - Model Context Protocol)
     * MCP Catalog (`/workspace/mcp-registry`)
     * MCP Library (`/workspace/mcp-registry/library`)
     * Tool Groups (`/workspace/mcp-tool-groups`)
     * Auth Sessions (`/workspace/mcp-sessions`)
     * OAuth Grants (`/workspace/oauth-grants`)
     * MCP Settings (`/workspace/mcp-settings`)
     * Plugins (`/workspace/plugins`)
   - Pillar 4: Governance & Enterprise Compliance (அணுகல் கட்டுப்பாடு & பாதுகாப்பு)
     * Virtual Keys (`/workspace/governance/virtual-keys`)
     * Users (`/workspace/governance/users`)
     * Teams (`/workspace/governance/teams`)
     * Business Units (`/workspace/governance/business-units`)
     * Customers (`/workspace/governance/customers`)
     * User Provisioning (SCIM) (`/workspace/scim`)
     * Roles & Permissions (RBAC) (`/workspace/governance/rbac`)
     * Access Profiles (`/workspace/governance/access-profiles`)
     * Audit Logs (`/workspace/audit-logs`)
   - Pillar 5: Guardrails & Content Security (உள்ளடக்கப் பாதுகாப்பு & கொள்கை)
     * Rules (`/workspace/guardrails/configuration`)
     * Providers (`/workspace/guardrails/providers`)
     * Cluster Config (`/workspace/cluster`)
   - Pillar 6: Adaptive Routing & Assets (ஸ்மார்ட் தேர்வு & அறிவு களஞ்சியம்)
     * Adaptive Routing Dashboard & Settings (`/workspace/adaptive-routing`)
     * Prompt Repository (`/workspace/prompt-repo`)
     * Skills Repository (`/workspace/skills-repo`)
   - Pillar 7: Global Settings & Engine Tuning (கட்டமைப்பு & செயல்திறன் ட்யூனிங்)
     * Client Settings (`/workspace/config/client-settings`)
     * Compatibility (`/workspace/config/compatibility`)
     * Caching (Semantic Cache) (`/workspace/config/caching`)
     * Security (`/workspace/config/security`)
     * API Keys (`/workspace/config/api-keys`)
     * Performance Tuning (`/workspace/config/performance-tuning`)
     * Feature Flags (`/workspace/config/feature-flags`)
     * Enterprise Outbound Proxy (`/workspace/config/proxy`)
     * Large Payload Streaming Engine (`/workspace/config/large-payload`)
     * Alert Channels (Enterprise Notifications) (`/workspace/alert-channels`)
     * MCP Authentication Config & Credential Vault (`/workspace/mcp-auth-config`)
     * Starlark Sandboxed Code Mode (`core/mcp/codemode/starlark`)
     * Hardware Secrets Vault & Envelope Encryption (`core/schemas/vault.go`)
     * Key Load Balancer & Key Pool Filtering (`framework/loadbalancer`)
     * Realtime Audio & Voice Gateway (`core/schemas/realtime.go`)
5. [Cross-Feature Interconnection & Data Flow Matrix (இணைப்பு வரைபடம்)](#5-cross-feature-interconnection--data-flow-matrix)
6. [Technology Stack & Programming Languages Deep Dive (தொழில்நுட்ப கட்டமைப்பு)](#6-technology-stack--programming-languages-deep-dive)
7. [Enterprise Production Scenarios & Playbooks (நடைமுறை பயன்பாடுகள்)](#7-enterprise-production-scenarios--playbooks)

---

# 1. Executive Summary & Platform Overview
### செயல் சுருக்கம் & தளம் கண்ணோட்டம்

UnifAI is a high-performance, enterprise-grade **Unified AI Gateway, Router, Governance, Guardrails, and Observability Control Plane**. In modern enterprises, AI consumption is fragmented across multiple vendors (OpenAI, Anthropic Claude, Google Gemini, AWS Bedrock, Mistral, Groq, and self-hosted Ollama/vLLM models). This fragmentation causes unpredictable billing, compliance risks, security vulnerabilities, and vendor lock-in.

UnifAI unifies all LLM and agentic interactions behind a single, resilient gateway delivering:

1. **Cost Optimization (செலவு குறைப்பு):** Up to 80% cost reduction via **Complexity Routing** and **Semantic Caching**.
2. **High Availability (99.99% அப்டைம்):** Instant automated failover via **Circuit Breaker** to backup providers during cloud outages.
3. **Enterprise Governance (அணுகல் கட்டுப்பாடு):** Virtual Keys (`sk-uf-*`), granular RBAC, multi-tenant customer scoping, and team budgets.
4. **Content Safety & DLP (உள்ளடக்கப் பாதுகாப்பு):** Input and output inspection (PII masking, prompt injection defense) via Google CEL rules and Presidio DLP.
5. **Agentic Extensibility (டூல்ஸ் பயன்பாடு):** Model Context Protocol (MCP) gateway managing curated tool libraries and OAuth user sessions.
6. **Real-time Observability (முழுமையான கண்காணிப்பு):** Sub-millisecond logging, live metrics dashboard, and streaming connectors to Datadog, Kafka, and BigQuery.

# 2. End-to-End Request Lifecycle & System Architecture
### கோரிக்கை வாழ்க்கைச் சுழற்சி & கணினி கட்டமைப்பு

```
[ CLIENT APPLICATION / SDK / BROWSER AI ]
                   │
                   ▼  (1) HTTP Request with `x-uf-vk: sk-uf-...` & JSON Body
┌────────────────────────────────────────────────────────────────────────┐
│ 1. TRANSPORT & GOVERNANCE LAYER                                        │
│ • FastHTTP router parses headers and TLS connection                    │
│ • Virtual Key (`sk-uf-*`) validated against PostgreSQL / memory cache   │
│ • Verify User, Team, Business Unit, and Customer membership             │
│ • Enforce Rate Limits (RPM, TPM) & Financial Monthly Budgets           │
│ • Verify Access Profile (allowed models & allowed MCP tool groups)     │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   ▼  (2) Authorized Context
┌────────────────────────────────────────────────────────────────────────┐
│ 2. PRE-LLM GUARDRAILS & SAFETY LAYER                                   │
│ • Evaluate Google CEL (Common Expression Language) Rules               │
│ • Provider scan: Presidio DLP (PII redaction), Llama Guard, Regex      │
│ • Prompt Injection & Jailbreak detection                               │
│ • Short-circuit with 400 Bad Request if policy violated                │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   ▼  (3) Safe, Sanitized Prompt
┌────────────────────────────────────────────────────────────────────────┐
│ 3. SEMANTIC CACHING LAYER                                              │
│ • Generate vector embedding of prompt or exact SHA256 key              │
│ • Search Qdrant / PgVector / Redis cache partition (`x-uf-cache-key`)   │
│ • If Cosine Similarity >= Threshold (`x-uf-cache-threshold`):          │
│   ───► [CACHE HIT] Return cached response directly (Latency < 20ms)    │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   ▼  (4) Cache Miss -> Needs LLM
┌────────────────────────────────────────────────────────────────────────┐
│ 4. INTELLIGENT ROUTING & LOAD BALANCING LAYER                          │
│ • Complexity Router analyzes prompt (Simple, Medium, Complex, Reason)   │
│ • Routing Rules match CEL conditions (tier, department, tags)          │
│ • Adaptive Router checks real-time latency & error rate weights        │
│ • Circuit Breaker checks provider health; routes to fallback if down   │
│ • Resolved target model & provider determined                          │
└──────────────────┬────────────────────────────────┬────────────────────┘
                   ▼                                ▼
┌────────────────────────────────────┐ ┌─────────────────────────────────┐
│ 5A. UPSTREAM LLM PROVIDER          │ │ 5B. MCP GATEWAY EXECUTION       │
│ • OpenAI, Anthropic, Bedrock, etc. │ │ • Model Context Protocol Tools  │
│ • API key from rotation pool       │ │ • OAuth token session injected  │
│ • Streaming SSE / Full response    │ │ • Sandboxed Starlark execution  │
└──────────────────┬─────────────────┘ └────────────────┬────────────────┘
                   └────────────────┬───────────────────┘
                                    ▼  (5) Raw Generated AI Output
┌────────────────────────────────────────────────────────────────────────┐
│ 6. POST-LLM GUARDRAILS & OUTPUT FILTERING                              │
│ • Scan response for hallucinated credentials or toxic outputs          │
│ • PII masking on generated text before sending to client               │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   ▼  (6) Final Validated Response
┌────────────────────────────────────────────────────────────────────────┐
│ 7. OBSERVABILITY, METRICS & TELEMETRY                                  │
│ • Append complete record to LLM Logs & MCP Logs                        │
│ • Calculate exact token cost via Pricing Overrides                     │
│ • Update real-time Metrics Dashboard via WebSockets                    │
│ • Stream telemetry event to Connectors (Datadog, Kafka, BigQuery, OTel)│
│ • Attach `x-unifai-*` response headers and return HTTP 200 OK to Client│
└────────────────────────────────────────────────────────────────────────┘
```

# 3. Exhaustive HTTP Headers Reference Guide
### ஹெடர்ஸ் முழு விவரக் கையேடு

Headers allow fine-grained control over routing, caching, security, debugging, and logging per request without altering the JSON body.

## Authentication & Identity Headers (அடையாளம் & பாதுகாப்பு)

| Header Name | Sample Value | Data Type | Description (English) | விளக்கம் (Tamil) |
| :--- | :--- | :--- | :--- | :--- |
| `x-uf-vk` | `sk-uf-prod_corp_a91b2c3d4e` | String (Virtual Key) | UnifAI Virtual Key representing synthetic API credentials. Binds the caller to an authorized Team, User, Budget Quota, Access Profile, and MCP Tool Groups. | Virtual Key மூலமாக client அங்கீகரிக்கப்படுகிறது. Upstream provider keys மறைக்கப்பட்டு, பட்ஜெட் மற்றும் அனுமதிகள் இதனுடன் இணைக்கப்படும். |
| `Authorization` | `Bearer sk-uf-prod_corp_a91b2c3d4e` | Standard Header | Standard HTTP Authorization header alternative for OpenAI SDK compatibility. Automatically parsed as a Virtual Key if prefixed with 'sk-uf-'. | OpenAI SDK பயன்படுத்தும்போது 'x-uf-vk'-க்கு மாற்றாக standard Bearer token வடிவத்தில் Virtual Key-ஐ அனுப்பலாம். |
| `x-uf-api-key` | `key_adm_89f0a21bc9e4` | String (Admin Key) | Platform Control Plane Administrative API Key. Authorizes access to administrative CRUD endpoints (creating keys, editing routing rules, cluster sync). | UnifAI நிர்வாக API-களை அணுக பயன்படும் Platform Admin Key. புதிய ரூல்ஸ், மாடல்கள் மற்றும் கீகளை உருவாக்க உதவும். |
| `x-uf-customer-id` | `cust_enterprise_7710` | String (UUID/Slug) | Tenant / Customer scoping key for B2B multi-tenant SaaS applications. Routes usage, token consumption, and dollar spend to a specific end-customer account under a shared team virtual key. | B2B SaaS செயலிகளில், எந்த இறுதி வாடிக்கையாளர் (End Customer) இந்த request-ஐ அனுப்புகிறார் என பிரித்து Cost & Analytics track செய்ய உதவும். |
| `x-uf-customer-name` | `Acme Corporation Global` | String (Human Name) | Display name for the customer tenant, populated in audit records, billing statements, and telemetry dashboards alongside x-uf-customer-id. | வாடிக்கையாளரின் பெயர். Audit logs மற்றும் பில்லிங் அறிக்கைகளில் எளிதாக அடையாளம் காண பயன்படுகிறது. |
| `x-uf-direct-key` | `true / false` | Boolean Flag | Direct Key Pass-Through. When set to 'true', UnifAI bypasses its internal key pool and uses the raw provider key supplied in standard headers (e.g. x-api-key or x-goog-api-key). | UnifAI-ல் சேமிக்கப்பட்ட key-ஐ பயன்படுத்தாமல், Client தன்னிடம் உள்ள raw OpenAI/Anthropic key-ஐ நேரடியாக பாஸ் செய்ய உதவும். |
| `X-UnifAI-Temp-Token` | `jwt_or_uuid_token` | Short-lived Session Token | Ephemeral temporary session token used during interactive OAuth consent flows, MCP tool authorization callbacks, and restricted UI views. | MCP டூல்ஸ் மற்றும் OAuth login callbacks-ன் போது தற்காலிக அங்கீகாரத்திற்காக பயன்படுத்தப்படும் short-lived டோக்கன். |


## Intelligent Routing & Model Steering Headers (ரூட்டிங் & மாடல் தேர்வு)

| Header Name | Sample Value | Data Type | Description (English) | விளக்கம் (Tamil) |
| :--- | :--- | :--- | :--- | :--- |
| `x-uf-provider` | `openai | anthropic | bedrock | vertex | groq | ollama` | Provider Enum | Explicit Provider Pinning. Overrides automated routing rules and forces UnifAI to dispatch the request directly to the specified upstream model provider. | தானியங்கி ரூட்டிங் விதிகளை தவிர்த்து, குறிப்பிட்ட ஒரு AI Provider-க்கு (Ex: Anthropic அல்லது Bedrock) நேரடியாக கோரிக்கையை அனுப்ப உதவும். |
| `x-uf-model` | `claude-3-7-sonnet | gpt-4o | deepseek-r1` | Model ID | Explicit Model Selection. Overrides the body 'model' parameter or acts as the primary model target when using native SDK conversions. | கோரிக்கை இயக்கப்பட வேண்டிய மாடலின் பெயரை நேரடியாக நிர்ணயிக்க பயன்படுகிறது. |
| `x-uf-api-key-id` | `key_azure_eastus_02` | Credential Pool ID | Target Credential Pinning. When a single provider has multiple keys (e.g., 5 Azure OpenAI endpoints in different regions), pins execution to a specific key ID. | ஒரே provider-ல் பல API keys (multi-region accounts) இருக்கும்போது, குறிப்பிட்ட ஒரு key-ஐ மட்டும் தேர்வு செய்ய உதவும். |
| `x-uf-circuit-breaker-bypass` | `true` | Diagnostic Flag | Administrative Circuit Breaker Bypass. Forces the gateway to attempt dispatch to an upstream provider even if its circuit breaker is currently in the TRIPPED (OPEN) state. | Circuit Breaker open-ஆக (tripped) இருந்தாலும், சோதனைகளுக்காக அந்த provider-க்கு கட்டாயமாக request அனுப்ப உதவும். |


## Semantic Caching & Performance Headers (கேச்சிங் & லேடன்சி குறைப்பு)

| Header Name | Sample Value | Data Type | Description (English) | விளக்கம் (Tamil) |
| :--- | :--- | :--- | :--- | :--- |
| `x-uf-cache-key` | `tenant_alpha:customer_support:v2` | Namespace String | Cache Partition Namespace. Segregates cached response vectors into isolated buckets to guarantee complete data isolation between tenants, departments, or application versions. | கேச் தரவை தனித்தனி பாகங்களாக (partitions) பிரிக்க உதவுகிறது. வெவ்வேறு வாடிக்கையாளர்களின் டேட்டா ஒன்றோடொன்று கலக்காமல் பாதுகாக்கும். |
| `x-uf-cache-ttl` | `3600 (seconds) | 86400` | Integer (Seconds) | Per-Request Cache Time-To-Live. Overrides the global cache TTL to specify exactly how many seconds this response should remain valid in the cache. | இந்த குறிப்பிட்ட பதில் எத்தனை வினாடிகள் கேச்சில் சேமிக்கப்பட்டிருக்க வேண்டும் என்பதை நிர்ணயிக்கிறது. |
| `x-uf-cache-threshold` | `0.92 (range: 0.0 to 1.0)` | Float Score | Cosine Similarity Threshold Override. Sets the minimum vector similarity required to consider a stored prompt a 'Cache Hit'. Higher = more accurate; Lower = more hits. | Semantic cache-ல் இரண்டு கேள்விகள் எத்தனை சதவீதம் ஒத்துப்போக வேண்டும் (Cosine similarity) என்பதை மாற்ற உதவும். |
| `x-uf-cache-type` | `direct | semantic` | Cache Mode Enum | 'direct' enforces exact SHA-256 prompt string matching. 'semantic' generates an embedding vector and performs approximate nearest neighbor (ANN) search. | 'direct' என்பது 100% வார்த்தை பொருத்தம்; 'semantic' என்பது அர்த்த ரீதியான பொருத்தம் (Embedding Vector similarity). |
| `x-uf-cache-no-store` | `true / false` | Boolean Flag | No-Store Directive. When set to 'true', UnifAI will serve a cached response if a hit exists, but will NOT store the new LLM completion in the cache upon a miss. | ஏற்கனவே கேச்சில் இருந்தால் பதிலை எடு, ஆனால் புதிய பதிலை கேச்சில் சேமிக்காதே என்ற உத்தரவு. |


## MCP (Model Context Protocol) & Tool Headers (டூல்ஸ் பயன்பாடு)

| Header Name | Sample Value | Data Type | Description (English) | விளக்கம் (Tamil) |
| :--- | :--- | :--- | :--- | :--- |
| `x-uf-mcp-include-clients` | `* | github,postgres,slack` | Comma-separated List | MCP Server Whitelist. Injects only the specified MCP servers into the LLM request. Setting '*' exposes all servers permitted by the caller's Access Profile. | எந்தெந்த MCP servers-ன் டூல்ஸ்களை மாடலுக்கு வழங்க வேண்டும் என கட்டுப்படுத்தும் whitelist (Ex: github, postgres). |
| `x-uf-mcp-include-tools` | `query_database,create_pull_request` | Comma-separated List | MCP Tool Filter. Restricts the exposed tools to a specific subset of function names within the permitted MCP servers. | சர்வரில் உள்ள டூல்ஸ்களில் குறிப்பிட்ட சில functions-ஐ மட்டும் மாடலுக்கு வெளிப்படுத்த உதவும். |
| `x-uf-mcp-session-id` | `sess_oauth_usr_8821a` | Session Identifier | Per-User Tool Session Key. Binds the tool execution to a human user's personal OAuth session (e.g. user's personal GitHub token rather than a system token). | பயனரின் தனிப்பட்ட OAuth credentials மூலம் MCP tools-ஐ இயக்க பயன்படும் Session ID. |
| `x-uf-eh-*` | `x-uf-eh-workspace-id: ws_991` | Prefixed Passthrough | Extra Tool Headers. Any header matching the 'x-uf-eh-*' prefix is forwarded directly to upstream MCP servers if included in their allowed_extra_headers configuration. | MCP சர்வருக்கு தேவைப்படும் தனிப்பயன் headers-ஐ பாதுகாப்பாக forward செய்ய உதவும் prefix. |


## Observability, Tracing & Debugging Headers (கண்காணிப்பு & பிழைத்திருத்தம்)

| Header Name | Sample Value | Data Type | Description (English) | விளக்கம் (Tamil) |
| :--- | :--- | :--- | :--- | :--- |
| `x-uf-session-id` | `sess_chat_conv_12345` | String (Session ID) | Conversation Session Grouping. Groups multiple sequential LLM calls into a single unified trace in OpenTelemetry and LLM Logs. | ஒரு பயனரின் தொடர்ச்சியான சாட் உரையாடல்களை ஒரே Trace-ஆக இணைக்க பயன்படும் Session ID. |
| `x-uf-dim-<key>` | `x-uf-dim-environment: production` | Arbitrary Key-Value | Custom Log Dimension. Injects custom dimensional metadata into internal log records and exported connector events (e.g., department, tier, feature). | Logs-ல் custom filters சேர்க்க பயன்படும் metadata (Ex: x-uf-dim-app: mobile-app). |
| `x-uf-lh-<header>` | `x-uf-lh-correlation-id: req_091` | Header Capture | Captured Request Header. Explicitly instructs UnifAI's logging engine to record the value of this header into the LLM log entry. | குறிப்பிட்ட ஒரு request header-ஐ logs-ல் பதிவு செய்ய கட்டளையிடும் header. |
| `x-uf-disable-content-logging` | `true / false` | Privacy Flag | Content Privacy Mode. Completely drops prompt and completion text from log storage, recording only token counts, duration, latency, cost, and metadata. | ரகசியத்தன்மையை பாதுகாக்க, prompt மற்றும் பதிலை logs-ல் சேமிக்காமல், வெறும் செலவு மற்றும் வேகத்தை மட்டும் பதிவு செய்ய உதவும். |
| `x-uf-store-raw-request-response` | `true / false` | Debug Capture | Raw Wire Byte Storage. Instructs the gateway to persist the exact raw JSON byte stream exchanged with the upstream provider for low-level debugging. | Upstream provider-க்கு அனுப்பிய அசல் raw bytes-ஐ logs-ல் சேமிக்க உதவும் debug toggle. |
| `x-uf-send-back-raw-request` | `true / false` | Echo Header | Debug Echo. Injects the converted raw request payload sent to the upstream provider into a debugging HTTP response header. | Gateway மாற்றி அனுப்பிய raw payload-ஐ response header-ல் திரும்பப் பெற உதவும். |
| `x-uf-send-back-raw-response` | `true / false` | Echo Header | Debug Echo. Injects the unparsed upstream response payload into a debugging HTTP response header. | Upstream provider தந்த அசல் பதிலை response header-ல் திரும்பப் பெற உதவும். |
| `traceparent` | `00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01` | W3C Trace Context | Distributed Tracing Header. Propagates distributed OpenTelemetry trace context from calling microservices through UnifAI to downstream connectors. | Microservices வழியே OpenTelemetry Distributed Tracing-ஐ தொடர்ந்து கண்காணிக்க உதவும் W3C standard header. |
| `x-uf-log-repo-id` | `repo_maxim_eval_01` | External Repo ID | Evaluation Routing. Directs the request's telemetry log directly to a designated evaluation repository in platforms like Maxim AI. | Maxim AI போன்ற வெளி evaluation தளங்களில் குறிப்பிட்ட repository-க்கு logs-ஐ அனுப்ப உதவும். |


## Gateway Response Headers (UnifAI திருப்பி அனுப்பும் Headers)

| Header Name | Sample Value | Data Type | Description (English) | விளக்கம் (Tamil) |
| :--- | :--- | :--- | :--- | :--- |
| `x-unifai-provider` | `anthropic | openai | bedrock` | Provider String | Indicates which model provider actually executed and served the request. | எந்த AI Provider கோரிக்கையை நிறைவேற்றியது என்பதை வாடிக்கையாளருக்கு தெரிவிக்கும். |
| `x-unifai-original-model` | `gpt-4o` | Model Identifier | The model originally requested by the client application prior to routing. | வாடிக்கையாளர் கேட்ட அசல் மாடலின் பெயர். |
| `x-unifai-resolved-model` | `claude-3-5-sonnet` | Model Identifier | The actual model architecture that handled the prompt following routing rule or complexity tier resolution. | Routing விதிகள் மற்றும் complexity ஆய்வுக்குப் பிறகு உண்மையில் இயங்கிய மாடல். |
| `x-unifai-fallback-index` | `0 (primary) | 1, 2... (fallback)` | Integer Index | Indicates whether a fallback route was taken. '0' denotes primary provider success; non-zero indicates which fallback triggered. | Primary provider தோல்வியடைந்து Fallback provider இயங்கியதா என்பதை காட்டும் (0 = No fallback). |
| `x-unifai-request-type` | `chat | completion | embedding | realtime` | Type String | Identifies the execution modality: chat completions, text completions, embeddings, or realtime voice. | கோரிக்கையின் வகை: chat, embeddings, realtime voice, etc. |


# 4. In-Depth Feature Catalog (7 Core Pillars - 38 Features)
### அனைத்து 38 அம்சங்களின் முழுமையான தொழில்நுட்ப உடற்கூறு ஆய்வு (Deep-Dive Technical Dissection)

## Pillar 1: Observability (முழுமையான கண்காணிப்பு & செயல்திறன்)

*The Observability pillar provides sub-millisecond telemetry, cost accounting, request logging, and external data connectors across all AI workloads.*

### Dashboard (`/workspace/dashboard`)

**சுருக்கம் / Overview:** Real-time executive analytics console displaying financial, throughput, and performance metrics across models and virtual keys.

#### ⚙️ உட்புற கட்டமைப்பு & இயங்கும் முறை (Internal Architecture & Mechanics)
The Dashboard is powered by a high-frequency WebSocket connection (useWebSocket) paired with TanStack Query. In the backend, metrics are aggregated in-memory using atomic counters and persisted to time-series Postgres tables. It calculates p50, p90, p95, and p99 latency percentiles, tracks dollar spend using live Pricing Overrides, and measures cache hit ratios across all active tenant nodes.

#### 🧩 முக்கிய கூறுகள் & அமைப்புகள் (Key Components & Capabilities)
- **Time Range Filter:**  1h, 24h, 7d, 30d, and custom calendar windowing.
- **Spend Gauges:**  Total aggregate cost ($), daily burn rate, and projected monthly invoice.
- **Latency Percentiles:**  p50, p95, p99 curves showing TTFT (Time To First Token) and total latency.
- **Breakdown Views:**  Bar and donut charts slicing traffic by Provider, Model, and Virtual Key.
- **Cache Efficiency Meter:**  Real-time calculation of cost saved via Semantic Cache hits.

#### 🔗 மற்ற கூறுகளுடன் தொடர்பு (Module Interconnections)
Receives aggregated telemetry from LLM Logs, Pricing Overrides, and Semantic Caching. Influences Budgets & Limits alert triggers.

#### 💡 நடைமுறை பயன்பாடு (Enterprise Production Use Case)
Engineering leaders and FinOps teams monitor daily token burn, identify slow endpoints (p99 > 3000ms), and detect abnormal traffic surges before budget overruns occur.

---

### LLM Logs (`/workspace/logs`)

**சுருக்கம் / Overview:** Full-fidelity request and response transaction ledger capturing complete prompts, completions, tokens, latency, and guardrail verdicts.

#### ⚙️ உட்புற கட்டமைப்பு & இயங்கும் முறை (Internal Architecture & Mechanics)
Requests passing through FastHTTP are buffered asynchronously into an in-memory queue (logstore) to guarantee zero impact on proxy latency. A dedicated background worker pool writes records in micro-batches to PostgreSQL with pgx v5. Each log entry captures request_id, session_id, virtual_key_id, provider, model requested vs resolved, prompt_tokens, completion_tokens, exact dollar cost, latency_ms, ttft_ms, HTTP status, and full JSON payloads.

#### 🧩 முக்கிய கூறுகள் & அமைப்புகள் (Key Components & Capabilities)
- **Full-Text & Regex Search:**  Search across user prompts and model completions.
- **Multidimensional Filtering:**  Filter by Virtual Key, Customer ID, Provider, Model, Status Code, and Date Range.
- **Content Privacy Control:**  Supports x-uf-disable-content-logging to omit sensitive text while preserving metrics.
- **Raw Byte Inspector:**  Inspects exact wire JSON exchanged with upstream providers.
- **Guardrail Annotation:**  Visual flags indicating whether input or output triggered PII redaction or safety rules.

#### 🔗 மற்ற கூறுகளுடன் தொடர்பு (Module Interconnections)
Fed by every LLM invocation; powers the Dashboard metrics; streams out to Connectors (Datadog, Kafka); validates Guardrails accuracy.

#### 💡 நடைமுறை பயன்பாடு (Enterprise Production Use Case)
Developers troubleshoot failed user requests, investigate hallucinated model answers, verify TTFT performance, and export compliance audit logs.

---

### MCP Logs (`/workspace/mcp-logs`)

**சுருக்கம் / Overview:** Granular execution audit log tracking Model Context Protocol tool invocations, arguments, return payloads, and runtime errors.

#### ⚙️ உட்புற கட்டமைப்பு & இயங்கும் முறை (Internal Architecture & Mechanics)
Located in 'core/mcp/exec.go', the MCP interceptor instruments every tool execution. It records the calling agent's identity, the target MCP server, function name, parsed input JSON arguments, execution duration in milliseconds, and the exact tool output or error stack trace. Supports both stdio and SSE transport protocols.

#### 🧩 முக்கிய கூறுகள் & அமைப்புகள் (Key Components & Capabilities)
- **Tool Call Inspector:**  View structured input parameters and returned output schemas.
- **Execution Time Tracking:**  Measure tool execution latency to identify slow database queries or API scrapers.
- **Error Diagnostics:**  Full exception stack traces for crashed tool processes or timeout breaches.
- **Session Binding:**  Correlates tool calls with specific User Auth Sessions and Virtual Keys.

#### 🔗 மற்ற கூறுகளுடன் தொடர்பு (Module Interconnections)
Tied directly to the MCP Gateway, Tool Groups, and Auth Sessions. Streams tool performance into Dashboard.

#### 💡 நடைமுறை பயன்பாடு (Enterprise Production Use Case)
AI Agent engineers diagnose why an autonomous agent entered an infinite tool loop, verify SQL queries executed by the Database MCP tool, and track 3rd-party API failures.

---

### Browser AI (`/workspace/browser-ai`)

**சுருக்கம் / Overview:** Enterprise Browser Extension and local DLP proxy that intercepts employee AI queries on public web portals (ChatGPT, Claude) to enforce corporate data safety.

#### ⚙️ உட்புற கட்டமைப்பு & இயங்கும் முறை (Internal Architecture & Mechanics)
Consists of two synchronized layers: (1) A local proxy daemon (browser_ai_proxy.py) with browser extensions deployed via MDM, and (2) a centralized control console in the UnifAI UI. It intercepts HTTPS requests to web AI portals, runs Presidio DLP and local Ollama classification models, and blocks the transmission of proprietary source code, credentials, or customer PII.

#### 🧩 முக்கிய கூறுகள் & அமைப்புகள் (Key Components & Capabilities)
- **Target Websites Registry:**  Manages parent and sub-domain policies (e.g. chatgpt.com, claude.ai, perplexity.ai).
- **DLP Rule Engine:**  Regex-based and LLM-assisted policy enforcement on browser paste events.
- **Attachment Text Extractor:**  Inspects and extracts text from uploaded PDF, Word, and text attachments.
- **Tamper-Proof Agent Management:**  Heartbeat tracking, bulk agent deletion, and uninstall key protection.
- **Violation Logs:**  Dedicated log tracking employee DLP violations with source IP, user email, and matched policy.

#### 🔗 மற்ற கூறுகளுடன் தொடர்பு (Module Interconnections)
Shares Guardrail Providers (Presidio, Regex) and routes violation telemetry into Audit Logs and Connectors.

#### 💡 நடைமுறை பயன்பாடு (Enterprise Production Use Case)
Prevents corporate data leakage by stopping engineers from pasting confidential customer databases or private cryptographic keys into public web ChatGPT.

---

### Connectors (`/workspace/observability`)

**சுருக்கம் / Overview:** Real-time streaming export pipelines forwarding UnifAI metrics, logs, and trace spans to enterprise observability platforms.

#### ⚙️ உட்புற கட்டமைப்பு & இயங்கும் முறை (Internal Architecture & Mechanics)
Implemented in 'framework/connectors/runtime.go'. It operates as an asynchronous worker ring buffer that decouples export operations from the gateway request path. It converts internal telemetry events into platform-native formats and delivers them with automatic retries, exponential backoff, and circuit-breaking.

#### 🧩 முக்கிய கூறுகள் & அமைப்புகள் (Key Components & Capabilities)
- **Datadog Connector:**  Exports APM trace spans and metrics (unifai.requests.count, unifai.tokens.total, unifai.latency).
- **New Relic Connector:**  Streams custom events and transaction metrics for enterprise APM.
- **Apache Kafka Connector:**  Publishes structured JSON event streams to dedicated enterprise Kafka topics.
- **Google BigQuery Connector:**  Direct streaming inserts into data warehouse tables for custom SQL billing analytics.
- **Google Cloud PubSub Connector:**  Pushes event notifications to downstream serverless functions.
- **OpenTelemetry (OTel) Exporter:**  OTLP gRPC/HTTP exporter compatible with Prometheus, Jaeger, and Grafana.

#### 🔗 மற்ற கூறுகளுடன் தொடர்பு (Module Interconnections)
Reads continuously from LLM Logs, MCP Logs, and Audit Logs; forwards data to external corporate SIEMs.

#### 💡 நடைமுறை பயன்பாடு (Enterprise Production Use Case)
Enterprises stream all AI consumption logs to their centralized Datadog dashboard and BigQuery data lake for corporate billing audits and security threat analysis.

---

### Logs Settings (`/workspace/config/logging`)

**சுருக்கம் / Overview:** Centralized policy management console for log retention, sampling ratios, data privacy redaction, and raw byte persistence.

#### ⚙️ உட்புற கட்டமைப்பு & இயங்கும் முறை (Internal Architecture & Mechanics)
Located in 'ui/app/workspace/config/views/loggingView.tsx'. Controls internal storage garbage collection routines, sampling filters in the FastHTTP middleware, and sensitive payload redaction algorithms.

#### 🧩 முக்கிய கூறுகள் & அமைப்புகள் (Key Components & Capabilities)
- **Retention Policy:**  Configurable auto-purge schedules (e.g. 7 days, 30 days, 90 days, 365 days).
- **Traffic Sampling:**  Configures percentage-based sampling (1% to 100%) to reduce storage costs in massive volume environments.
- **Content Redaction Toggle:**  Global enforcement of zero-prompt storage for extreme regulatory environments.
- **Raw Wire Byte Storage:**  Toggle for storing full wire-level JSON payloads for diagnostic deep-dives.
- **Storage Offloading:**  Integrates with AWS S3 and Google Cloud Storage for cold log archival.

#### 🔗 மற்ற கூறுகளுடன் தொடர்பு (Module Interconnections)
Directly governs the storage behavior of LLM Logs and MCP Logs.

#### 💡 நடைமுறை பயன்பாடு (Enterprise Production Use Case)
Healthcare and financial institutions enforce 30-day auto-deletion policies and disable prompt storage to satisfy HIPAA and PCI-DSS compliance.

---

## Pillar 2: Models & Intelligent Routing (மாடல் மேலாண்மை & ரூட்டிங்)

*The Models pillar orchestrates model cataloging, dynamic multi-provider traffic routing, financial budget quotas, and automated failover.*

### Model Catalog (`/workspace/model-catalog`)

**சுருக்கம் / Overview:** Unified inventory of all connected models across cloud and self-hosted providers, displaying context limits, capabilities, and pricing.

#### ⚙️ உட்புற கட்டமைப்பு & இயங்கும் முறை (Internal Architecture & Mechanics)
Maintained in 'framework/modelcatalog'. Aggregates model metadata from all configured providers. Maintains token window boundaries, max generation tokens, supported modalities (text, vision, audio), feature capabilities (function calling, JSON mode, reasoning effort), and real-time provider reachability.

#### 🧩 முக்கிய கூறுகள் & அமைப்புகள் (Key Components & Capabilities)
- **Model Directory:**  Comprehensive searchable catalog of models from OpenAI, Anthropic, Bedrock, Vertex, Ollama, etc.
- **Capability Matrix:**  Flags for Tool Calling, Vision, Structured Outputs, and Streaming support.
- **Token Limits:**  Context window size (e.g. 128k, 200k, 1M) and maximum output token ceilings.
- **Model Aliasing:**  Maps logical names (e.g. 'production-fast') to specific underlying architectures.

#### 🔗 மற்ற கூறுகளுடன் தொடர்பு (Module Interconnections)
Supplies target definitions to Routing Rules, Complexity Router, and Access Profiles. Displays pricing in Dashboard.

#### 💡 நடைமுறை பயன்பாடு (Enterprise Production Use Case)
Developers query the catalog to discover which models support vision inputs and tool-calling capabilities across enterprise accounts.

---

### Model Providers (`/workspace/providers`)

**சுருக்கம் / Overview:** Credential and endpoint management console for upstream AI vendors, supporting multi-key rotation and custom private endpoints.

#### ⚙️ உட்புற கட்டமைப்பு & இயங்கும் முறை (Internal Architecture & Mechanics)
Located in 'core/providers'. Contains dedicated adapters for 25+ AI providers (OpenAI, Azure, Anthropic, Bedrock, Vertex, Groq, Cerebras, Cohere, DeepSeek, Mistral, Ollama, vLLM, Replicate). Implements connection pooling, custom base URLs, and multi-key rotation pools with round-robin or priority weighting.

#### 🧩 முக்கிய கூறுகள் & அமைப்புகள் (Key Components & Capabilities)
- **Provider Adapters:**  Specialized wire protocol implementations for each major AI provider.
- **Multi-Key Rotation:**  Pool multiple API keys to distribute rate limits and avoid provider throttling.
- **Private Endpoints:**  Configure custom base URLs for internal vLLM, Ollama, or VPC-peered deployments.
- **Connection Tuning:**  Per-provider HTTP keep-alive, dial timeouts, and connection pool sizes.

#### 🔗 மற்ற கூறுகளுடன் தொடர்பு (Module Interconnections)
Powers the Model Catalog; feeds health data to Circuit Breaker; executes requests dispatched by Routing Rules.

#### 💡 நடைமுறை பயன்பாடு (Enterprise Production Use Case)
Platform teams rotate OpenAI API keys without downtime and configure dedicated AWS Bedrock IAM role credentials.

---

### Budgets & Limits (`/workspace/model-limits`)

**சுருக்கம் / Overview:** Multi-tier rate limiting and financial budget enforcement engine preventing runaway spending and provider throttling.

#### ⚙️ உட்புற கட்டமைப்பு & இயங்கும் முறை (Internal Architecture & Mechanics)
Implemented in 'framework/configstore' and 'plugins/governance/tracker.go'. Maintains atomic sliding-window rate limit counters (RPM, TPM, RPD) in Redis / local memory. Continuously evaluates current token burn against daily and monthly dollar budgets ($ USD). Triggers immediate rejection with HTTP 429 when limits are breached.

#### 🧩 முக்கிய கூறுகள் & அமைப்புகள் (Key Components & Capabilities)
- **Throughput Limits:**  Requests Per Minute (RPM), Tokens Per Minute (TPM), Requests Per Day (RPD).
- **Dollar Spending Caps:**  Hard and soft monthly/daily financial budget limits in USD.
- **Multilevel Scoping:**  Enforce limits globally, per Virtual Key, per Team, per User, or per Model.
- **Breach Actions:**  Reject with 429 Too Many Requests, downgrade to a cheaper model, or trigger webhook alerts.

#### 🔗 மற்ற கூறுகளுடன் தொடர்பு (Module Interconnections)
Evaluated during Stage 1 of the request lifecycle; updates budget balances from LLM Logs token consumption.

#### 💡 நடைமுறை பயன்பாடு (Enterprise Production Use Case)
Ensures an experimental hackathon project cannot exceed $500/month or flood the company's shared OpenAI tier with 10,000 RPM.

---

### Routing Rules (`/workspace/routing-rules`)

**சுருக்கம் / Overview:** Condition-based dynamic routing engine powered by Google CEL expressions for intelligent traffic routing and A/B testing.

#### ⚙️ உட்புற கட்டமைப்பு & இயங்கும் முறை (Internal Architecture & Mechanics)
Located in 'plugins/governance/routing.go'. Pre-compiles Google Common Expression Language (CEL) rules into memory. Upon request arrival, evaluates rules against request context (model name, prompt content, user department, headers). Selects target provider, performs traffic splitting, or triggers fallback chains.

#### 🧩 முக்கிய கூறுகள் & அமைப்புகள் (Key Components & Capabilities)
- **CEL Expression Builder:**  Define rules like `request.model == 'fast' && prompt.length < 500`.
- **Traffic Splitting:**  Distribute traffic (e.g. 80% to OpenAI, 20% to Anthropic) for zero-risk model evaluation.
- **Header-Based Routing:**  Route requests based on custom headers like `x-uf-dim-env: staging`.
- **Fallback Target Sequences:**  Ordered array of backup models if primary destination is unavailable.

#### 🔗 மற்ற கூறுகளுடன் தொடர்பு (Module Interconnections)
Works in tandem with Complexity Router; hands off resolved target to Circuit Breaker.

#### 💡 நடைமுறை பயன்பாடு (Enterprise Production Use Case)
Automatically routes customer queries mentioning 'code' to DeepSeek Coder, while routing French queries to Mistral Large.

---

### Complexity Router (`/workspace/complexity-router`)

**சுருக்கம் / Overview:** Intelligent prompt complexity classifier that buckets queries into 4 tiers and routes them to cost-appropriate models, cutting costs by 60–80%.

#### ⚙️ உட்புற கட்டமைப்பு & இயங்கும் முறை (Internal Architecture & Mechanics)
Located in 'plugins/governance/complexity'. Analyzes incoming user messages across 4 distinct tiers: SIMPLE, MEDIUM, COMPLEX, and REASONING. Uses keyword dictionary matching, token length boundaries, and lightweight heuristics to identify task difficulty and route to corresponding model architectures.

#### 🧩 முக்கிய கூறுகள் & அமைப்புகள் (Key Components & Capabilities)
- **Tier Palette:**  Simple (P1), Medium (P2), Complex (P3), Reasoning (P4).
- **Keyword Lists:**  Reasoning keywords ('prove', 'step by step', 'derivation'), coding terms, and simple greetings.
- **Boundary Controls:**  Token length thresholds separating simple questions from heavy multi-turn reasoning.
- **Tier Target Mapping:**  Simple -> gpt-4o-mini; Medium -> claude-3-5-haiku; Complex -> gpt-4o; Reasoning -> o1.

#### 🔗 மற்ற கூறுகளுடன் தொடர்பு (Module Interconnections)
Feeds classified tier context directly into Routing Rules; updates cost metrics in Dashboard.

#### 💡 நடைமுறை பயன்பாடு (Enterprise Production Use Case)
Slashes enterprise AI bills by routing routine 'What are your store hours?' questions to a $0.15/1M token model instead of a $15/1M token reasoning model.

---

### Circuit Breaker (`/workspace/circuit-breaker`)

**சுருக்கம் / Overview:** Automated failure detection and failover engine that guarantees 99.99% application uptime by rerouting around downed AI providers.

#### ⚙️ உட்புற கட்டமைப்பு & இயங்கும் முறை (Internal Architecture & Mechanics)
Implemented in 'framework/circuitbreaker/runtime.go'. Employs a 3-state finite state machine (CLOSED, OPEN, HALF-OPEN). Tracks consecutive 5xx errors, timeouts, and latency spikes across a sliding sample window. When error thresholds are crossed, the circuit TRIPS (OPEN) and diverts traffic to healthy fallbacks.

#### 🧩 முக்கிய கூறுகள் & அமைப்புகள் (Key Components & Capabilities)
- **Failure Threshold:**  Configurable error percentage (e.g. 50% errors over 10 requests).
- **Latency Threshold:**  Trips if p95 response time exceeds configured ceiling (e.g. 8000ms).
- **Cool-off Duration:**  Sleep window (e.g. 30s) before transitioning to HALF-OPEN to test provider recovery.
- **Fallback Chains:**  Automatic cascade through secondary and tertiary backup models.
- **Header Emission:**  Returns `x-unifai-fallback-index: 1` to notify callers that a fallback route was executed.

#### 🔗 மற்ற கூறுகளுடன் தொடர்பு (Module Interconnections)
Guards all outbound requests dispatched by Routing Rules and Model Providers.

#### 💡 நடைமுறை பயன்பாடு (Enterprise Production Use Case)
When an OpenAI outage causes 504 Gateway Timeouts, UnifAI automatically shifts chatbot traffic to Claude-3.5-Sonnet in <100ms with zero dropped user sessions.

---

### Pricing Overrides (`/workspace/custom-pricing/overrides`)

**சுருக்கம் / Overview:** Granular custom token pricing table defining exact $/1M token costs for enterprise negotiated discount rates and custom fine-tuned models.

#### ⚙️ உட்புற கட்டமைப்பு & இயங்கும் முறை (Internal Architecture & Mechanics)
Maintained in 'framework/configstore'. Evaluated during post-request processing. Matches the executed provider and model against custom price rules, calculating prompt cost, completion cost, and cached token read cost down to micro-cents.

#### 🧩 முக்கிய கூறுகள் & அமைப்புகள் (Key Components & Capabilities)
- **Input / Output Token Rates:**  Configurable cost per 1M prompt and completion tokens.
- **Cached Token Discount:**  Custom pricing for prompt cache read hits.
- **Scoped Overrides:**  Define custom rates for specific enterprise accounts or private clusters.

#### 🔗 மற்ற கூறுகளுடன் தொடர்பு (Module Interconnections)
Calculates exact dollar spend recorded in LLM Logs, Budgets & Limits, and Dashboard.

#### 💡 நடைமுறை பயன்பாடு (Enterprise Production Use Case)
Enterprises with custom 30% volume discounts from Microsoft Azure input their exact discounted token rates for precise financial accounting.

---

### Model Settings (`/workspace/custom-pricing`)

**சுருக்கம் / Overview:** Global routing parameters, request timeout defaults, retry policies, and fallback model definitions.

#### ⚙️ உட்புற கட்டமைப்பு & இயங்கும் முறை (Internal Architecture & Mechanics)
Defines platform-wide default behaviors applied when specific provider or routing rules are omitted. Manages HTTP transport timeouts, max retries, exponential backoff with jitter, and default fallback models.

#### 🧩 முக்கிய கூறுகள் & அமைப்புகள் (Key Components & Capabilities)
- **Global Timeouts:**  Sets default request and connect timeouts (e.g. 60s).
- **Retry Policy:**  Configures maximum retry attempts and exponential backoff jitter.
- **Default Fallback:**  Universal emergency fallback model when all routing chains fail.

#### 🔗 மற்ற கூறுகளுடன் தொடர்பு (Module Interconnections)
Underpins the execution engine across all Model Providers.

#### 💡 நடைமுறை பயன்பாடு (Enterprise Production Use Case)
Standardizes a 30-second timeout and 2-retry policy across all AI microservices in the organization.

---

## Pillar 3: MCP Gateway (டூல்ஸ் & ஏஜென்ட்கள் - Model Context Protocol)

*The Model Context Protocol Gateway standardizes agentic tool integration, sandboxed code execution, and enterprise OAuth credential delegation.*

### MCP Catalog (`/workspace/mcp-registry`)

**சுருக்கம் / Overview:** Master registry of all registered MCP servers, available tool definitions, schemas, and transport configurations.

#### ⚙️ உட்புற கட்டமைப்பு & இயங்கும் முறை (Internal Architecture & Mechanics)
Located in 'core/mcp'. Implements the Model Context Protocol JSON-RPC 2.0 specification over stdio, SSE, and in-process transports. Maintains active connections, fetches available tool schemas, resources, and prompt templates, and dynamically formats tool specifications into model-native tool calling schemas.

#### 🧩 முக்கிய கூறுகள் & அமைப்புகள் (Key Components & Capabilities)
- **Server Registry:**  Catalog of active and registered MCP servers.
- **Schema Inspector:**  View function signatures, descriptions, and required JSON parameters.
- **Transport Support:**  Native support for stdio subprocesses and HTTP Server-Sent Events (SSE).
- **Health Monitor:**  Continuously pings MCP servers and flags unresponsive processes.

#### 🔗 மற்ற கூறுகளுடன் தொடர்பு (Module Interconnections)
Supplies tool definitions to Tool Groups and the LLM execution pipeline; records execution in MCP Logs.

#### 💡 நடைமுறை பயன்பாடு (Enterprise Production Use Case)
Agent developers inspect what database query tools and web scraping functions are currently registered and online.

---

### MCP Library (`/workspace/mcp-registry/library`)

**சுருக்கம் / Overview:** One-click curated installer for popular, production-ready open-source MCP servers.

#### ⚙️ உட்புற கட்டமைப்பு & இயங்கும் முறை (Internal Architecture & Mechanics)
Pre-configured repository of enterprise MCP servers. Allows administrators to install and spin up containerized or subprocess MCP servers with pre-tested configurations in a single click.

#### 🧩 முக்கிய கூறுகள் & அமைப்புகள் (Key Components & Capabilities)
- **Curated Servers:**  GitHub, PostgreSQL, Slack, Google Drive, Jira, Local Filesystem, Memory, Brave Search.
- **Configuration Templates:**  Pre-filled environment variables and connection string templates.
- **1-Click Deploy:**  Automatically provisions and connects servers to the MCP Catalog.

#### 🔗 மற்ற கூறுகளுடன் தொடர்பு (Module Interconnections)
Directly registers newly installed tools into the MCP Catalog and Tool Groups.

#### 💡 நடைமுறை பயன்பாடு (Enterprise Production Use Case)
A team instantly adds a PostgreSQL database query tool to their AI Agent in 30 seconds without writing custom integration code.

---

### Tool Groups (`/workspace/mcp-tool-groups`)

**சுருக்கம் / Overview:** Logical grouping and security boundary mechanism bundling related tools together for role-based assignment to Virtual Keys.

#### ⚙️ உட்புற கட்டமைப்பு & இயங்கும் முறை (Internal Architecture & Mechanics)
Maintained in 'framework/mcptoolgroups'. Groups individual tools into logical operational bundles (e.g. 'DevOps-Tools', 'Finance-Tools', 'Support-Tools'). Attached to Virtual Keys via Access Profiles to enforce strict least-privilege tool access.

#### 🧩 முக்கிய கூறுகள் & அமைப்புகள் (Key Components & Capabilities)
- **Tool Bundles:**  Logical collections of tools from one or more MCP servers.
- **Granular Whitelisting:**  Selectively include or exclude individual functions within an MCP server.
- **Access Profile Mapping:**  Bind tool groups directly to specific Virtual Keys.

#### 🔗 மற்ற கூறுகளுடன் தொடர்பு (Module Interconnections)
Bound to Virtual Keys via Access Profiles; controls which tools are injected into LLM requests.

#### 💡 நடைமுறை பயன்பாடு (Enterprise Production Use Case)
Ensures a Customer Support bot only has access to Zendesk tools, completely blocking it from executing Database Drop Table commands.

---

### Auth Sessions (`/workspace/mcp-sessions`)

**சுருக்கம் / Overview:** Stateful credential manager tracking per-user authenticated sessions for tools requiring individual user permissions.

#### ⚙️ உட்புற கட்டமைப்பு & இயங்கும் முறை (Internal Architecture & Mechanics)
Located in 'core/mcp/credstore'. Associates stateful credentials (e.g. personal access tokens, session tokens) with individual human users via `x-uf-mcp-session-id`. When an agent calls a tool, UnifAI injects that specific user's credentials rather than a shared corporate master key.

#### 🧩 முக்கிய கூறுகள் & அமைப்புகள் (Key Components & Capabilities)
- **Session Keying:**  Keyed to an end-user SSO identity, virtual key, or client session ID.
- **Credential Vault:**  Encrypted at-rest storage for user session tokens.
- **Session Lifecycle:**  Automatic expiration, idle timeouts, and manual revocation.

#### 🔗 மற்ற கூறுகளுடன் தொடர்பு (Module Interconnections)
Works alongside OAuth Grants to supply credentials during MCP execution; logged in MCP Logs.

#### 💡 நடைமுறை பயன்பாடு (Enterprise Production Use Case)
When an executive asks an AI agent to 'Summarize my unread emails', the agent accesses Gmail using that executive's specific session token.

---

### OAuth Grants (`/workspace/oauth-grants`)

**சுருக்கம் / Overview:** Downstream OAuth 2.0 authorization server managing consent screens, token exchange, and refresh token cycles for 3rd-party tools.

#### ⚙️ உட்புற கட்டமைப்பு & இயங்கும் முறை (Internal Architecture & Mechanics)
Implemented in 'framework/oauth2'. Acts as a full OAuth 2.0 authorization server supporting PKCE. Handles authorization code redirects, user consent interfaces, token storage, and automated background refresh token cycles for third-party providers (Google, Microsoft, GitHub, Slack).

#### 🧩 முக்கிய கூறுகள் & அமைப்புகள் (Key Components & Capabilities)
- **OAuth 2.0 PKCE Flow:**  Secure authorization flow for browser and desktop clients.
- **Consent Management:**  Displays fine-grained scope approval screens to end users.
- **Token Refresh Engine:**  Automatically refreshes expired OAuth access tokens in the background.

#### 🔗 மற்ற கூறுகளுடன் தொடர்பு (Module Interconnections)
Supplies live access tokens to Auth Sessions for MCP tool execution.

#### 💡 நடைமுறை பயன்பாடு (Enterprise Production Use Case)
End-users securely authorize an AI agent to read their Google Calendar without ever exposing their Google password.

---

### MCP Settings (`/workspace/mcp-settings`)

**சுருக்கம் / Overview:** Global execution parameters for MCP servers, including execution timeouts, concurrency limits, and restart policies.

#### ⚙️ உட்புற கட்டமைப்பு & இயங்கும் முறை (Internal Architecture & Mechanics)
Configures runtime constraints for MCP tool execution processes. Enforces hard execution timeouts, maximum concurrent tool processes, memory limits, and auto-restart policies.

#### 🧩 முக்கிய கூறுகள் & அமைப்புகள் (Key Components & Capabilities)
- **Execution Timeout:**  Maximum duration a tool is permitted to run (e.g. 30s) before cancellation.
- **Concurrency Limits:**  Caps simultaneous tool executions to prevent server CPU exhaustion.
- **Process Restart Policy:**  Auto-restart crashed stdio server subprocesses.

#### 🔗 மற்ற கூறுகளுடன் தொடர்பு (Module Interconnections)
Governs the execution runtime of all servers in the MCP Catalog.

#### 💡 நடைமுறை பயன்பாடு (Enterprise Production Use Case)
Terminates rogue or hanging tool execution scripts after 30 seconds to prevent resource exhaustion.

---

### Plugins (`/workspace/plugins`)

**சுருக்கம் / Overview:** Modular extensibility framework supporting custom Go plugins and sandboxed Starlark scripts in the request pipeline.

#### ⚙️ உட்புற கட்டமைப்பு & இயங்கும் முறை (Internal Architecture & Mechanics)
Located in 'core/pluginpipeline.go' and 'core/mcp/codemode/starlark'. Supports both compiled Go plugins implementing BasePlugin and dynamically interpreted Starlark scripts. Provides lifecycle hooks: PreLLMHook, PostLLMHook, PreMCPHook, and PostMCPHook.

#### 🧩 முக்கிய கூறுகள் & அமைப்புகள் (Key Components & Capabilities)
- **Lifecycle Hooks:**  Intercept and modify requests before and after LLM and MCP execution.
- **Starlark Script Sandbox:**  Secure, non-Turing complete runtime for dynamic in-memory transformations.
- **Custom Encryption:**  Apply proprietary data encryption algorithms to prompts.

#### 🔗 மற்ற கூறுகளுடன் தொடர்பு (Module Interconnections)
Integrates into the core FastHTTP request-response lifecycle.

#### 💡 நடைமுறை பயன்பாடு (Enterprise Production Use Case)
An enterprise injects a proprietary data anonymization algorithm into the PreLLMHook before prompts leave the company network.

---

## Pillar 4: Governance & Enterprise Compliance (அணுகல் கட்டுப்பாடு & பாதுகாப்பு)

*The Governance pillar establishes multi-tenant identity, role-based access control, automated SCIM provisioning, and regulatory audit logging.*

### Virtual Keys (`/workspace/governance/virtual-keys`)

**சுருக்கம் / Overview:** Synthetic proxy API keys (sk-uf-*) issued to applications, encapsulating permissions, quotas, and upstream credential masking.

#### ⚙️ உட்புற கட்டமைப்பு & இயங்கும் முறை (Internal Architecture & Mechanics)
Located in 'plugins/governance/main.go'. Virtual Keys are high-entropy cryptographic strings starting with 'sk-uf-'. They hide upstream provider credentials, binding the request to a specific Team, Customer, Budget Limit, Access Profile, and Tool Group. Verified in <0.5ms via local cache.

#### 🧩 முக்கிய கூறுகள் & அமைப்புகள் (Key Components & Capabilities)
- **Key Obfuscation:**  Completely hides sensitive upstream OpenAI and Anthropic master keys.
- **Configurable Expiration:**  Set automated key expiry dates (e.g. 90-day rotation).
- **IP & CIDR Restrictions:**  Restrict key usage to specific corporate IP address ranges.
- **Instant Revocation:**  Revoke compromised keys in real-time across the cluster without restarting apps.

#### 🔗 மற்ற கூறுகளுடன் தொடர்பு (Module Interconnections)
Entry point for authentication; enforces Budgets & Limits, Access Profiles, and Audit Logs.

#### 💡 நடைமுறை பயன்பாடு (Enterprise Production Use Case)
A microservice uses 'sk-uf-prod-svc-123' to make AI calls; if compromised, it can be revoked instantly without affecting other services.

---

### Users (`/workspace/governance/users`)

**சுருக்கம் / Overview:** User account directory for developers, administrators, and stakeholders with workspace access.

#### ⚙️ உட்புற கட்டமைப்பு & இயங்கும் முறை (Internal Architecture & Mechanics)
Manages platform user accounts, authentication credentials (bcrypt hashed), SSO SAML/OIDC identity bindings, and Multi-Factor Authentication (MFA) status.

#### 🧩 முக்கிய கூறுகள் & அமைப்புகள் (Key Components & Capabilities)
- **User Directory:**  Searchable list of workspace members and their status.
- **MFA Enforcement:**  Mandatory Two-Factor Authentication via TOTP authenticator apps.
- **Session Invalidation:**  Force-terminate active user login sessions across devices.

#### 🔗 மற்ற கூறுகளுடன் தொடர்பு (Module Interconnections)
Members of Teams; assigned Roles & Permissions (RBAC); actions tracked in Audit Logs.

#### 💡 நடைமுறை பயன்பாடு (Enterprise Production Use Case)
Workspace administrators invite developers and enforce MFA for all production environment access.

---

### Teams (`/workspace/governance/teams`)

**சுருக்கம் / Overview:** Departmental organizational units managing shared budgets, team-owned virtual keys, and delegated administration.

#### ⚙️ உட்புற கட்டமைப்பு & இயங்கும் முறை (Internal Architecture & Mechanics)
Organizes users into functional departments (e.g. Frontend Engineering, Data Science, Customer Support). Virtual Keys and Budgets are created at the Team level for unified departmental tracking.

#### 🧩 முக்கிய கூறுகள் & அமைப்புகள் (Key Components & Capabilities)
- **Team Hierarchy:**  Departmental groupings with dedicated Team Admins.
- **Shared Budget Pool:**  Shared monthly financial spending quota across team members.
- **Team Virtual Keys:**  Keys accessible only by authorized team engineers.

#### 🔗 மற்ற கூறுகளுடன் தொடர்பு (Module Interconnections)
Groups Users; belongs to Business Units; owns Virtual Keys and Budgets.

#### 💡 நடைமுறை பயன்பாடு (Enterprise Production Use Case)
The Data Science team is allocated a $5,000 monthly budget and 5 dedicated GPU model keys.

---

### Business Units (`/workspace/governance/business-units`)

**சுருக்கம் / Overview:** Top-level enterprise divisions grouping multiple teams for macroscopic financial chargeback and corporate reporting.

#### ⚙️ உட்புற கட்டமைப்பு & இயங்கும் முறை (Internal Architecture & Mechanics)
Represents top-level corporate subsidiaries or operating divisions (e.g. Retail Banking, Commercial Insurance, Corporate IT). Aggregates token consumption across multiple child teams.

#### 🧩 முக்கிய கூறுகள் & அமைப்புகள் (Key Components & Capabilities)
- **Division Grouping:**  Hierarchical aggregation of teams.
- **Corporate Chargeback:**  High-level financial reporting for CFO and Finance teams.

#### 🔗 மற்ற கூறுகளுடன் தொடர்பு (Module Interconnections)
Contains multiple Teams; reported in Dashboard and BigQuery connector exports.

#### 💡 நடைமுறை பயன்பாடு (Enterprise Production Use Case)
Corporate Finance views the total quarterly AI expenditure of the entire Retail Division across 15 engineering teams.

---

### Customers (`/workspace/governance/customers`)

**சுருக்கம் / Overview:** Multi-tenant client registry for B2B SaaS applications, tracking token consumption and cost per paying customer.

#### ⚙️ உட்புற கட்டமைப்பு & இயங்கும் முறை (Internal Architecture & Mechanics)
Allows B2B SaaS platforms to track external tenant consumption. When requests include `x-uf-customer-id`, UnifAI isolates and attributes token counts and dollar spend to that specific customer entity.

#### 🧩 முக்கிய கூறுகள் & அமைப்புகள் (Key Components & Capabilities)
- **Customer Registry:**  Directory of client organizations using the SaaS product.
- **Per-Customer Quotas:**  Enforce rate limits and cost caps on specific customer accounts.
- **Billing Reports:**  Export itemized monthly AI consumption bills per customer.

#### 🔗 மற்ற கூறுகளுடன் தொடர்பு (Module Interconnections)
Scoped via the `x-uf-customer-id` header; reported in Dashboard and LLM Logs.

#### 💡 நடைமுறை பயன்பாடு (Enterprise Production Use Case)
A legal SaaS platform calculates that Customer X consumed $412 in GPT-4o legal doc summaries this month, auto-invoicing them via Stripe.

---

### User Provisioning (SCIM) (`/workspace/scim`)

**சுருக்கம் / Overview:** SCIM v2.0 endpoint automating employee onboarding and deprovisioning from enterprise Identity Providers (Okta, Azure AD).

#### ⚙️ உட்புற கட்டமைப்பு & இயங்கும் முறை (Internal Architecture & Mechanics)
Implements RFC 7643 and RFC 7644 SCIM 2.0 endpoints (/scim/v2/Users, /scim/v2/Groups). Receives webhook push updates from enterprise IdPs (Okta, Microsoft Entra ID / Azure AD, PingIdentity). Automatically provisions accounts, assigns team memberships, and immediately deactivates former employees.

#### 🧩 முக்கிய கூறுகள் & அமைப்புகள் (Key Components & Capabilities)
- **SCIM 2.0 Protocol:**  Standardized enterprise user lifecycle integration.
- **Automated Deprovisioning:**  Instant revocation of platform access when an employee leaves the company.
- **Group Mapping:**  Automatically maps corporate Okta groups to UnifAI Teams and Roles.

#### 🔗 மற்ற கூறுகளுடன் தொடர்பு (Module Interconnections)
Directly provisions Users and updates Team memberships; actions recorded in Audit Logs.

#### 💡 நடைமுறை பயன்பாடு (Enterprise Production Use Case)
When an engineer is offboarded in Okta, their UnifAI account and personal virtual keys are deactivated within 1 second.

---

### Roles & Permissions (RBAC) (`/workspace/governance/rbac`)

**சுருக்கம் / Overview:** Fine-grained Role-Based Access Control matrix governing administrative actions across all gateway resources.

#### ⚙️ உட்புற கட்டமைப்பு & இயங்கும் முறை (Internal Architecture & Mechanics)
Implemented in 'framework/rbac'. Enforces a matrix of Resources (VirtualKeys, RoutingRules, Guardrails, Logs, Providers, Settings) and Operations (View, Create, Edit, Delete). Evaluated on every UI route match and control plane API call.

#### 🧩 முக்கிய கூறுகள் & அமைப்புகள் (Key Components & Capabilities)
- **Predefined Roles:**  Super Admin, Workspace Admin, Developer, Auditor, Viewer.
- **Custom Roles:**  Create bespoke enterprise roles with granular permission toggles.
- **Resource Scoping:**  Restrict permissions to specific Teams or Business Units.

#### 🔗 மற்ற கூறுகளுடன் தொடர்பு (Module Interconnections)
Governs UI visibility (via useRbac hook) and authorizes Admin API calls.

#### 💡 நடைமுறை பயன்பாடு (Enterprise Production Use Case)
Junior developers can view logs and test prompts, but are blocked from creating new Virtual Keys or modifying Routing Rules.

---

### Access Profiles (`/workspace/governance/access-profiles`)

**சுருக்கம் / Overview:** Reusable security policy presets defining allowed models, providers, and MCP tool groups bound to Virtual Keys.

#### ⚙️ உட்புற கட்டமைப்பு & இயங்கும் முறை (Internal Architecture & Mechanics)
Located in 'framework/configstore'. Encapsulates model and tool permissions into reusable bundles. When attached to a Virtual Key, UnifAI rejects any request attempting to use an unapproved model or unlisted MCP tool.

#### 🧩 முக்கிய கூறுகள் & அமைப்புகள் (Key Components & Capabilities)
- **Approved Models Whitelist:**  Exact list of allowed model IDs.
- **Approved Providers Whitelist:**  Approved vendor endpoints.
- **Approved Tool Groups:**  Permitted MCP tool groups.

#### 🔗 மற்ற கூறுகளுடன் தொடர்பு (Module Interconnections)
Bound to Virtual Keys; evaluated during Stage 1 request validation.

#### 💡 நடைமுறை பயன்பாடு (Enterprise Production Use Case)
A 'Staging-Profile' guarantees that staging microservices can only use cheap open-source models (Llama 3.1 8B), preventing accidental GPT-4o spend in QA.

---

### Audit Logs (`/workspace/audit-logs`)

**சுருக்கம் / Overview:** Cryptographically timestamped, immutable audit ledger recording all administrative mutations for SOC 2 and ISO 27001 compliance.

#### ⚙️ உட்புற கட்டமைப்பு & இயங்கும் முறை (Internal Architecture & Mechanics)
Every state mutation across the platform (creating a key, editing a route, altering budget limits) triggers an immutable audit event. Captures Actor ID, action type, target resource, JSON diff of changes (before/after), source IP address, user agent, and timestamp.

#### 🧩 முக்கிய கூறுகள் & அமைப்புகள் (Key Components & Capabilities)
- **Immutable Storage:**  Tamper-resistant append-only database table.
- **JSON Diff Inspector:**  Visual before-and-after comparison of configuration changes.
- **Compliance Export:**  One-click export to CSV / JSON for regulatory audits.

#### 🔗 மற்ற கூறுகளுடன் தொடர்பு (Module Interconnections)
Records all mutations across Governance, Models, Guardrails, and Settings; streams to Connectors.

#### 💡 நடைமுறை பயன்பாடு (Enterprise Production Use Case)
SOC 2 auditors verify who changed the production routing rule on August 12th and view the exact JSON diff of the modification.

---

## Pillar 5: Guardrails & Content Security (உள்ளடக்கப் பாதுகாப்பு & கொள்கை)

*The Guardrails pillar intercepts prompt inputs and model outputs to enforce PII redaction, brand safety, prompt injection defense, and cluster sync.*

### Rules (`/workspace/guardrails/configuration`)

**சுருக்கம் / Overview:** Safety policy definitions executed pre-LLM (input validation) and post-LLM (output validation) to mask PII and block prompt injections.

#### ⚙️ உட்புற கட்டமைப்பு & இயங்கும் முறை (Internal Architecture & Mechanics)
Located in 'plugins/guardrails/main.go'. Pre-compiles Google CEL expressions for lightning-fast execution. Evaluates input prompts before they reach external LLMs and output responses before they return to clients. Supported actions: Block request (400 Bad Request), Redact/Mask matching tokens (e.g. `[REDACTED_SSN]`), or Flag in logs.

#### 🧩 முக்கிய கூறுகள் & அமைப்புகள் (Key Components & Capabilities)
- **Pre-LLM Rules:**  Input scanning for prompt injection, jailbreak keywords, and leaked secrets.
- **Post-LLM Rules:**  Output scanning for hallucinated API keys, toxic output, or leaked PII.
- **Custom Actions:**  Block, Redact/Mask, Flag, or Replace.
- **Threshold Tuning:**  Custom sensitivity scores for classification models.

#### 🔗 மற்ற கூறுகளுடன் தொடர்பு (Module Interconnections)
Executes in Stage 2 (Pre-LLM) and Stage 6 (Post-LLM); annotates records in LLM Logs.

#### 💡 நடைமுறை பயன்பாடு (Enterprise Production Use Case)
Automatically detects and masks credit card numbers and Aadhaar numbers with `[REDACTED_PII]` before sending prompts to OpenAI.

---

### Providers (`/workspace/guardrails/providers`)

**சுருக்கம் / Overview:** Configuration console for specialized safety engines, including Presidio DLP, Llama Guard, AWS Bedrock Guardrails, and regex filters.

#### ⚙️ உட்புற கட்டமைப்பு & இயங்கும் முறை (Internal Architecture & Mechanics)
Adapters integrating dedicated detection engines: 1. Microsoft Presidio DLP (entity extraction for PII), 2. Meta Llama Guard (content moderation classification), 3. AWS Bedrock Guardrails (managed cloud safety), 4. Lakera AI (prompt injection & jailbreak defense), and 5. High-speed compiled regex engines.

#### 🧩 முக்கிய கூறுகள் & அமைப்புகள் (Key Components & Capabilities)
- **Presidio DLP Integration:**  Recognizes SSN, Credit Cards, Names, Phone Numbers, Email, Medical IDs.
- **Llama Guard Integration:**  Flags hate speech, violence, self-harm, and sexual content.
- **Regex Fast-Path:**  Zero-latency pattern matching for proprietary internal account numbers.

#### 🔗 மற்ற கூறுகளுடன் தொடர்பு (Module Interconnections)
Supplies detection capabilities to Guardrail Rules and Browser AI.

#### 💡 நடைமுறை பயன்பாடு (Enterprise Production Use Case)
Enables Meta Llama Guard to block adversarial jailbreak attempts ('Ignore all previous instructions...').

---

### Cluster Config (`/workspace/cluster`)

**சுருக்கம் / Overview:** Multi-node distributed cluster coordination engine synchronizing rules, rate limit counters, and configurations in real-time.

#### ⚙️ உட்புற கட்டமைப்பு & இயங்கும் முறை (Internal Architecture & Mechanics)
Coordinates distributed UnifAI gateway instances deployed in high-availability clusters. Uses pub/sub sync to propagate routing rule updates, newly issued virtual keys, and rate limit counters across all nodes in <50ms without restarting services.

#### 🧩 முக்கிய கூறுகள் & அமைப்புகள் (Key Components & Capabilities)
- **Node Discovery:**  Real-time health monitoring of all active cluster gateway instances.
- **Config Synchronization:**  Instant zero-downtime propagation of rule mutations.
- **Distributed Rate Limiting:**  Synchronized Redis counters preventing quota circumvention.

#### 🔗 மற்ற கூறுகளுடன் தொடர்பு (Module Interconnections)
Synchronizes Governance, Routing Rules, Guardrails, and Caching across all cluster nodes.

#### 💡 நடைமுறை பயன்பாடு (Enterprise Production Use Case)
A global deployment with 10 gateway instances across US-East and EU-West maintains synchronized rate limits and instant rule updates.

---

## Pillar 6: Adaptive Routing & Assets (ஸ்மார்ட் தேர்வு & அறிவு களஞ்சியம்)

*Adaptive Routing leverages reinforcement learning to optimize latency and cost while managing versioned prompt templates and agent skills.*

### Adaptive Routing Dashboard & Settings (`/workspace/adaptive-routing`)

**சுருக்கம் / Overview:** Reinforcement learning traffic router that continuously evaluates provider latency and error rates to steer requests to the fastest, cheapest model.

#### ⚙️ உட்புற கட்டமைப்பு & இயங்கும் முறை (Internal Architecture & Mechanics)
Implements Multi-Armed Bandit (MAB) optimization algorithms (Epsilon-Greedy, Thompson Sampling, Upper Confidence Bound UCB1). Continuously evaluates real-time latency, error rates, and token costs across equivalent candidate models. Dynamically shifts traffic weights to minimize p95 latency while adhering to cost budgets.

#### 🧩 முக்கிய கூறுகள் & அமைப்புகள் (Key Components & Capabilities)
- **Algorithm Selection:**  Toggle between Epsilon-Greedy, Thompson Sampling, and Latency-Weighted routing.
- **Latency vs Cost Sliders:**  Configurable weighting favoring speed vs dollar savings.
- **Exploration Ratio:**  Percentage of traffic reserved for testing slower/newer models.
- **Performance Dashboard:**  Visual charts showing dynamic weight distribution and latency improvements.

#### 🔗 மற்ற கூறுகளுடன் தொடர்பு (Module Interconnections)
Acts as an intelligent layer within Routing Rules; reads performance telemetry from LLM Logs.

#### 💡 நடைமுறை பயன்பாடு (Enterprise Production Use Case)
When Azure OpenAI experiences temporary latency spikes (p95 > 4000ms), the Adaptive Router automatically diverts 90% of traffic to AWS Bedrock.

---

### Prompt Repository (`/workspace/prompt-repo`)

**சுருக்கம் / Overview:** Centralized, version-controlled enterprise prompt repository supporting variable interpolation, test suites, and model bindings.

#### ⚙️ உட்புற கட்டமைப்பு & இயங்கும் முறை (Internal Architecture & Mechanics)
Enterprise prompt management engine. Stores parameterized prompt templates with Git-style versioning (v1, v2, production tag). Supports Mustache/Jinja variable interpolation (`{{customer_query}}`), parameter presets (temperature, top_p), and test suite benchmarking.

#### 🧩 முக்கிய கூறுகள் & அமைப்புகள் (Key Components & Capabilities)
- **Version Control:**  Full commit history, diffs, and instant rollback capabilities.
- **Variable Templating:**  Define required variables with default values and type validation.
- **Model Binding:**  Associate prompts with tested, approved model architectures.
- **Playground Testing:**  Interactive test console to execute templates against real models.

#### 🔗 மற்ற கூறுகளுடன் தொடர்பு (Module Interconnections)
Referenced by applications via prompt IDs; logged in LLM Logs; bound to specific Model Catalog entries.

#### 💡 நடைமுறை பயன்பாடு (Enterprise Production Use Case)
Prompt engineers update customer service prompt templates in UnifAI; microservices automatically consume the updated prompt without code redeployments.

---

### Skills Repository (`/workspace/skills-repo`)

**சுருக்கம் / Overview:** Standardized catalog of autonomous AI Agent instructions, domain personas, and specialized execution skill packages.

#### ⚙️ உட்புற கட்டமைப்பு & இயங்கும் முறை (Internal Architecture & Mechanics)
Stores modular, reusable agent skills (system instructions, role definitions, operational guardrails). Skills can be dynamically injected into LLM requests or bound to specific MCP Tool Groups to build autonomous agents.

#### 🧩 முக்கிய கூறுகள் & அமைப்புகள் (Key Components & Capabilities)
- **Skill Packages:**  Modular instructions (e.g. 'SQL-Expert', 'Python-Debugger', 'Compliance-Auditor').
- **Tool Bindings:**  Associate specialized skills directly with approved MCP tools.
- **Version History:**  Track refinements in agent behavior and system instructions.

#### 🔗 மற்ற கூறுகளுடன் தொடர்பு (Module Interconnections)
Combines with MCP Tool Groups and Prompt Repository to configure autonomous agents.

#### 💡 நடைமுறை பயன்பாடு (Enterprise Production Use Case)
Teams share a battle-tested 'Secure Code Reviewer' skill package across 20 different development squads.

---

## Pillar 7: Global Settings & Engine Tuning (கட்டமைப்பு & செயல்திறன் ட்யூனிங்)

*Platform-wide system configuration, wire compatibility translation, semantic vector caching, and network security.*

### Client Settings (`/workspace/config/client-settings`)

**சுருக்கம் / Overview:** Global connection timeouts, keep-alive settings, and header forward allowlists.

#### ⚙️ உட்புற கட்டமைப்பு & இயங்கும் முறை (Internal Architecture & Mechanics)
Configures network-level HTTP client behavior in FastHTTP. Defines header forwarding allowlists and blocklists, controlling which client headers are forwarded to upstream AI providers.

#### 🧩 முக்கிய கூறுகள் & அமைப்புகள் (Key Components & Capabilities)
- **Header Allowlists:**  Explicitly permit custom headers (x-uf-eh-*) to reach upstream providers.
- **Header Blocklists:**  Strip sensitive internal tracking headers before dispatch.
- **Keep-Alive Tuning:**  Configure client connection persistence and idle socket timeouts.

#### 🔗 மற்ற கூறுகளுடன் தொடர்பு (Module Interconnections)
Governs the inbound and outbound HTTP Transport layer.

#### 💡 நடைமுறை பயன்பாடு (Enterprise Production Use Case)
Allows microservices to forward custom transaction correlation IDs to upstream LLM providers while stripping internal cookies.

---

### Compatibility (`/workspace/config/compatibility`)

**சுருக்கம் / Overview:** Automated JSON API translation engine bridging OpenAI, Anthropic, AWS Bedrock, and Google Gemini schemas.

#### ⚙️ உட்புற கட்டமைப்பு & இயங்கும் முறை (Internal Architecture & Mechanics)
Located in 'plugins/compat'. Real-time schema converter. Enables client applications written with the OpenAI SDK (`/v1/chat/completions`) to interact seamlessly with Anthropic (`/v1/messages`), AWS Bedrock Converse, or Google Vertex AI without modifying a single line of client code.

#### 🧩 முக்கிய கூறுகள் & அமைப்புகள் (Key Components & Capabilities)
- **Schema Translation:**  Converts messages, roles (system/user/assistant), tools, and choices across provider formats.
- **Parameter Adaptation:**  Automatically converts or safely drops unsupported parameters (e.g. frequency_penalty).
- **Streaming SSE Normalization:**  Normalizes provider-specific SSE streaming chunks into standard OpenAI-compatible chunks.

#### 🔗 மற்ற கூறுகளுடன் தொடர்பு (Module Interconnections)
Executes inside the HTTP Transport layer before provider dispatch and after response receipt.

#### 💡 நடைமுறை பயன்பாடு (Enterprise Production Use Case)
An application built exclusively for OpenAI can switch seamlessly to Anthropic Claude 3.7 Sonnet by changing only the model name.

---

### Caching (Semantic Cache) (`/workspace/config/caching`)

**சுருக்கம் / Overview:** High-speed semantic vector caching engine using Redis or Qdrant to deliver instant, zero-cost responses for similar queries.

#### ⚙️ உட்புற கட்டமைப்பு & இயங்கும் முறை (Internal Architecture & Mechanics)
Implemented in 'plugins/semanticcache'. Combines direct SHA-256 hash lookup with vector embedding search. Generates vector embeddings of user queries using fast embedding models (OpenAI text-embedding-3-small or local BGE). Performs cosine similarity search against Qdrant / Redis vector partitions. If similarity >= threshold (default 0.90), returns cached answer in <15ms at $0.00 cost.

#### 🧩 முக்கிய கூறுகள் & அமைப்புகள் (Key Components & Capabilities)
- **Vector Store Backend:**  Connect to Redis Vector Engine or Qdrant.
- **Embedding Generator:**  Configurable embedding model source for vectorizing incoming prompts.
- **Similarity Threshold:**  Global cosine similarity threshold (e.g. 0.90).
- **Partition Keying:**  Scopes cache entries via `x-uf-cache-key`.
- **Streaming Cache:**  Caches streaming SSE chunks for seamless instant replay.

#### 🔗 மற்ற கூறுகளுடன் தொடர்பு (Module Interconnections)
Evaluated in Stage 3 of the request pipeline; records cache hit savings in Dashboard and LLM Logs.

#### 💡 நடைமுறை பயன்பாடு (Enterprise Production Use Case)
In high-volume customer support, 25% of queries are repeated questions; Semantic Caching answers them instantly, cutting monthly API spend by thousands of dollars.

---

### Security (`/workspace/config/security`)

**சுருக்கம் / Overview:** Enterprise network defense console managing TLS certificates, IP allowlists, CORS policies, and secret encryption.

#### ⚙️ உட்புற கட்டமைப்பு & இயங்கும் முறை (Internal Architecture & Mechanics)
Located in 'core/schemas/vault.go' and HTTP middleware. Enforces TLS 1.3 encryption in transit, encrypts API keys at rest using AES-256-GCM, validates incoming IP addresses against CIDR allowlists, and enforces strict Cross-Origin Resource Sharing (CORS) rules.

#### 🧩 முக்கிய கூறுகள் & அமைப்புகள் (Key Components & Capabilities)
- **AES-256-GCM Encryption:**  Master key encryption for all stored provider secrets and virtual keys.
- **IP CIDR Whitelisting:**  Restrict gateway access to designated corporate VPN or VPC IP subnets.
- **CORS Policy Manager:**  Whitelist allowed frontend web origins.
- **Direct Key Policy:**  Enable or disable `x-uf-direct-key` pass-through globally.

#### 🔗 மற்ற கூறுகளுடன் தொடர்பு (Module Interconnections)
Protects all incoming connections and secures all stored secrets in PostgreSQL.

#### 💡 நடைமுறை பயன்பாடு (Enterprise Production Use Case)
Security teams restrict UnifAI Gateway access exclusively to internal corporate VPC subnets and enforce TLS 1.3.

---

### API Keys (`/workspace/config/api-keys`)

**சுருக்கம் / Overview:** Administrative API key manager for automation, CI/CD pipelines, and infrastructure-as-code orchestration.

#### ⚙️ உட்புற கட்டமைப்பு & இயங்கும் முறை (Internal Architecture & Mechanics)
Issues and manages Control Plane Admin API Keys (`x-uf-api-key`). Used by Terraform providers, Kubernetes operators, and CI/CD pipelines to programmatically configure UnifAI.

#### 🧩 முக்கிய கூறுகள் & அமைப்புகள் (Key Components & Capabilities)
- **Admin Key Generation:**  Generate cryptographically random administrative keys.
- **Scope Assignment:**  Assign read-only or read-write permissions to admin keys.
- **Usage Tracking:**  Audit log of actions executed by each admin key.

#### 🔗 மற்ற கூறுகளுடன் தொடர்பு (Module Interconnections)
Authorizes programmatic control-plane configuration requests; recorded in Audit Logs.

#### 💡 நடைமுறை பயன்பாடு (Enterprise Production Use Case)
Terraform scripts use an Admin API Key to provision Virtual Keys and Routing Rules during automated environment spin-up.

---

### Performance Tuning (`/workspace/config/performance-tuning`)

**சுருக்கம் / Overview:** Low-level runtime performance tuning console for worker pool concurrency, memory pools, and buffer sizes.

#### ⚙️ உட்புற கட்டமைப்பு & இயங்கும் முறை (Internal Architecture & Mechanics)
Located in 'core/unifai.go'. Controls internal Go runtime parameters: FastHTTP request channel pool size (channelMessagePool), response stream pool (responseStreamPool), worker goroutine counts per provider queue, and memory buffer allocations.

#### 🧩 முக்கிய கூறுகள் & அமைப்புகள் (Key Components & Capabilities)
- **Worker Pool Size:**  Maximum concurrent worker goroutines per upstream provider queue.
- **Zero-Allocation Pool Sizing:**  Pre-allocated buffer capacity in `sync.Pool` to eliminate GC pauses.
- **Queue Overflow Policy:**  Block-and-wait vs immediate rejection (`dropExcessRequests`) under heavy traffic.

#### 🔗 மற்ற கூறுகளுடன் தொடர்பு (Module Interconnections)
Optimizes the execution performance of the entire core gateway engine.

#### 💡 நடைமுறை பயன்பாடு (Enterprise Production Use Case)
Under peak traffic of 50,000 requests/second, performance engineers tune worker pools to achieve zero GC pause times.

---

### Feature Flags (`/workspace/config/feature-flags`)

**சுருக்கம் / Overview:** Dynamic runtime feature toggles allowing administrators to enable, test, or disable capabilities without redeploying the gateway.

#### ⚙️ உட்புற கட்டமைப்பு & இயங்கும் முறை (Internal Architecture & Mechanics)
Maintained in 'framework/featureflags'. Real-time in-memory configuration flags synchronized across the cluster. Allows instant activation or deactivation of beta features (e.g. experimental routers, new provider adapters) with zero downtime.

#### 🧩 முக்கிய கூறுகள் & அமைப்புகள் (Key Components & Capabilities)
- **Dynamic Toggles:**  Enable or disable platform features in real-time.
- **Gradual Rollout:**  Enable beta capabilities for specific teams or virtual keys.
- **Instant Kill-Switch:**  Immediately disable problematic features without redeploying code.

#### 🔗 மற்ற கூறுகளுடன் தொடர்பு (Module Interconnections)
Controls code execution paths across all gateway modules.

#### 💡 நடைமுறை பயன்பாடு (Enterprise Production Use Case)
A platform team safely tests an experimental new reasoning router with internal engineers before enabling it organization-wide.

---

### Enterprise Outbound Proxy (`/workspace/config/proxy`)

**சுருக்கம் / Overview:** Corporate forward and reverse proxy configuration routing outbound AI traffic through enterprise egress gateways.

#### ⚙️ உட்புற கட்டமைப்பு & இயங்கும் முறை (Internal Architecture & Mechanics)
Located in 'ui/app/workspace/config/views/proxyView.tsx' and core transport. Enables UnifAI to route all outbound LLM API requests through corporate forward proxies (HTTP, HTTPS, SOCKS5, TCP). Supports basic proxy authentication, corporate bypass allowlists (CIDR / hostnames), and custom CA certificate bundles for SSL inspection.

#### 🧩 முக்கிய கூறுகள் & அமைப்புகள் (Key Components & Capabilities)
- **Proxy Protocol:**  HTTP, HTTPS, SOCKS5, and TCP egress.
- **Authentication:**  Basic authentication (Username / Password) for proxy gateways.
- **No-Proxy Bypass List:**  Whitelist of hostnames and IP ranges (localhost, 127.0.0.1, internal VPCs) bypassing the proxy.
- **Custom CA Bundle:**  Enterprise root CA certificate upload for corporate SSL inspection proxies.

#### 🔗 மற்ற கூறுகளுடன் தொடர்பு (Module Interconnections)
Wraps all outbound HTTP and WebSocket connections to Model Providers and external MCP servers.

#### 💡 நடைமுறை பயன்பாடு (Enterprise Production Use Case)
Enterprises in banking and defense require all external internet traffic to traverse corporate BlueCoat or Zscaler egress proxies.

---

### Large Payload Streaming Engine (`/workspace/config/large-payload`)

**சுருக்கம் / Overview:** Zero-memory direct streaming engine designed for massive multimodal outputs, audio files, and 100k+ token responses.

#### ⚙️ உட்புற கட்டமைப்பு & இயங்கும் முறை (Internal Architecture & Mechanics)
Implemented in 'transports/unifai-http/integrations/utils.go' (tryStreamLargeResponse). Detects responses exceeding the memory buffer threshold and bypasses gateway memory allocations entirely, streaming chunked transfer encoding directly from the upstream provider to the client.

#### 🧩 முக்கிய கூறுகள் & அமைப்புகள் (Key Components & Capabilities)
- **Payload Threshold Slider:**  Configures byte ceiling (e.g. 5MB) triggering large payload bypass.
- **Direct Pipe Streaming:**  Eliminates memory buffering to avoid out-of-memory crashes on massive generations.
- **Multimodal Asset Transfer:**  Optimized for high-resolution vision models, image generation, and audio synthesis.

#### 🔗 மற்ற கூறுகளுடன் தொடர்பு (Module Interconnections)
Integrates directly with FastHTTP response writer pool and Upstream LLM Providers.

#### 💡 நடைமுறை பயன்பாடு (Enterprise Production Use Case)
Prevents gateway memory exhaustion when 1,000 concurrent clients download multi-megabyte audio or high-resolution image generation files.

---

### Alert Channels (Enterprise Notifications) (`/workspace/alert-channels`)

**சுருக்கம் / Overview:** Multi-channel automated alerting engine broadcasting budget thresholds, circuit breaker trips, and error spikes to enterprise ops tools.

#### ⚙️ உட்புற கட்டமைப்பு & இயங்கும் முறை (Internal Architecture & Mechanics)
Implemented in '@enterprise/components/alert-channels/alertChannelsView'. Listens to internal event buses for budget exhaustion events, provider circuit breaker trips, and p95 latency spikes. Formats incident payloads and delivers them to Slack Webhooks, PagerDuty, Microsoft Teams, Discord, and Email.

#### 🧩 முக்கிய கூறுகள் & அமைப்புகள் (Key Components & Capabilities)
- **Channel Connectors:**  Slack Webhooks, PagerDuty Incident API, Microsoft Teams, Email (SMTP), and Custom Webhooks.
- **Trigger Rules:**  Budget Warning (80% / 100% spend), Circuit Breaker Trip, Error Spike (>5% 5xx), Rate Limit Throttle.
- **Notification Throttling:**  Configurable cooldown windows preventing alert storms during major outages.

#### 🔗 மற்ற கூறுகளுடன் தொடர்பு (Module Interconnections)
Receives alert signals from Budgets & Limits, Circuit Breaker, and Observability.

#### 💡 நடைமுறை பயன்பாடு (Enterprise Production Use Case)
When OpenAI goes down and the Circuit Breaker trips to Claude, an immediate alert is dispatched to the DevOps Slack channel and PagerDuty.

---

### MCP Authentication Config & Credential Vault (`/workspace/mcp-auth-config`)

**சுருக்கம் / Overview:** Centralized credential vault managing per-user headers, API keys, and OAuth client credentials for external MCP servers.

#### ⚙️ உட்புற கட்டமைப்பு & இயங்கும் முறை (Internal Architecture & Mechanics)
Located in 'core/mcp/credstore'. Stores and resolves authentication credentials for MCP servers. Supports static API keys, per-user HTTP headers, and dynamic OAuth 2.0 client secrets with AES-256-GCM encryption.

#### 🧩 முக்கிய கூறுகள் & அமைப்புகள் (Key Components & Capabilities)
- **Auth Mode Selector:**  Static API Key, Per-User Headers, or OAuth 2.0 PKCE.
- **Header Mapping:**  Maps client request headers to tool execution headers.
- **Encrypted Vault:**  Hardware-grade encryption for third-party service tokens.

#### 🔗 மற்ற கூறுகளுடன் தொடர்பு (Module Interconnections)
Supplies authorized credentials to MCP Catalog, Tool Groups, and Auth Sessions.

#### 💡 நடைமுறை பயன்பாடு (Enterprise Production Use Case)
Enables an AI agent to authenticate with internal Jira and GitHub enterprise servers using dynamic corporate service accounts.

---

### Starlark Sandboxed Code Mode (`core/mcp/codemode/starlark`)

**சுருக்கம் / Overview:** Embedded Python-like sandboxed execution engine enabling AI agents to run multi-tool workflows and data transformations in-memory.

#### ⚙️ உட்புற கட்டமைப்பு & இயங்கும் முறை (Internal Architecture & Mechanics)
Implemented in 'core/mcp/codemode/starlark'. Leverages Google Starlark (the deterministic language behind Bazel). Agents generate Starlark code to orchestrate multiple tools, perform mathematical calculations, and transform data in a secure, memory-isolated sandbox without executing untrusted OS commands.

#### 🧩 முக்கிய கூறுகள் & அமைப்புகள் (Key Components & Capabilities)
- **Deterministic Sandbox:**  Non-Turing complete runtime preventing infinite loops and filesystem access.
- **Tool Binding Interface:**  Exposes registered MCP tools as native Starlark functions.
- **In-Memory Execution:**  Zero network latency between multi-step tool calls.

#### 🔗 மற்ற கூறுகளுடன் தொடர்பு (Module Interconnections)
Integrates directly into MCP Gateway and Tool Groups.

#### 💡 நடைமுறை பயன்பாடு (Enterprise Production Use Case)
An autonomous data science agent queries a SQL database, filters 10,000 rows, and calculates summary statistics in-memory in under 50ms.

---

### Hardware Secrets Vault & Envelope Encryption (`core/schemas/vault.go`)

**சுருக்கம் / Overview:** Cryptographic envelope encryption vault securing all stored provider API keys, virtual keys, and credentials at rest.

#### ⚙️ உட்புற கட்டமைப்பு & இயங்கும் முறை (Internal Architecture & Mechanics)
Located in 'core/schemas/vault.go'. Employs AES-256-GCM authenticated encryption. Every secret is encrypted with a unique Data Encryption Key (DEK), which is in turn encrypted with a Master Key (KEK) stored in AWS KMS, Google Cloud KMS, HashiCorp Vault, or Infisical.

#### 🧩 முக்கிய கூறுகள் & அமைப்புகள் (Key Components & Capabilities)
- **AES-256-GCM Encryption:**  Authenticated cipher preventing tampering and eavesdropping.
- **Envelope Encryption:**  Multi-tier key hierarchy (Master Key / Data Keys).
- **KMS Integration:**  Seamless integration with AWS KMS, Google Cloud KMS, and Infisical.

#### 🔗 மற்ற கூறுகளுடன் தொடர்பு (Module Interconnections)
Protects secrets across Model Providers, Virtual Keys, and MCP Gateway.

#### 💡 நடைமுறை பயன்பாடு (Enterprise Production Use Case)
Guarantees that even if the PostgreSQL database backup is stolen, all OpenAI and Anthropic provider keys remain mathematically unreadable.

---

### Key Load Balancer & Key Pool Filtering (`framework/loadbalancer`)

**சுருக்கம் / Overview:** Advanced multi-key load balancing engine distributing traffic across credential pools with session stickiness.

#### ⚙️ உட்புற கட்டமைப்பு & இயங்கும் முறை (Internal Architecture & Mechanics)
Implemented in 'framework/loadbalancer' and 'core/keyselectors'. Supports Round-Robin, Weighted Distribution, and Priority Failover across multiple provider keys. Integrates with Redis KVStore for session stickiness, pinning multi-turn conversations to the same key or GPU node.

#### 🧩 முக்கிய கூறுகள் & அமைப்புகள் (Key Components & Capabilities)
- **Balancing Strategies:**  Round-Robin, Weighted Ratios, Priority Tiers, and Least-Connections.
- **Session Stickiness:**  Binds conversational sessions (via x-uf-session-id) to the same upstream deployment.
- **Key Pool Filters:**  Custom hooks (keyPoolFilter) to dynamically disqualify degraded or rate-limited keys.

#### 🔗 மற்ற கூறுகளுடன் தொடர்பு (Module Interconnections)
Operates inside the Models and Model Providers dispatch pipeline.

#### 💡 நடைமுறை பயன்பாடு (Enterprise Production Use Case)
Distributes 100,000 RPM evenly across 10 Azure OpenAI deployments in different geographic regions with automatic failover.

---

### Realtime Audio & Voice Gateway (`core/schemas/realtime.go`)

**சுருக்கம் / Overview:** Bidirectional WebRTC and WebSocket streaming gateway supporting ultra-low latency conversational voice AI.

#### ⚙️ உட்புற கட்டமைப்பு & இயங்கும் முறை (Internal Architecture & Mechanics)
Located in 'core/schemas/realtime.go'. Bridges client WebRTC and WebSocket voice connections to upstream providers (e.g. OpenAI Realtime API). Manages full-duplex audio chunking (PCM16, G.711, Opus), Voice Activity Detection (VAD), and automated speech-to-speech protocol normalization.

#### 🧩 முக்கிய கூறுகள் & அமைப்புகள் (Key Components & Capabilities)
- **Full-Duplex Audio Streaming:**  Sub-300ms voice conversational latency.
- **Protocol Normalization:**  Bidirectional audio frame translation across voice providers.
- **Voice Activity Detection (VAD):**  Server-side speech interruption and turn-taking detection.

#### 🔗 மற்ற கூறுகளுடன் தொடர்பு (Module Interconnections)
Connects clients to Voice-enabled Model Providers and logs audio tokens in LLM Logs.

#### 💡 நடைமுறை பயன்பாடு (Enterprise Production Use Case)
Powers customer service interactive voice response (IVR) phone bots with natural human-like voice conversational speed.

---

# 5. Cross-Feature Interconnection & Data Flow Matrix
### இணைப்பு வரைபடம் (எப்படி ஒன்றுடன் ஒன்று இணைகிறது?)

| மூல கூறு (Source Module) | இணைக்கப்பட்டுள்ள கூறுகள் (Connected Modules) | தொழில்நுட்ப தொடர்பு & Data Flow (Technical Relationship) |
| :--- | :--- | :--- |
| **Virtual Keys** | Users, Teams, Customers, Budgets, Access Profiles | Authenticates request; resolves quota limits, team ownership, and access profile. |
| **Access Profiles** | Model Catalog, MCP Tool Groups | Restricts the virtual key to specific approved models and MCP tool groups. |
| **Complexity Router** | Routing Rules, Model Catalog | Classifies prompt tier (Simple/Reasoning) and sets context for routing rules. |
| **Routing Rules** | Model Providers, Circuit Breaker | Evaluates CEL expressions; passes target provider to Circuit Breaker for health check. |
| **Circuit Breaker** | Routing Rules, Fallback Providers | If primary provider is TRIPPED, automatically switches to next configured fallback. |
| **Guardrails Rules** | Guardrail Providers, LLM Pipeline | Intercepts prompt pre-LLM and response post-LLM; runs PII/injection validation. |
| **Semantic Cache** | Vector Store, Models Pipeline | Intercepts request before LLM; returns cached hit or stores new completion on miss. |
| **MCP Tool Groups** | MCP Catalog, Virtual Keys | Injects approved tool JSON schemas into LLM prompt; audits calls in MCP Logs. |
| **Browser AI** | Guardrails, Observability | Intercepts browser web AI queries, runs DLP guardrail rules, logs to Browser AI logs. |
| **Pricing Overrides** | Dashboard, Budgets & Limits, LLM Logs | Computes exact dollar cost per token; updates budget balances and dashboard graphs. |
| **Connectors** | LLM Logs, MCP Logs, Audit Logs | Streams structured JSON telemetry to external platforms (Datadog, Kafka, BigQuery). |
| **SCIM Provisioning** | Users, Teams, RBAC | Automatically provisions enterprise IdP accounts and maps them into UnifAI roles. |

# 6. Technology Stack & Programming Languages Deep Dive
### தொழில்நுட்ப கட்டமைப்பு & தேர்வு செய்யப்பட்டதற்கான காரணங்கள்

| அடுக்கு (Layer) | தொழில்நுட்பம் / மொழி (Tech Stack) | பயன்பாடு & கட்டடக்கலை நன்மை (Architectural Benefit & Rationale) |
| :--- | :--- | :--- |
| **Core Gateway Engine** | `Go (Golang 1.23+)` | Ultra-low proxy latency (<1ms), lightweight goroutine concurrency, memory safety, and native zero-allocation memory pools (sync.Pool). |
| **HTTP & Networking** | `FastHTTP & Sonic JSON` | FastHTTP avoids per-request heap allocations of standard net/http. ByteDance's Sonic JIT compiler parses JSON at near-native assembly speeds. |
| **Rule Evaluation Engine** | `Google CEL (Common Expression Language)` | Safe, non-Turing complete expression evaluation. Compiles routing rules and guardrail policies into bytecode, executing in microseconds. |
| **Agent Scripting Sandbox** | `Starlark (Google Bazel Language)` | Deterministic, thread-safe, sandboxed Python-like language for executing dynamic custom plugins without security risk. |
| **Frontend Web Application** | `TypeScript 5.x, React 18, Vite` | Strict compile-time type safety across all 38 UI views, instant HMR development, and optimized single-page app bundle delivery. |
| **Routing & UI Components** | `TanStack Router, Tailwind CSS, Radix UI` | TanStack Router provides preload-on-hover routing for instantaneous navigation. Radix UI (Shadcn) delivers accessible, sleek dark-mode components. |
| **State Management** | `Redux Toolkit (RTK Query), WebSockets` | Manages client-side caching, optimistic UI updates, and real-time live metrics streaming via WebSockets. |
| **Desktop / Browser DLP Agent** | `Python 3.11+, mitmproxy / asyncio` | Mature networking and proxy ecosystem for local HTTPS interception, regex matching, and integration with local Ollama models. |
| **Relational Database** | `PostgreSQL (pgx v5 driver), SQLite, GORM` | ACID transactional storage for Governance, Virtual Keys, Audit Logs, and Budgets. pgx provides high-performance connection pooling. |
| **Caching & Vector Store** | `Redis (go-redis), Qdrant, pgvector` | Sub-millisecond sliding-window rate limiting in Redis, and high-throughput vector similarity search for Semantic Caching in Qdrant. |
| **Telemetry & Observability** | `OpenTelemetry (OTel), Prometheus, Datadog, Kafka` | W3C standard distributed tracing, Prometheus metric scrapers, and event-driven enterprise streaming to Kafka and Datadog. |
| **DevOps & Build System** | `Docker, Docker Compose, Nix / Flake, Makefile` | Hermetic, reproducible development and build environments across multi-platform container architectures. |


# 7. Enterprise Production Scenarios & Playbooks
### நடைமுறை பயன்பாடுகள் & தயாரிப்பு காட்சிகள் (Playbooks)

### Scenario 1: Multi-Tenant B2B SaaS Cost Attribution
- **சவால் (Challenge):** ஒரு B2B SaaS நிறுவனம் 500 நிறுவன வாடிக்கையாளர்களுக்கு ஒரே AI அசிஸ்டெண்ட்டை வழங்குகிறது. ஒவ்வொரு வாடிக்கையாளரும் எவ்வளவு AI செலவு செய்கிறார்கள் என்று துல்லியமாக பில் செய்ய வேண்டும்.
- **தீர்வு (Solution):** Backend சேவை `x-uf-customer-id: cust_42` ஹெடரை இணைத்து UnifAI வழியாக அழைக்கிறது. UnifAI ஒவ்வொரு வாடிக்கையாளரின் டோக்கன் மற்றும் டாலர் செலவை தனித்தனியாக பிரித்து BigQuery-க்கு stream செய்கிறது. மாத இறுதியில் தானியங்கி இன்வாய்ஸ் உருவாக்கப்படுகிறது.

### Scenario 2: Zero-Downtime High Availability Failover
- **சவால் (Challenge):** OpenAI சர்வர்கள் செயலிழக்கும்போது அல்லது 504 Gateway Timeouts வரும்போது, வாடிக்கையாளர் சேவை சாட்பாட் முடங்கி விடுகிறது.
- **தீர்வு (Solution):** `gpt-4o` மாடலுக்கு Circuit Breaker அமைக்கப்பட்டு, 50% தோல்வி விகிதம் ஏற்பட்டால் Anthropic `claude-3-5-sonnet` மாடலுக்கு தானாக மாறுகிறது. <100ms-ல் failover முடிந்து, அழைப்பாளருக்கு `x-unifai-fallback-index: 1` ஹெடர் திரும்புகிறது. ஒரு பயனர் அமர்வும் பாதிக்கப்படுவதில்லை.

### Scenario 3: Slashing Costs via Complexity Router & Semantic Cache
- **சவால் (Challenge):** ஒரு நாளைக்கு 1,000,000 கேள்விகள் வருகின்றன. 60% கேள்விகள் எளிய கேள்விகள் ('கடை எப்போது திறக்கும்?'). ஆனால் அனைத்திற்கும் விலையுயர்ந்த Frontier மாடல்கள் பயன்படுத்தப்படுவதால் மாதாந்திர பில் $45,000 ஆகிறது.
- **தீர்வு (Solution):** Semantic Caching 25% கேள்விகளுக்கு Redis-ல் இருந்து உடனடி பதிலை $0.00 செலவில் அளிக்கிறது. மீதமுள்ள எளிய கேள்விகளை Complexity Router அடையாளம் கண்டு `gpt-4o-mini` ($0.15/1M) மாடலுக்கும், கடினமான கேள்விகளை மட்டும் `o1` மாடலுக்கும் அனுப்புகிறது. மொத்த செலவு $9,800 ஆக (78% குறைவு) குறைகிறது.

### Scenario 4: Enterprise Data Loss Prevention (DLP) using Browser AI
- **சவால் (Challenge):** நிறுவன ஊழியர்கள் பொது ChatGPT தளத்தில் நிறுவனத்தின் ரகசிய சோர்ஸ் கோட், வாடிக்கையாளர் ஆதார் எண்கள் மற்றும் API சாவி-களை பேஸ்ட் செய்து விடுகிறார்கள்.
- **தீர்வு (Solution):** ஊழியர்களின் மடிக்கணினிகளில் UnifAI Browser AI agent நிறுவப்படுகிறது. ஊழியர் ChatGPT தளத்தில் ஏதேனும் ரகசிய தகவலை பேஸ்ட் செய்யும்போது, Browser AI உடனடியாக தடுத்து நிறுத்தி, Audit Logs-ல் எச்சரிக்கையை பதிவு செய்கிறது.
