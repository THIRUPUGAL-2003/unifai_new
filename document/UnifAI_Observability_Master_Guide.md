# UnifAI Observability Master Deep-Dive Guide
## UnifAI கண்காணிப்பு அமைப்பின் முழுமையான உடற்கூறு ஆய்வு (Tech & Non-Tech Master Manual)

**Module:** Observability (கண்காணிப்பு & செயல்திறன் பகுப்பாய்வு)  
**Target Audience:** Developers, System Architects, CTOs, Product Managers & Operations Teams  
**Generated At:** 2026-09-05  
**Format:** Bilingual (Tamil & English Technical Guide)  

---

## Table of Contents (பொருளடக்கம்)
1. [Observability System Architecture & Structure Map (முழுமையான கட்டமைப்பு வரைபடம்)](#1-observability-system-architecture--structure-map)
2. [Detailed Feature Dissection (6 Core Observability Features)](#2-detailed-feature-dissection)
   - [Dashboard (கண்காணிப்பு முகப்புத் திரை) (/workspace/dashboard)](#dashboard)
   - [LLM Logs (AI கோரிக்கை பரிவர்த்தனை பதிவேடு) (/workspace/logs)](#llm_logs)
   - [MCP Logs (ஏஜென்ட் டூல்ஸ் இயக்கப் பதிவேடு) (/workspace/mcp-logs)](#mcp_logs)
   - [Browser AI (பிரவுசர் பாதுகாப்பு & DLP ப்ராக்ஸி) (/workspace/browser-ai)](#browser_ai)
   - [Connectors (வெளிப்புற கண்காணிப்பு இணைப்பு குழாய்கள்) (/workspace/observability)](#connectors)
   - [Logs Settings (பதிவேடு அமைப்புகள் & கொள்கைகள்) (/workspace/config/logging)](#logs_settings)
3. [Cross-Feature Interconnections & Data Flow (அம்சங்களுக்கிடையேயான தொடர்பு)](#3-cross-feature-interconnections--data-flow)
4. [Tech vs Non-Tech Comparative Matrix (தொழில்நுட்ப & வணிக பார்வை ஒப்பீடு)](#4-tech-vs-non-tech-comparative-matrix)

---

# 1. Observability System Architecture & Structure Map
### முழுமையான கட்டமைப்பு & தரவு ஓட்டம் (Data Flow Map)

```
                    [ INCOMING AI REQUESTS & AGENT TOOL CALLS ]
                                        │
                                        ▼
      ┌───────────────────────────────────────────────────────────────────┐
      │               FastHTTP PROXY & MCP INTERCEPTOR                    │
      │  • Captures Request Headers, Prompts, User Tokens, Virtual Keys   │
      │  • Measures Time-To-First-Token (TTFT) and Total Latency          │
      └─────────────────┬───────────────────────────────┬─────────────────┘
                        │                               │
          [LLM Calls]   ▼                 [Tool Calls]  ▼
      ┌─────────────────────────┐           ┌─────────────────────────┐
      │       LLM LOGS          │           │        MCP LOGS         │
      │  • Prompts & Responses  │           │  • Tool Arguments       │
      │  • Cost ($), Tokens     │           │  • Tool Outputs         │
      │  • Guardrail Verdicts   │           │  • Execution Time (ms)  │
      └────────────┬────────────┘           └────────────┬────────────┘
                   │                                     │
                   ├──────────────────┬──────────────────┤
                   ▼                  ▼                  ▼
      ┌─────────────────────────┐ ┌─────────────────────────┐ ┌─────────────────────────┐
      │       DASHBOARD         │ │       CONNECTORS        │ │      LOGS SETTINGS      │
      │  • Realtime Metrics     │ │  • Datadog APM Spans    │ │  • Retention Schedules  │
      │  • p95/p99 Latencies    │ │  • Apache Kafka Topics  │ │  • Traffic Sampling %   │
      │  • Cost Aggregations    │ │  • BigQuery Billing     │ │  • PII Content Redactor │
      │  • Cache Hit Ratios     │ │  • OpenTelemetry (OTel) │ │  • S3 / GCS Archival    │
      └─────────────────────────┘ └─────────────────────────┘ └─────────────────────────┘
                   ▲
                   │  (Employee Web AI Interception)
      ┌────────────┴────────────┐
      │       BROWSER AI        │
      │  • Local DLP Proxy      │
      │  • Attachment Scanner   │
      │  • Policy Violations    │
      └─────────────────────────┘
```

# 2. Detailed Feature Dissection (6 Core Observability Features)
### ஆறு அம்சங்களின் விரிவான உடற்கூறு ஆய்வு

<a name='dashboard'></a>
## Dashboard (கண்காணிப்பு முகப்புத் திரை)
**UI Route:** `/workspace/dashboard`

### 👤 Non-Tech Perspective (சாதாரண மனிதர்களுக்கான எளிய விளக்கம்)
- **உருவகம் (Analogy):** விமானத்தின் காக்பிட் (Airplane Cockpit) அல்லது சொகுசு காரின் டேஷ்போர்டு போன்றது.
- **விளக்கம் (Explanation):** ஒரு கார் ஓட்டும்போது ஸ்பீடோமீட்டர் வேகம், பெட்ரோல் அளவு மற்றும் இன்ஜின் நிலைமை காட்டுவது போல, கம்பெனியில் AI பயன்பாடு எப்படி நடக்கிறது என்பதை தலைவர்கள் ஒரே பார்வையில் பார்க்கும் இடம். இன்று எத்தனை லட்சம் AI கேள்விகள் கேட்கப்பட்டது, எவ்வளவு டாலர் செலவாகியுள்ளது, எந்த AI மாடல் வேகமாக இயங்குகிறது, எந்த டீம் அதிக டோக்கன் பயன்படுத்துகிறது என்பதை நிகழ்நேரத்தில் (Realtime Graphs) காட்டும்.
- **வணிக மதிப்பு (Business Value):** செலவை உடனுக்குடன் கட்டுப்படுத்தலாம்; திடீரென பில் எகிறாமல் தடுக்கலாம்; AI அமைப்பின் வேகத்தை கண்காணிக்கலாம்.

### 💻 Tech Perspective (பொறியாளர்களுக்கான தொழில்நுட்ப விளக்கம்)
- **Backend Architecture:** The Dashboard is powered by a persistent WebSocket connection ('useWebSocket') synchronized with TanStack Query. Backend telemetry is collected at the FastHTTP transport layer using lock-free atomic counters (sync/atomic). Metrics are aggregated into time-series buckets (1-min, 5-min, 1-hour intervals) and queried via PostgreSQL. Calculates percentile response times (p50, p90, p95, p99) and Time-To-First-Token (TTFT). Dynamically prices token volumes using live rules from Pricing Overrides.
- **Backend Endpoints:**
  * `GET /api/v1/dashboard/stats`
  * `GET /api/v1/dashboard/histogram`
  * `WS /api/v1/ws/dashboard`


### 🖥️ Screen Layout & Bottom Elements (திரை கூறுகள் & பட்டன்கள்)
**1. மேல்புற கட்டுப்பாடுகள் (Top Bar Controls):**
- Time Period Selector: Quick toggles for 1h, 24h, 7d, 30d, and custom date range.
- Date Range Picker (DateTimePickerWithRange): Calendar and time modal for custom historical analysis.
- Timezone Dropdown: Switch between UTC and Local Browser Timezone.
- Export Popover Button: Download metrics in CSV, JSON, or PNG chart formats.
- Filter Sidebar Toggle Button: Slides out 'LogsFilterSidebar' to filter by Virtual Keys, Providers, and Models.

**2. மத்திய திரைக் கூறுகள் & வரைபடங்கள் (Tabs & Views):**
- Overview Tab: Request volume charts, total token consumption, total spend ($), and p50/p95/p99 latency curves.
- Provider Usage Tab: Comparative traffic distribution across OpenAI, Anthropic, Bedrock, and Ollama.
- Model Rankings Tab: Leaderboard of top models ranked by request count, cost, and latency.
- Dimension Rankings Tab: Usage breakdown by custom tags passed in 'x-uf-dim-*' (e.g. environment, department).
- MCP Tab: Volume and dollar cost incurred specifically by Model Context Protocol tool executions.
- Chart Type Toggle: Button switching between Line Graph and Bar Chart views.

**3. கீழ்புற கூறுகள், படிவங்கள் & ஸ்லைடு-ஓவர் ஷீட்டுகள் (Bottom Elements & Sheets):**
- Model Filter Select: Dropdown isolating individual model trends.
- Cache Hit Ratio Meter: Live gauge showing percentage of requests resolved via Semantic Cache at $0 cost.


### 🔗 Connection & Structure Map (இணைப்புகள் & செயல்பாடுகள்)
- **தரவை எங்கிருந்து பெறுகிறது (Receives Data From):** Aggregates real-time data from LLM Logs, Pricing Overrides, and Semantic Caching.
- **எதனை இயக்குகிறது / பாதிக்கிறது (Triggers & Affects):** If error rates spike >5% or spending exceeds 80% of budget, triggers automated alerts to Alert Channels (Slack/PagerDuty).

### 💡 Real-World Enterprise Use Case (நடைமுறை பயன்பாட்டு உதாரணம்)
ஒரு ஃபின்டெக் கம்பெனியின் CTO காலை 9 மணிக்கு டேஷ்போர்டைப் பார்த்து, நேற்று இரவு OpenAI-ல் ஏற்பட்ட லேடன்சி ஸ்பைக்கை (p99 > 4000ms) கண்டறிந்து, ரூட்டிங் விதியை Claude-க்கு மாற்ற உத்தரவிடுகிறார்.

---

<a name='llm_logs'></a>
## LLM Logs (AI கோரிக்கை பரிவர்த்தனை பதிவேடு)
**UI Route:** `/workspace/logs`

### 👤 Non-Tech Perspective (சாதாரண மனிதர்களுக்கான எளிய விளக்கம்)
- **உருவகம் (Analogy):** வங்கியின் பாஸ்புக் (Bank Statement) + அலுவலகத்தின் சிசிடிவி கேமரா பதிவு (CCTV Footage).
- **விளக்கம் (Explanation):** யார், எப்போது, எந்த AI மாடலிடம் என்ன கேள்வி கேட்டார்கள்? மாடல் என்ன பதில் தந்தது? அதற்கு எத்தனை ரூபாய்/டாலர் செலவானது? பதில் வர எத்தனை விநாடி எடுத்தது? ஏதேனும் ரகசிய ஆதார்/கிரெடிட் கார்டு தகவல்கள் மறைக்கப்பட்டதா? என்பதை ஒவ்வொரு பரிவர்த்தனையாக அக்குவேறு ஆணிவேறாகப் பதிவு செய்து வைக்கும் ரசீது புத்தகம்.
- **வணிக மதிப்பு (Business Value):** பிழைகளை உடனடியாக சரிசெய்யலாம் (Debugging), சட்ட ரீதியான தணிக்கைக்கு (Audit Compliance) முழு ஆதாரம் கிடைக்கும்.

### 💻 Tech Perspective (பொறியாளர்களுக்கான தொழில்நுட்ப விளக்கம்)
- **Backend Architecture:** Implemented with an asynchronous, non-blocking ring-buffer queue ('framework/logstore'). FastHTTP request context captures exact request headers, messages, and wire bytes. A decoupled worker pool writes micro-batches to PostgreSQL using 'pgx v5' connection pooling. Every log row records: request_id, session_id, virtual_key_id, provider, requested_model, resolved_model, prompt_tokens, completion_tokens, total_tokens, cost_usd, latency_ms, ttft_ms, status_code, and guardrail_verdict.
- **Backend Endpoints:**
  * `GET /api/v1/logs`
  * `GET /api/v1/logs/:id`
  * `POST /api/v1/logs/delete`


### 🖥️ Screen Layout & Bottom Elements (திரை கூறுகள் & பட்டன்கள்)
**1. மேல்புற கட்டுப்பாடுகள் (Top Bar Controls):**
- Top Metric Cards: Live animated counters for Total Requests, Total Cost ($), Total Tokens, and Errors.
- Search Input Bar: Full-text and regex search matching keywords inside prompt or completion text.
- WebSocket Live Indicator: Animated green pulsing dot indicating real-time log ingestion.
- Column Customizer (useColumnConfig): Dropdown to show/hide specific table columns.
- Export CSV Button: Download filtered log entries as CSV.
- Delete Logs Button: Role-protected button (RBAC) to delete historical records.

**2. மத்திய திரைக் கூறுகள் & வரைபடங்கள் (Tabs & Views):**
- Collapsible Logs Volume Chart: Hourly/Daily bar graph displaying traffic spikes above the table.
- Logs Data Table: Columns for Timestamp, Status (Badge), Model (Original -> Resolved), Provider Icon, Virtual Key, Customer ID, Latency, Tokens, Cost ($), Actions.

**3. கீழ்புற கூறுகள், படிவங்கள் & ஸ்லைடு-ஓவர் ஷீட்டுகள் (Bottom Elements & Sheets):**
- LogDetailSheet (Slide-over): Opens on row click. 4 Tabs: (1) Request (headers & prompt), (2) Response (completion & finish reason), (3) Guardrails (verdict & redacted entities), (4) Trace (spans & TTFT breakdown).
- SessionDetailsSheet (Slide-over): Chronological multi-turn conversation replay for requests sharing the same 'x-uf-session-id'.
- Row Action Dropdown: 'Copy Request ID', 'Copy cURL Command', 'View Raw Wire Bytes'.


### 🔗 Connection & Structure Map (இணைப்புகள் & செயல்பாடுகள்)
- **தரவை எங்கிருந்து பெறுகிறது (Receives Data From):** Intercepts every HTTP and WebSocket request flowing through the FastHTTP Gateway.
- **எதனை இயக்குகிறது / பாதிக்கிறது (Triggers & Affects):** Feeds Dashboard metrics, drains event streams to Connectors (Datadog/Kafka), and validates Guardrail rule accuracy.

### 💡 Real-World Enterprise Use Case (நடைமுறை பயன்பாட்டு உதாரணம்)
ஒரு மருத்துவர் AI-யிடம் ஒரு நோயாளியின் தரவை உள்ளிடும்போது, அவரது பெயர் மற்றும் மொபைல் எண் '[REDACTED_PII]' என மாற்றப்பட்டு பாதுகாப்பாக அனுப்பப்பட்டதா என செக்யூரிட்டி அதிகாரி Logs-ல் சரிபார்க்கிறார்.

---

<a name='mcp_logs'></a>
## MCP Logs (ஏஜென்ட் டூல்ஸ் இயக்கப் பதிவேடு)
**UI Route:** `/workspace/mcp-logs`

### 👤 Non-Tech Perspective (சாதாரண மனிதர்களுக்கான எளிய விளக்கம்)
- **உருவகம் (Analogy):** ஒரு மெக்கானிக் அல்லது ஊழியர் பயன்படுத்திய கருவிகளின் டைரி (Tools Usage Audit Book).
- **விளக்கம் (Explanation):** இன்றைய AI வெறும் பதில் மட்டும் சொல்வதில்லை; அது டேட்டாபேஸை அணுகுகிறது, GitHub-ல் கோட் உருவாக்குகிறது, Slack-ல் மெசேஜ் அனுப்புகிறது. அப்படி AI ஏஜென்ட் இயக்கிய ஒவ்வொரு வெளிப்புற டூலின் (External Tool) செயல்பாடுகளையும், என்ன இன்புட் கொடுத்து என்ன ரிசல்ட் எடுத்தது என்பதையும் பதிவு செய்யும் இடம்.
- **வணிக மதிப்பு (Business Value):** AI ஏஜென்ட் தவறான டேட்டாபேஸ் கமாண்ட் இயக்கிவிட்டதா அல்லது ஹேக் ஆகிவிட்டதா என்பதை கண்காணிக்கலாம்.

### 💻 Tech Perspective (பொறியாளர்களுக்கான தொழில்நுட்ப விளக்கம்)
- **Backend Architecture:** Implemented in 'core/mcp/exec.go'. Instruments tool execution lifecycles across stdio subprocesses and HTTP SSE transports. Captures calling agent identity, target MCP server, tool function name, parsed input JSON arguments, execution duration in milliseconds, output JSON return schema, and any stderr/exception traces.
- **Backend Endpoints:**
  * `GET /api/v1/mcp-logs`
  * `GET /api/v1/mcp-logs/:id`


### 🖥️ Screen Layout & Bottom Elements (திரை கூறுகள் & பட்டன்கள்)
**1. மேல்புற கட்டுப்பாடுகள் (Top Bar Controls):**
- Tool Name Filter Dropdown: Filter by specific tool (e.g. 'execute_sql_query', 'read_file').
- Server Label Dropdown: Filter by MCP server (e.g. 'github', 'postgres', 'slack').
- Time Window Selector: Filter tool invocations by time.
- Export Button: Export tool audit logs.

**2. மத்திய திரைக் கூறுகள் & வரைபடங்கள் (Tabs & Views):**
- MCP Logs Table: Columns for Timestamp, Tool Name (Badge), Server Name, Status (Success/Failed), Duration (ms), Virtual Key, User Session ID.

**3. கீழ்புற கூறுகள், படிவங்கள் & ஸ்லைடு-ஓவர் ஷீட்டுகள் (Bottom Elements & Sheets):**
- ToolExecutionDetailSheet (Slide-over): Detailed inspector with: (1) Arguments Tab (JSON inputs sent to the tool), (2) Results Tab (JSON response returned by tool), (3) Error Stack Trace Tab.


### 🔗 Connection & Structure Map (இணைப்புகள் & செயல்பாடுகள்)
- **தரவை எங்கிருந்து பெறுகிறது (Receives Data From):** Triggered by MCP Gateway execution whenever an LLM initiates a Tool Calling loop.
- **எதனை இயக்குகிறது / பாதிக்கிறது (Triggers & Affects):** Tied to Tool Groups and Auth Sessions. If a tool fails repeatedly, updates Circuit Breaker and Alert Channels.

### 💡 Real-World Enterprise Use Case (நடைமுறை பயன்பாட்டு உதாரணம்)
ஒரு AI கோடிங் ஏஜென்ட் GitHub Repositories-ல் தேவையில்லாத கோப்பை நீக்கிவிட்டதா என்பதை MCP Logs-ல் சென்று 'delete_file' டூலின் இன்புட் ஆர்குமெண்ட்டை எடுத்து ஆராய்கிறார்கள்.

---

<a name='browser_ai'></a>
## Browser AI (பிரவுசர் பாதுகாப்பு & DLP ப்ராக்ஸி)
**UI Route:** `/workspace/browser-ai`

### 👤 Non-Tech Perspective (சாதாரண மனிதர்களுக்கான எளிய விளக்கம்)
- **உருவகம் (Analogy):** அலுவலக வாயிலில் இருக்கும் செக்யூரிட்டி கார்டு (Security Checkpost at the Gate).
- **விளக்கம் (Explanation):** ஊழியர்கள் தங்கள் அலுவலக லேப்டாப்பில் பொது இணையதளங்களான ChatGPT, Claude, Perplexity போன்றவற்றைப் பயன்படுத்தும்போது, நிறுவனத்தின் ரகசிய சோர்ஸ் கோட், பாஸ்வேர்டுகள், வாடிக்கையாளர் விபரங்கள் ஆகியவற்றை காப்பி-பேஸ்ட் செய்துவிடாமல் நடுவில் நின்று தடுத்து நிறுத்தும் டிஜிட்டல் செக்யூரிட்டி கார்டு.
- **வணிக மதிப்பு (Business Value):** நிறுவனத்தின் மிகப்பெரிய பாதுகாப்பு அச்சுறுத்தலான 'Employee Data Leakage'-ஐ 100% தடுத்து நிறுத்துகிறது.

### 💻 Tech Perspective (பொறியாளர்களுக்கான தொழில்நுட்ப விளக்கம்)
- **Backend Architecture:** A hybrid two-layer architecture: (1) A lightweight Python proxy daemon ('apps/browser-guard/proxy/browser_ai_proxy.py') with Chrome/Edge extensions deployed via corporate MDM, and (2) a central management UI in UnifAI. Intercepts HTTPS paste events on designated AI domains, evaluates Presidio DLP regexes, runs local Ollama classification models, extracts text from uploaded attachments (PDF, DOCX), and enforces block/mask actions.
- **Backend Endpoints:**
  * `GET /api/v1/browser-ai/logs`
  * `POST /api/v1/browser-ai/rules`
  * `POST /api/v1/browser-ai/targets`


### 🖥️ Screen Layout & Bottom Elements (திரை கூறுகள் & பட்டன்கள்)
**1. மேல்புற கட்டுப்பாடுகள் (Top Bar Controls):**
- 5 Main Tabs: Logs Tab, Rules Tab, Target Websites Tab, Agents Tab, Settings Tab.
- Agent Heartbeat Status Bar: Shows active, online, and disconnected employee machines.

**2. மத்திய திரைக் கூறுகள் & வரைபடங்கள் (Tabs & Views):**
- Rules Tab: List of DLP policies with toggle switches (Enabled/Disabled).
- Target Websites Tab: Directory of monitored AI websites (chatgpt.com, claude.ai) with host roles (Allow/Block).
- Agents Tab: Table of employee laptops (Hostname, IP, OS, Agent Version, Last Heartbeat).
- Logs Tab: Intercepted queries showing employee ID, target domain, matched rule, and blocked text preview.

**3. கீழ்புற கூறுகள், படிவங்கள் & ஸ்லைடு-ஓவர் ஷீட்டுகள் (Bottom Elements & Sheets):**
- + Create Rule Button: Modal with Policy-to-Regex AI generator (converts English descriptions to Regex).
- + Add Target Website Dialog: Add new AI websites to monitor with attachment scanning toggle.
- Save Uninstall Key Button: Sets tamper-proof password required to remove the agent from laptops.
- Bulk Delete Agents Button: Clean up decommissioned employee machines.


### 🔗 Connection & Structure Map (இணைப்புகள் & செயல்பாடுகள்)
- **தரவை எங்கிருந்து பெறுகிறது (Receives Data From):** Receives real-time intercepted traffic from employee laptop daemons via WebSocket/HTTP.
- **எதனை இயக்குகிறது / பாதிக்கிறது (Triggers & Affects):** Shares Guardrail Providers (Presidio); writes violations directly into Audit Logs and Alert Channels.

### 💡 Real-World Enterprise Use Case (நடைமுறை பயன்பாட்டு உதாரணம்)
ஒரு ஜூனியர் டெவலப்பர் தனது நிறுவனத்தின் AWS Secret Key-ஐ ChatGPT-ல் பேஸ்ட் செய்ய முயலும்போது, Browser AI அதை உடனடியாக தடுத்து நிறுத்தி, 'Corporate Policy Violation' எச்சரிக்கையை திரையில் காட்டுகிறது.

---

<a name='connectors'></a>
## Connectors (வெளிப்புற கண்காணிப்பு இணைப்பு குழாய்கள்)
**UI Route:** `/workspace/observability`

### 👤 Non-Tech Perspective (சாதாரண மனிதர்களுக்கான எளிய விளக்கம்)
- **உருவகம் (Analogy):** தொழிற்சாலையிலிருந்து கழிவுநீர் அல்லது பொருட்களை பெரிய குழாய் மூலம் நகராட்சி டேங்கிற்கு அனுப்புவது போன்ற எக்ஸ்போர்ட் பைப்லைன் (Export Pipeline).
- **விளக்கம் (Explanation):** UnifAI-க்குள் மட்டுமே தகவல்களை வைத்திருக்காமல், நிறுவனத்தின் கார்ப்பரேட் கண்காணிப்பு தளங்களான Datadog, New Relic, Google BigQuery, அல்லது Kafka-வுக்கு இந்த AI லாக் தகவல்களை நிகழ்நேரத்தில் தானாகவே பம்ப் செய்து அனுப்பும் இணைப்பு குழாய்கள்.
- **வணிக மதிப்பு (Business Value):** நிறுவனத்தின் அனைத்து மென்பொருள் மற்றும் AI செலவுகளை ஒரே பெரிய எண்டர்பிரைஸ் டேஷ்போர்டில் ஒருங்கிணைக்கலாம்.

### 💻 Tech Perspective (பொறியாளர்களுக்கான தொழில்நுட்ப விளக்கம்)
- **Backend Architecture:** Implemented in 'framework/connectors/runtime.go'. Employs a decoupled ring-buffer worker pipeline. Separates telemetry export from the critical path of the gateway to maintain zero-latency proxying. Formats internal telemetry into vendor-specific schemas and streams them asynchronously with configurable batch sizes, flush intervals (ms), retry logic, and exponential jitter backoff.
- **Backend Endpoints:**
  * `GET /api/v1/connectors`
  * `POST /api/v1/connectors`
  * `POST /api/v1/connectors/:id/test`


### 🖥️ Screen Layout & Bottom Elements (திரை கூறுகள் & பட்டன்கள்)
**1. மேல்புற கட்டுப்பாடுகள் (Top Bar Controls):**
- + Add Connector Button: Opens creation sheet for external platforms.
- Active Connectors Status Badges: Displays health indicators (Green = Streaming, Red = Unreachable).

**2. மத்திய திரைக் கூறுகள் & வரைபடங்கள் (Tabs & Views):**
- Connector Cards Grid: Datadog, New Relic, Apache Kafka, Google BigQuery, Google PubSub, OpenTelemetry (OTel).

**3. கீழ்புற கூறுகள், படிவங்கள் & ஸ்லைடு-ஓவர் ஷீட்டுகள் (Bottom Elements & Sheets):**
- ConnectorConfigSheet (Slide-over): Form inputs for API Key, Endpoint URL, Buffer Size Slider, Flush Interval (ms), Header Whitelist.
- Test Connection Button: Dispatches a synthetic ping payload to verify credentials and connectivity before saving.


### 🔗 Connection & Structure Map (இணைப்புகள் & செயல்பாடுகள்)
- **தரவை எங்கிருந்து பெறுகிறது (Receives Data From):** Drains event records continuously from LLM Logs, MCP Logs, and Audit Logs.
- **எதனை இயக்குகிறது / பாதிக்கிறது (Triggers & Affects):** Pushes live AI telemetry to external corporate data lakes and SIEM systems.

### 💡 Real-World Enterprise Use Case (நடைமுறை பயன்பாட்டு உதாரணம்)
ஒரு வங்கியின் பில்லிங் சாப்ட்வேர், Google BigQuery-ல் UnifAI Connectors வழியாக வரும் வாடிக்கையாளர் டோக்கன் டேட்டாவை வைத்து தானாகவே மாதாந்திர இன்வாய்ஸ் தயாரிக்கிறது.

---

<a name='logs_settings'></a>
## Logs Settings (பதிவேடு அமைப்புகள் & கொள்கைகள்)
**UI Route:** `/workspace/config/logging`

### 👤 Non-Tech Perspective (சாதாரண மனிதர்களுக்கான எளிய விளக்கம்)
- **உருவகம் (Analogy):** ஆவணங்களை பாதுகாக்கும் காப்பகம் மற்றும் ஆவண அழிப்பு கொள்கை (Document Retention & Shredding Policy).
- **விளக்கம் (Explanation):** பழைய லாக் விபரங்களை எத்தனை நாட்கள் வைத்திருக்க வேண்டும்? எப்போது தானாக அழிக்க வேண்டும்? மிகவும் ரகசியமான மருத்துவ/வங்கி உரையாடல்களை லாக் செய்யாமல் மறைக்க வேண்டுமா? பழைய டேட்டாவை மலிவான கிளவுட் ஸ்டோரேஜிற்கு (AWS S3) மாற்ற வேண்டுமா? என்பதை தீர்மானிக்கும் கொள்கை அறை.
- **வணிக மதிப்பு (Business Value):** சர்வர் ஸ்டோரேஜ் செலவு மிச்சமாகும்; அரசாங்கத்தின் GDPR / HIPAA சட்ட விதிகளுக்கு இணங்கலாம்.

### 💻 Tech Perspective (பொறியாளர்களுக்கான தொழில்நுட்ப விளக்கம்)
- **Backend Architecture:** Located in 'ui/app/workspace/config/views/loggingView.tsx' and backend garbage collection scheduler. Controls internal database vacuuming routines, FastHTTP request context logging filters, and AWS S3 / Google Cloud Storage multi-part blob upload routines for cold archive tiering.
- **Backend Endpoints:**
  * `GET /api/v1/config/logging`
  * `PUT /api/v1/config/logging`


### 🖥️ Screen Layout & Bottom Elements (திரை கூறுகள் & பட்டன்கள்)
**1. மேல்புற கட்டுப்பாடுகள் (Top Bar Controls):**
- Page Header with Save Configuration Button and Reset to Defaults Option.

**2. மத்திய திரைக் கூறுகள் & வரைபடங்கள் (Tabs & Views):**
- Retention Schedule Slider: Dropdown setting log lifespan (7, 14, 30, 90, 365 days).
- Traffic Sampling Rate Slider: 1% to 100% sampling controls for ultra-high traffic environments.
- Privacy Switches: (1) Disable Content Logging (omits prompts/responses), (2) Store Raw Bytes, (3) Auto PII Redaction in logs.
- External Storage Configuration: AWS S3 / GCS bucket name, region, access key, and secret key inputs.

**3. கீழ்புற கூறுகள், படிவங்கள் & ஸ்லைடு-ஓவர் ஷீட்டுகள் (Bottom Elements & Sheets):**
- Purge Logs Now Button: Administrative action to instantly delete logs matching selected criteria.
- Save Logs Configuration Button: Applies changes instantly across all cluster nodes.


### 🔗 Connection & Structure Map (இணைப்புகள் & செயல்பாடுகள்)
- **தரவை எங்கிருந்து பெறுகிறது (Receives Data From):** Admin configurations from the UI.
- **எதனை இயக்குகிறது / பாதிக்கிறது (Triggers & Affects):** Governs the storage lifecycle, privacy masking, and deletion behavior of LLM Logs and MCP Logs.

### 💡 Real-World Enterprise Use Case (நடைமுறை பயன்பாட்டு உதாரணம்)
ஒரு மருத்துவமனை 'HIPAA Compliance' விதிப்படி, நோயாளிகளின் உரையாடல்களை 30 நாட்களில் ஆட்டோ-டெலீட் செய்ய Retention-ஐ 30 நாட்களாக அமைத்து, Content Logging-ஐ ஆஃப் செய்கிறது.

---

# 3. Cross-Feature Interconnections & Data Flow
### அம்சங்களுக்கிடையேயான நேரடித் தொடர்பு வரைபடம்

| மூல கூறு (Source) | இணைக்கப்பட்டுள்ள கூறு (Connected To) | தரவு பரிமாற்றம் & செயல்பாடு (Data Flow & Action) |
| :--- | :--- | :--- |
| **LLM Logs** | **Dashboard** | ஒவ்வொரு லாக் வரியிலிருந்தும் Token count, Latency மற்றும் Cost கணக்கிடப்பட்டு Dashboard வரைபடங்கள் புதுப்பிக்கப்படுகின்றன. |
| **LLM Logs** | **Connectors** | லாக் பதிவுகள் Asynchronous Ring Buffer வழியாக Datadog, Kafka, மற்றும் BigQuery-க்கு நேரலையாக ஸ்ட்ரீம் செய்யப்படுகின்றன. |
| **MCP Logs** | **MCP Gateway** | AI ஏஜென்ட் இயக்கிய டூல்களின் JSON இன்புட் மற்றும் அவுட்புட் பரிவர்த்தனைகள் MCP Logs-ல் சேமிக்கப்படுகின்றன. |
| **Browser AI** | **LLM Logs / Audit Logs** | ஊழியர்கள் ChatGPT தளத்தில் ரகசிய டேட்டாவை பேஸ்ட் செய்யும்போது Browser AI தடுத்து நிறுத்தி, அந்த விதிமீறலை Logs-ல் பதிகிறது. |
| **Logs Settings** | **LLM & MCP Logs** | பதிவுகள் எத்தனை நாட்கள் சேமிப்பில் இருக்க வேண்டும் (Retention) மற்றும் PII மறைப்பு விதிகளையும் Logs Settings நிர்வகிக்கிறது. |
| **Dashboard** | **Alert Channels** | செலவு அல்லது எரர் விகிதம் அதிகமாகும்போது Dashboard அமைப்புகள் மூலமாக Slack/PagerDuty-க்கு அலர்ட் செல்கிறது. |

# 4. Tech vs Non-Tech Comparative Matrix
### தொழில்நுட்ப & வணிக பார்வை ஒப்பீடு (Comparative Matrix)

| Observability அம்சம் | வணிகப் பார்வை (CFO / Manager Perspective) | தொழில்நுட்பப் பார்வை (DevOps / Architect Perspective) |
| :--- | :--- | :--- |
| **Dashboard** | 'இந்த வாரம் AI-க்கு எவ்வளவு செலவாகியுள்ளது? பட்ஜெட் மிச்சமிருக்கிறதா?' | 'p95 லேடன்சி எவ்வளவு? FastHTTP மெட்ரிக்ஸ் மற்றும் WebSocket இணைப்புகள் சீராக உள்ளதா?' |
| **LLM Logs** | 'வாடிக்கையாளர் என்ன கேள்வி கேட்டார்? மாடல் சரியான பதில் தந்ததா?' | 'HTTP Status Code என்ன? TTFT மில்லி விநாடிகள் மற்றும் PostgreSQL இன்செர்ஷன் வேகம் எவ்வளவு?' |
| **MCP Logs** | 'AI ஏஜென்ட் நம் கம்பெனி டூல்களை சரியாகப் பயன்படுத்துகிறதா?' | 'stdio/SSE transport வழியாக டூல் இயங்கிய latency மற்றும் JSON Schema validation நிலைகள் என்ன?' |
| **Browser AI** | 'நிறுவன ரகசியங்களை ஊழியர்கள் ChatGPT-ல் லீக் செய்யாமல் தடுக்க முடிகிறதா?' | 'mitmproxy daemon இயங்குகிறதா? Presidio DLP regexes மற்றும் Ollama மாடல் கிளாசிபிகேஷன் துல்லியமா?' |
| **Connectors** | 'எங்கள் கார்ப்பரேட் பில்லிங் சிஸ்டத்தில் AI செலவு தானாக ஏறி விடுகிறதா?' | 'Kafka topics-க்கு batch size மற்றும் flush interval (ms) முறையில் டேட்டா இழப்பின்றி செல்கிறதா?' |
| **Logs Settings** | 'சட்ட விதிகளுக்கு ஏற்ப பழைய உரையாடல்கள் தானாக அழிகிறதா (GDPR Compliance)?' | 'Postgres vacuumingGC அட்டவணை மற்றும் S3 cold storage multi-part upload சரியாக நடக்கிறதா?' |
