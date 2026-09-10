# UnifAI Status Report, Feature Map & Roadmap

**Project:** UnifAI (`unify - Copy`)  
**Remote:** `https://github.com/THIRUPUGAL-2003/unifai_new.git`  
**Branch:** `main`  
**Document date:** 10 Sep 2026  
**Audience:** Team handoff (Thiru offline until ~15:00 IST)  
**Deploy refs:** `https://unifai.dev-yp.com` / `https://unifaiv2.dev-yp.com`

---

## 0. Handoff note

- Thiru is **off development until 3:00 PM IST**.
- This document is the handoff pack: **what exists, what was changed, what is broken, what is next**.
- A phone call cannot be placed by the coding agent. Use this doc + chat for sync.

---

## 1. How to read this document

| Symbol | Meaning |
|--------|---------|
| **Enabled** | Feature UI/config turned on in your environment |
| **Working** | Code path exists and basic health/wiring looks OK |
| **Needs test** | Enabled, but live QA still required |
| **Known error** | Confirmed issue / partial behaviour |
| **Not done** | Explicitly pending |

---

## 2. Changes vs base (this repo)

### 2.1 Base

- Product base: UnifAI / Bifrost-style gateway + UI.
- This copy tracks `origin/main` on `unifai_new`.
- Recent theme of commits: **MCP catalog/sync**, **Browser Guard**, **cmd / deploy**, **model UI fixes**.

### 2.2 Uncommitted changes (as of this document)

These files are modified locally and **not yet committed**:

| File | Change |
|------|--------|
| `core/mcp/credstore/shared_headers.go` | Do not send empty `Authorization` header (avoids confusing upstream 401) |
| `core/mcp/utils/utils.go` | Skip empty static header values on the wire |
| `transports/unifai-http/handlers/mcp.go` | Reject `auth_type=headers` create without any header value (clear 400) |
| `ui/.../mcpClientForm.tsx` | UI validation: Headers auth requires ≥1 filled header |

### 2.3 Major work completed in this stream (summary)

| Area | What was done |
|------|----------------|
| **MCP Library** | Rebuilt curated catalog (~122 servers with logos); sync default → `file:///app/configs/mcp-library.json` (getunifai.ai DNS is dead) |
| **MCP sync logic** | Removed silent bad fallback behaviour; prune guard; resurrect soft-deleted remotes on sync; sanitize dead catalog URLs |
| **MCP settings UI** | Allow `file://` catalog URL; placeholder fixed; RBAC aligned |
| **MCP Headers connect** | Empty-header / validation hardening (see 2.2) |
| **Auth / email (earlier)** | Registration accept/reject mail; login notice for new device; lockout/reset/email uniqueness rules |
| **MySQL support (earlier)** | Driver paths + `DB_TYPE` override (live env still Postgres) |
| **Browser Guard** | Windows installer / agent updates (v1.5.x–1.6.x line in git history) |
| **Model catalog** | Description/attributes error fixes claimed by team — **still needs re-check** |

### 2.4 What “base vs your fork” means practically

You did **not** only toggle UI switches. You:

1. **Enabled** many enterprise-style modules (Observability connectors, Governance, Guardrails, Routing, MCP sub-features).
2. **Repaired / rebuilt** MCP catalog after DB wipe / wrong sync source.
3. **Hardened** Headers auth so empty keys fail clearly.
4. **Operate** Browser AI Guard on Windows laptops; Mac + Chrome-all-sites still pending.

---

## 3. Feature map (inside → what it does → status)

### 3.1 Browser AI / UnifAI Guard (laptop)

| Inside | Purpose | Status |
|--------|---------|--------|
| Target websites | Sites Guard watches | **Enabled** — some sites work, some don’t |
| Prompt interception | Capture submitted prompts | **Working** (incl. short text/numbers in Guard v1.5.7+) |
| Prompt logs | Audit prompts | **Needs test** |
| Guard Bot | Bot / policy actions | **Needs test** |
| Regex rules | Pattern block/allow | **Working for all sites (claimed)** |
| LLM classification | Smarter allow/block | **Known gap — LLM not working; regex only** |
| Windows installer | Employee install | **Added / OK** |
| Mac agent | Same on macOS | **Not done** |
| Chrome “all websites” | Global intercept | **Not done** (partial site list only) |

**Use:** Employee browser traffic → UnifAI policy → log / block / allow.

---

### 3.2 Observability connectors

You enabled: **Maxim, Datadog, BigQuery, Kafka, Pub/Sub, New Relic** (+ OTEL / Prometheus in UI).

| Connector | Connects to | Use | Status |
|-----------|-------------|-----|--------|
| Maxim | Maxim AI observability | Trace/tags export | **Enabled — needs live connect test** |
| Datadog | Datadog | Metrics/logs/APM style export | **Enabled — needs live connect test** |
| BigQuery | GCP BigQuery | Analytics warehouse export | **Enabled — needs live connect test** |
| Kafka | Kafka cluster | Event stream export | **Enabled — needs live connect test** |
| Pub/Sub | Google Pub/Sub | Event publish | **Enabled — needs live connect test** |
| New Relic | New Relic | APM/telemetry | **Enabled — needs live connect test** |
| OpenTelemetry | OTLP collector | Traces (Headers = collector auth) | **UI present — verify config** |
| Prometheus | Prometheus / telemetry plugin | Metrics scrape | **UI present — verify config** |

**Note:** “Enabled” ≠ proven healthy export. Each needs destination credentials + one successful export sample.

---

### 3.3 Models / Providers / Pricing

| Feature | Use | Status |
|---------|-----|--------|
| Circuit Breaker | Fail over when provider/header signal trips | **Added — needs test** |
| Pricing Overrides | Custom model pricing | **Added — needs test** |
| Model Settings | Sync URLs, intervals, routing depth, etc. | **Added — needs test** |
| Model providers (60+) | Upstream LLM vendors | **Added — needs smoke test per critical vendors** |
| Model catalog description / attributes | Catalog metadata display | **Fixed earlier — re-check still required** |

---

### 3.4 MCP Gateway

| Sub-feature | Use | Status |
|-------------|-----|--------|
| MCP Catalog / Library | Browse/install MCP servers (~122 + logos) | **Recovered & seeded — needs install/OAuth test** |
| Tool Groups | Group tools for access control | **Enabled — needs test** |
| Auth Sessions | Per-user OAuth/Headers sessions | **Enabled — needs test** |
| OAuth Grants | OAuth grant management | **Enabled — needs test** |
| MCP Settings | Catalog URL / sync | **Fixed (`file://` default) — Force Sync after deploy** |
| Headers auth path | API-key MCP connect | **Hardened (empty key blocked)** |
| OAuth install path | Vendor login MCP connect | **Expected** — some servers fail without OAuth; some vendor/timeout errors remain |

**Known MCP issues (current):**

- Some installs → **timeout / connect error**
- Some servers → **auth/OAuth incomplete**
- Some servers → **vendor endpoint strict / unavailable**
- Catalog is **not** getunifai remote anymore (domain NXDOMAIN); local JSON is source of truth

---

### 3.5 Guardrails

| Inside | Use | Status |
|--------|-----|--------|
| Rules | Content/policy rules | **Enabled + connected — needs regression test** |
| Providers | Guardrail provider backends | **Enabled + connected — needs regression test** |

---

### 3.6 Governance

| Feature | Status |
|---------|--------|
| Virtual Keys | **Working focus area — keep testing** |
| Users | **Working focus area — keep testing** |
| Teams | **Enabled — was erroring; re-test all flows** |
| Business Units | **Enabled — was erroring; re-test** |
| Customers | **Enabled — was erroring; re-test** |
| User Provisioning | **Enabled — was erroring; re-test** |
| Roles & Permissions | **Enabled — was erroring; re-test** |
| Access Profiles | **Enabled — was erroring; re-test** |
| Audit Logs | **Enabled — was erroring; re-test** |

---

### 3.7 Adaptive Routing / Dashboard / Settings (routing)

| Feature | Status |
|---------|--------|
| Adaptive Routing | **Fully enabled/configured — needs end-to-end request test** |
| Dashboard | **Enabled — needs metric sanity check** |
| Routing Settings | **Enabled — needs test** |

---

### 3.8 Prompt Repository & Skills Repository

| Feature | Use | Status |
|---------|-----|--------|
| Prompt Repository | Prompt templates / playground | **Present — needs test** |
| Skills Repository | Skills metadata/packages | **Present — needs test** |

---

### 3.9 Settings

| Section | Notes | Status |
|---------|-------|--------|
| Client Settings | Header forwarding, client behaviour | **Needs test** |
| Compatibility | Compat layer | **Needs test** |
| Caching | Cache behaviour | **Needs test** |
| Security | CORS / required headers | **Needs test** |
| API Keys | Platform keys | **Needs test** |
| Performance Tuning | Limits / tuning | **Needs test** |
| Feature Flags | Feature toggles | **Needs test** |
| Vector DB | Error removed (per your note) | **Removed/cleaned — confirm UI no longer errors** |

---

### 3.10 Auth / Login / Email / Guard on laptop

| Item | Status |
|------|--------|
| Full login flows | **Implemented — needs full QA** |
| Create account | **Implemented** |
| Accept / Reject registration + email | **Implemented earlier** |
| Mail options | **Enabled — verify SMTP in env** |
| Laptop Guard installed | **Done on Windows path** |

---

## 4. Headers cheat-sheet (where they connect)

| UI Headers | Connects to | Affects “Connected”? |
|------------|-------------|----------------------|
| MCP Headers | Upstream MCP server | **Yes** |
| MCP Per-user Headers | Upstream MCP (per user) | **Yes (tools)** |
| MCP Gateway auth mode Headers | Client → UnifAI `/mcp` | **Yes (gateway)** |
| Provider Extra Headers | LLM provider | No badge; call success/fail |
| Provider Beta Headers | Anthropic betas | No |
| OTEL Headers | Trace collector | No |
| Security / Logging / Routing Headers | Policy / logs / routing | No |

---

## 5. Known errors / gaps (priority)

### P0 — user-visible broken / incomplete

1. **Browser AI LLM path not working** — only regex works across sites.  
2. **Chrome all-websites coverage not done.**  
3. **Mac Guard not developed yet.**  
4. **MCP:** intermittent server/timeout/auth failures on install/connect.  
5. **Governance modules** (Teams → Audit Logs except VK/Users): historically errored — full working-condition pass required.

### P1 — enabled but not proven

6. Observability connectors (Maxim, Datadog, BigQuery, Kafka, Pub/Sub, New Relic) — enabled, need live export proof.  
7. Circuit Breaker / Pricing Overrides / Model Settings / 60+ providers — smoke tests.  
8. Adaptive Routing / Dashboard — request path proof.  
9. Model catalog description/attributes — re-verify after prior fix.  
10. MCP Tool Groups / Auth Sessions / OAuth Grants / MCP Settings — functional QA.

### P2 — polish / ops

11. Commit + deploy uncommitted Headers hardening.  
12. Document SMTP + OAuth callback URLs per environment.  
13. PDF/DOC distribution to stakeholders.

---

## 6. Roadmap

### Done / largely done

- [x] Core UnifAI gateway + UI  
- [x] Browser Guard Windows packaging  
- [x] Observability connector UIs enabled  
- [x] Models: Circuit Breaker, Pricing Overrides, Model Settings, many providers  
- [x] MCP Library recovery (~122 + logos) + sync URL fix  
- [x] MCP Headers empty-key hardening  
- [x] Guardrails Rules + Providers enabled  
- [x] Governance modules enabled (VK/Users trusted more than others)  
- [x] Adaptive Routing / Dashboard enabled  
- [x] Login + registration decision emails + laptop Guard  
- [x] Vector DB settings error cleanup (per team)

### Next (recommended order)

1. **Deploy** latest code (incl. uncommitted Headers fixes) to `unifai.dev-yp.com`.  
2. **MCP QA matrix** — 10 priority servers (OAuth + Headers samples); log failures by cause.  
3. **Governance QA** — Teams, Business Units, Customers, Provisioning, Roles, Access Profiles, Audit Logs.  
4. **Observability proof** — one successful event per connector.  
5. **Browser AI** — fix LLM classification path; expand site list; design Chrome all-sites.  
6. **Mac Guard** — port agent/installer.  
7. **Models smoke** — top 10 providers + Circuit Breaker trip test.  
8. **Adaptive Routing e2e** — one rule path with metrics on Dashboard.

### Later

- Full Chrome extension / system-wide intercept  
- Hardening CI for MCP catalog sync  
- Optional remote catalog host replacement for dead getunifai.ai  

---

## 7. Test checklist (copy/paste)

### Browser AI
- [ ] Regex blocks on Site A / Site B  
- [ ] LLM path returns decision (currently failing)  
- [ ] Prompt log appears in UI  
- [ ] Windows Guard install on clean PC  

### Observability
- [ ] Maxim receives a trace  
- [ ] Datadog receives payload  
- [ ] BigQuery row inserted  
- [ ] Kafka message published  
- [ ] Pub/Sub message published  
- [ ] New Relic event visible  

### Models
- [ ] Circuit Breaker failover fires  
- [ ] Pricing override applied on cost  
- [ ] Model Settings save persists  
- [ ] Catalog description/attributes render without error  
- [ ] Sample chat via 3–5 critical providers  

### MCP
- [ ] Library shows ~122 + logos  
- [ ] Force Sync succeeds from `file:///app/configs/mcp-library.json`  
- [ ] OAuth install completes for GitHub/Notion (or org standards)  
- [ ] Headers install with real API key connects  
- [ ] Tool Groups / Sessions / Grants / Settings pages load without error  

### Guardrails / Governance / Routing
- [ ] Guardrail rule blocks bad content  
- [ ] VK create/use  
- [ ] User create/login  
- [ ] Team / BU / Customer / Roles / Access Profile / Audit Log CRUD  
- [ ] Adaptive route selects expected model  

### Settings / Auth
- [ ] Security required headers enforce 400  
- [ ] Caching toggle behaviour  
- [ ] Feature flags toggle  
- [ ] Register → admin accept/reject email  
- [ ] Login mail on new device only  

---

## 8. Environments

| Env | URL | Notes |
|-----|-----|-------|
| New / primary | `https://unifai.dev-yp.com` | Health OK when last probed |
| Legacy / YES PANCHI line | `https://unifaiv2.dev-yp.com` | Health OK when last probed |
| DB | Postgres (`Unifai_test` via `.env`) | MCP library live count was 122 after reseed |

---

## 9. Modify vs new vs enabled (plain language)

| Type | Examples |
|------|----------|
| **New / rebuilt by you** | MCP catalog file + logos seeding; Headers empty-value guards; Guard Windows releases; many connectors enabled in ops |
| **Modified** | MCP sync defaults/settings; auth emails; model catalog metadata fixes; vector DB settings cleanup |
| **Enabled (product already had code)** | Maxim/Datadog/BigQuery/Kafka/PubSub/New Relic; Circuit Breaker; Pricing Overrides; Governance suite; Adaptive Routing; Guardrails; MCP Tool Groups/Sessions/Grants |
| **Still missing** | Browser AI LLM path; Chrome all sites; Mac Guard; full connector/MCP/governance proof tests |

---

## 10. Immediate actions after 15:00

1. Deploy / restart with latest Headers fixes.  
2. Run **Section 7** checklist; mark pass/fail with screenshots.  
3. Open one MCP fail + one Governance fail as tickets with exact error text.  
4. Prioritize Browser AI LLM fix if Guard is customer-facing this week.

---

*Generated for UnifAI team handoff. Update this file when checklist items flip to Pass.*
