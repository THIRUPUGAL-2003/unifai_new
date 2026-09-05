# UnifAI Model Providers & MCP Server Complete Technical Guide
**Platform Architecture, Complete Provider Directory, Logo Engineering & MCP Server Integration**
*Generated from active codebase | UnifAI Platform v2.0 | 93 Model Providers | 178 MCP Servers*

---

## 1. Overview & Thanglish Summary (Mukiya Vilakkam)

Indha document-la UnifAI platform kulla irukura **Model Providers** pathiyum, **MCP (Model Context Protocol) Servers** pathiyum complete full details irukku.
- **Model Providers**: UnifAI codebase-la total-ah **93 built-in model providers** support panni irukom. OpenAI, Anthropic, AWS Bedrock, Google Vertex AI, Azure la irundhu Sarvam AI, DeepSeek, Cerebras, Ollama, vLLM varaikum ellame integrated. Ithu koodave endha custom OpenAI/Anthropic-compatible server-ayum **Add Custom Provider** moolama add pannalam.
- **Logo & Icons**: Providers logos epadi handle aagudhu na, `ui/lib/constants/icons.tsx` kulla theme-aware SVG vector components vachu render panrom. User dark mode or light mode switch pannum bodhu Anthropic, OpenAI, etc. logos automatic-ah black/white color change aagum. Branded logos (Cerebras orange, DeepSeek blue) avanga brand colors-la crisp vector-ah render aagum. Azure mari konjam providers `/images/azure.webp` static file use panrom.
- **MCP Gateway**: UnifAI kulla built-in-ah **178 MCP servers** library irukku (`configs/mcp-library.json`). Developer Tools (GitHub, GitLab, Supabase), Search (Brave, Tavily), Productivity (Notion, Slack), etc. Ellame `stdio` (local process execution) or `http`/`sse` (remote HTTP streaming) transports moolama run aagum.
- **Step-by-Step MCP Adding**: MCP Library-la irundhu epadi 1-click install panrathu, or custom MCP server epadi form fill panni add panrathu, apram real GitHub Copilot MCP & PostgreSQL database MCP examples vachu full flow explain panni irukom.

---

## 2. All 93 Model Providers Directory (Complete List)

UnifAI `ui/lib/constants/logs.ts` and `framework/` codebase-la support panra full 93 providers list:

| # | Provider ID | Display Label / Name | Icon / Logo Type | Embedding Support | Primary Focus / Notes |
|---|-------------|----------------------|------------------|-------------------|-----------------------|
| 1 | `ai21` | **AI21 Labs** | Branded Vector SVG (Custom Color Fill) | No | Cloud Inference & Specialized Gateway |
| 2 | `bedrock` | **AWS Bedrock** | Branded Vector SVG (Custom Color Fill) | Yes | Tier-1 Frontier Multi-Modal LLM Provider |
| 3 | `bedrock_mantle` | **AWS Bedrock Mantle** | Branded Vector SVG (Custom Color Fill) | No | Tier-1 Frontier Multi-Modal LLM Provider |
| 4 | `aionlabs` | **AionLabs** | Branded Vector SVG (Custom Color Fill) | No | Cloud Inference & Specialized Gateway |
| 5 | `dashscope` | **Alibaba DashScope** | Branded Vector SVG (Custom Color Fill) | No | Leading Global Foundation & Reasoning Models |
| 6 | `anthropic` | **Anthropic** | Theme-Aware Vector SVG (Dynamic Light/Dark) | No | Tier-1 Frontier Multi-Modal LLM Provider |
| 7 | `anyscale` | **Anyscale** | Branded Vector SVG (Custom Color Fill) | No | Cloud Inference & Specialized Gateway |
| 8 | `arcee` | **Arcee AI** | Branded Vector SVG (Custom Color Fill) | No | Cloud Inference & Specialized Gateway |
| 9 | `azure` | **Azure** | Static Image (/images/azure.webp) | Yes | Tier-1 Frontier Multi-Modal LLM Provider |
| 10 | `baichuan` | **Baichuan** | Branded Vector SVG (Custom Color Fill) | No | Cloud Inference & Specialized Gateway |
| 11 | `qianfan` | **Baidu Qianfan** | Branded Vector SVG (Custom Color Fill) | No | Cloud Inference & Specialized Gateway |
| 12 | `baseten` | **Baseten** | Branded Vector SVG (Custom Color Fill) | No | Cloud Inference & Specialized Gateway |
| 13 | `cerebras` | **Cerebras** | Theme-Aware Vector SVG (Dynamic Light/Dark) | No | Ultra-Fast Hardware LPU / Silicon Inference |
| 14 | `cerebrium` | **Cerebrium** | Branded Vector SVG (Custom Color Fill) | No | Cloud Inference & Specialized Gateway |
| 15 | `cohere` | **Cohere** | Branded Vector SVG (Custom Color Fill) | Yes | Leading Global Foundation & Reasoning Models |
| 16 | `dashscopecn` | **DashScope China** | Branded Vector SVG (Custom Color Fill) | No | Leading Global Foundation & Reasoning Models |
| 17 | `deepinfra` | **DeepInfra** | Branded Vector SVG (Custom Color Fill) | No | High-Throughput Serverless Model Cloud |
| 18 | `deepseek` | **DeepSeek** | Branded Vector SVG (Custom Color Fill) | No | Leading Global Foundation & Reasoning Models |
| 19 | `dit` | **Dit.ai** | Branded Vector SVG (Custom Color Fill) | No | Cloud Inference & Specialized Gateway |
| 20 | `elevenlabs` | **Elevenlabs** | Branded Vector SVG (Custom Color Fill) | No | Voice Synthesis & Audio Generation |
| 21 | `empower` | **Empower AI** | Branded Vector SVG (Custom Color Fill) | No | Cloud Inference & Specialized Gateway |
| 22 | `fastinfra` | **FastInfra** | Branded Vector SVG (Custom Color Fill) | No | Cloud Inference & Specialized Gateway |
| 23 | `featherless` | **Featherless AI** | Branded Vector SVG (Custom Color Fill) | No | Cloud Inference & Specialized Gateway |
| 24 | `fenay` | **Fenay AI** | Branded Vector SVG (Custom Color Fill) | No | Cloud Inference & Specialized Gateway |
| 25 | `fireworks` | **Fireworks AI** | Branded Vector SVG (Custom Color Fill) | Yes | High-Throughput Serverless Model Cloud |
| 26 | `freeai` | **Free.ai** | Branded Vector SVG (Custom Color Fill) | No | Cloud Inference & Specialized Gateway |
| 27 | `freeinference` | **FreeInference** | Branded Vector SVG (Custom Color Fill) | No | Cloud Inference & Specialized Gateway |
| 28 | `freemodel` | **FreeModel** | Branded Vector SVG (Custom Color Fill) | No | Cloud Inference & Specialized Gateway |
| 29 | `friendli` | **FriendliAI** | Branded Vector SVG (Custom Color Fill) | No | Cloud Inference & Specialized Gateway |
| 30 | `gmiserving` | **GMI Serving** | Branded Vector SVG (Custom Color Fill) | No | Cloud Inference & Specialized Gateway |
| 31 | `gemini` | **Gemini** | Branded Vector SVG (Custom Color Fill) | Yes | Tier-1 Frontier Multi-Modal LLM Provider |
| 32 | `groq` | **Groq** | Branded Vector SVG (Custom Color Fill) | No | Ultra-Fast Hardware LPU / Silicon Inference |
| 33 | `huggingface` | **HuggingFace** | Branded Vector SVG (Custom Color Fill) | Yes | Cloud Inference & Specialized Gateway |
| 34 | `hyperbolic` | **Hyperbolic** | Branded Vector SVG (Custom Color Fill) | No | Ultra-Fast Hardware LPU / Silicon Inference |
| 35 | `inceptionlabs` | **Inception Labs** | Branded Vector SVG (Custom Color Fill) | No | Cloud Inference & Specialized Gateway |
| 36 | `inferencenet` | **Inference.net** | Branded Vector SVG (Custom Color Fill) | No | Cloud Inference & Specialized Gateway |
| 37 | `jina` | **Jina AI** | Branded Vector SVG (Custom Color Fill) | Yes | Specialized High-Performance Embeddings & Reranking |
| 38 | `kluster` | **Kluster AI** | Branded Vector SVG (Custom Color Fill) | No | Cloud Inference & Specialized Gateway |
| 39 | `krutrim` | **Krutrim** | Branded Vector SVG (Custom Color Fill) | No | Indic Regional & Sovereign Indian AI Models |
| 40 | `lepton` | **Lepton AI** | Branded Vector SVG (Custom Color Fill) | No | Cloud Inference & Specialized Gateway |
| 41 | `lingyiwanwu` | **Lingyi Wanwu** | Branded Vector SVG (Custom Color Fill) | No | Cloud Inference & Specialized Gateway |
| 42 | `mancer` | **Mancer** | Branded Vector SVG (Custom Color Fill) | No | Cloud Inference & Specialized Gateway |
| 43 | `minimax` | **MiniMax** | Branded Vector SVG (Custom Color Fill) | No | Cloud Inference & Specialized Gateway |
| 44 | `mistral` | **Mistral AI** | Branded Vector SVG (Custom Color Fill) | Yes | Leading Global Foundation & Reasoning Models |
| 45 | `modelscope` | **ModelScope** | Branded Vector SVG (Custom Color Fill) | No | Cloud Inference & Specialized Gateway |
| 46 | `monsterapi` | **MonsterAPI** | Branded Vector SVG (Custom Color Fill) | No | Cloud Inference & Specialized Gateway |
| 47 | `moonshot` | **Moonshot AI** | Branded Vector SVG (Custom Color Fill) | No | Cloud Inference & Specialized Gateway |
| 48 | `morphllm` | **MorphLLM** | Branded Vector SVG (Custom Color Fill) | No | Cloud Inference & Specialized Gateway |
| 49 | `nlpcloud` | **NLP Cloud** | Branded Vector SVG (Custom Color Fill) | No | Cloud Inference & Specialized Gateway |
| 50 | `nvidia` | **NVIDIA NIM** | Branded Vector SVG (Custom Color Fill) | No | NVIDIA NIM Microservices & Enterprise Containers |
| 51 | `nanogpt` | **Nano-GPT** | Branded Vector SVG (Custom Color Fill) | No | Cloud Inference & Specialized Gateway |
| 52 | `nararouter` | **NaraRouter** | Branded Vector SVG (Custom Color Fill) | No | Cloud Inference & Specialized Gateway |
| 53 | `navy` | **Navy AI** | Branded Vector SVG (Custom Color Fill) | No | Cloud Inference & Specialized Gateway |
| 54 | `nebius` | **Nebius Token Factory** | Static Image (/images/nebius.webp) | Yes | High-Throughput Serverless Model Cloud |
| 55 | `nousresearch` | **Nous Research** | Branded Vector SVG (Custom Color Fill) | No | Cloud Inference & Specialized Gateway |
| 56 | `novita` | **Novita AI** | Branded Vector SVG (Custom Color Fill) | No | High-Throughput Serverless Model Cloud |
| 57 | `nscale` | **Nscale** | Branded Vector SVG (Custom Color Fill) | No | Cloud Inference & Specialized Gateway |
| 58 | `ollama` | **Ollama** | Theme-Aware Vector SVG (Dynamic Light/Dark) | Yes | Self-Hosted & Local Open-Weights Engine |
| 59 | `openai` | **OpenAI** | Theme-Aware Vector SVG (Dynamic Light/Dark) | Yes | Tier-1 Frontier Multi-Modal LLM Provider |
| 60 | `openadapter` | **OpenAdapter** | Branded Vector SVG (Custom Color Fill) | No | Cloud Inference & Specialized Gateway |
| 61 | `opencode-go` | **OpenCode Go** | Theme-Aware Fallback Vector | No | Cloud Inference & Specialized Gateway |
| 62 | `opencode-zen` | **OpenCode Zen** | Theme-Aware Fallback Vector | No | Cloud Inference & Specialized Gateway |
| 63 | `openrouter` | **OpenRouter** | Branded Vector SVG (Custom Color Fill) | Yes | Cloud Inference & Specialized Gateway |
| 64 | `opper` | **Opper** | Branded Vector SVG (Custom Color Fill) | No | Cloud Inference & Specialized Gateway |
| 65 | `parasail` | **Parasail** | Branded Vector SVG (Custom Color Fill) | No | Cloud Inference & Specialized Gateway |
| 66 | `perplexity` | **Perplexity** | Branded Vector SVG (Custom Color Fill) | No | Cloud Inference & Specialized Gateway |
| 67 | `portkey` | **Portkey** | Branded Vector SVG (Custom Color Fill) | No | Cloud Inference & Specialized Gateway |
| 68 | `publicai` | **PublicAI** | Branded Vector SVG (Custom Color Fill) | No | Cloud Inference & Specialized Gateway |
| 69 | `reka` | **Reka AI** | Branded Vector SVG (Custom Color Fill) | No | Cloud Inference & Specialized Gateway |
| 70 | `relace` | **Relace** | Branded Vector SVG (Custom Color Fill) | No | Cloud Inference & Specialized Gateway |
| 71 | `replicate` | **Replicate** | Branded Vector SVG (Custom Color Fill) | No | Image, Video & Generative Media |
| 72 | `runware` | **Runware** | Branded Vector SVG (Custom Color Fill) | No | Image, Video & Generative Media |
| 73 | `runway` | **Runway** | Branded Vector SVG (Custom Color Fill) | No | Image, Video & Generative Media |
| 74 | `sgl` | **SGLang** | Static Image (/images/sgl.webp) | Yes | Self-Hosted & Local Open-Weights Engine |
| 75 | `sakana` | **Sakana AI** | Branded Vector SVG (Custom Color Fill) | No | Cloud Inference & Specialized Gateway |
| 76 | `sambanova` | **SambaNova** | Branded Vector SVG (Custom Color Fill) | No | Ultra-Fast Hardware LPU / Silicon Inference |
| 77 | `sarvam` | **Sarvam AI** | Branded Vector SVG (Custom Color Fill) | No | Indic Regional & Sovereign Indian AI Models |
| 78 | `scaleway` | **Scaleway** | Branded Vector SVG (Custom Color Fill) | No | Cloud Inference & Specialized Gateway |
| 79 | `sensenova` | **SenseNova** | Branded Vector SVG (Custom Color Fill) | No | Cloud Inference & Specialized Gateway |
| 80 | `siliconflow` | **SiliconFlow** | Branded Vector SVG (Custom Color Fill) | No | High-Throughput Serverless Model Cloud |
| 81 | `stepfun` | **StepFun** | Branded Vector SVG (Custom Color Fill) | No | Cloud Inference & Specialized Gateway |
| 82 | `hunyuan` | **Tencent Hunyuan** | Branded Vector SVG (Custom Color Fill) | No | Cloud Inference & Specialized Gateway |
| 83 | `together` | **Together AI** | Branded Vector SVG (Custom Color Fill) | No | High-Throughput Serverless Model Cloud |
| 84 | `totalgpt` | **TotalGPT** | Branded Vector SVG (Custom Color Fill) | No | Cloud Inference & Specialized Gateway |
| 85 | `upstage` | **Upstage** | Branded Vector SVG (Custom Color Fill) | No | Cloud Inference & Specialized Gateway |
| 86 | `vertex` | **Vertex AI** | Branded Vector SVG (Custom Color Fill) | Yes | Tier-1 Frontier Multi-Modal LLM Provider |
| 87 | `ark` | **Volcengine Ark** | Branded Vector SVG (Custom Color Fill) | No | Cloud Inference & Specialized Gateway |
| 88 | `voyage` | **Voyage AI** | Branded Vector SVG (Custom Color Fill) | Yes | Specialized High-Performance Embeddings & Reranking |
| 89 | `wafer` | **Wafer** | Branded Vector SVG (Custom Color Fill) | No | Cloud Inference & Specialized Gateway |
| 90 | `zhipu` | **Zhipu AI** | Branded Vector SVG (Custom Color Fill) | No | Cloud Inference & Specialized Gateway |
| 91 | `spark` | **iFlytek Spark** | Branded Vector SVG (Custom Color Fill) | No | Cloud Inference & Specialized Gateway |
| 92 | `vllm` | **vLLM** | Branded Vector SVG (Custom Color Fill) | Yes | Self-Hosted & Local Open-Weights Engine |
| 93 | `xai` | **xAI** | Branded Vector SVG (Custom Color Fill) | No | Cloud Inference & Specialized Gateway |

### Provider Categories & Distribution:

- **Frontier Cloud Providers**: OpenAI, Anthropic, Azure, AWS Bedrock, AWS Bedrock Mantle, Google Vertex AI, Gemini.
- **Ultra-Fast Hardware Accelerators**: Groq (LPU), Cerebras (CS-3 Wafer-scale), SambaNova (DataScale), Hyperbolic.
- **Open Source Inference Hubs**: Together AI, Fireworks AI, DeepInfra, SiliconFlow, Novita AI, Nebius Token Factory, Baseten, Lepton, Anyscale, FriendliAI.
- **Local & Private Serving**: Ollama, vLLM, SGLang (Runs private on-prem or VPC clusters).
- **Regional & Sovereign Models**: Sarvam AI (India), Krutrim (India), Alibaba DashScope / DashScope China, Baidu Qianfan, Tencent Hunyuan, SenseNova, iFlytek Spark, Moonshot AI, MiniMax, StepFun, Baichuan, Zhipu AI.
- **Multi-Media & Specialized**: ElevenLabs (Audio/TTS), Runway & Runware (Video), Replicate, Voyage AI (Embeddings), Jina AI (Search/Rerank).
- **Embedding Ready Providers (16 Built-in)**: Azure, Bedrock, Cohere, Fireworks, Gemini, HuggingFace, Mistral, Nebius, Ollama, OpenAI, OpenRouter, SGLang, Vertex AI, vLLM, Voyage AI, Jina AI.

---

## 3. Logo & Image Architecture (Logo Epadi Work Aagudhu?)

UnifAI UI-la logo rendering romba efficient-ah irukum. Enna architecture use panrom na:
1. **Theme-Aware SVG Components (`ui/lib/constants/icons.tsx`)**:
   - Monochromatic logos like Anthropic, OpenAI: Code checks `theme === 'light' ? fill='black' : fill='white'`. Dark mode-la white logo-vum, light mode-la black logo-vum automatically switch aagum without flicker.
   - Multi-color branded logos like DeepSeek (`#4D6BFE`), Cerebras (`#F15A29`), AWS Bedrock (Gradient from `#6350FB` to `#3D8FFF`), Cohere (`#39594D`, `#D18EE2`, `#FF7759`): Vector SVGs with exact brand paths preserve high DPI sharpness on Retina displays.
2. **Static WebP Assets (`ui/public/images/`)**:
   - Complex corporate logos (like Azure) use lightweight `<img src="/images/azure.webp" width={14} height={14} loading="lazy" decoding="async" />`.
3. **Custom Provider Logo Fallback**:
   - User oru custom model provider (e.g. `my-vllm-server`) add pannum bodhu, `getProviderLabel(provider)` check pannum. Adhu known providers list-la illana, system automatically oru generic AI/Database icon render panni, pakkathula `Custom` badge display pannum.
4. **Responsive Icon Sizing**:
   - `resolveSize()` helper: `xs` (20px), `sm` (32px), `md` (40px), `lg` (48px), `xl` (64px) or direct numeric pixel values.

---

## 4. Adding Custom Model Providers (Custom Provider Epadi Add Panrathu?)

UnifAI-la 93 providers mattum illama, ungaloda own private model or fine-tuned model-ai yum connect panlaam via `/workspace/providers` -> **Add Custom Provider** (`addNewCustomProviderSheet.tsx`):

### Step-by-Step Process:
1. **Go to Model Providers Page**: Navigate to `https://unifaiv2.dev-yp.com/workspace/providers`.
2. **Click Add Provider -> Custom Provider**: Top right dropdown-la click pannunga.
3. **Fill Configuration Form**:
   - **Provider Name**: e.g., `company-llama-vllm`
   - **Base Provider Format**: Choose `openai` or `anthropic` (UnifAI translates internal calls into this standard format).
   - **Base URL**: e.g., `http://10.0.1.50:8000/v1` or `https://ai.internal.corp/v1`
   - **Allowed Request Types**: Checkboxes for chat completion, streaming, embeddings, token count, etc.
   - **Keyless Mode (`is_key_less`)**: If running inside local private network without API keys, enable Keyless mode.
   - **Allow Private Network**: Toggle ON to route traffic to RFC1918 private VPC addresses.
4. **Save**: Now custom provider catalog kulla add aagidum. Virtual Key create panni use panna start panlaam!

---

## 5. MCP Server Gateway & Library (Total 178 Servers)

UnifAI MCP (Model Context Protocol) Gateway enables LLMs to interact with external tools, APIs, and databases securely.

### MCP Servers Breakdown by Category:

### Category: General (59 Servers)
| Server Name | Transport | Auth Type | Publisher | Description |
|-------------|-----------|-----------|-----------|-------------|
| **Inside Ads** | `http` | `none` | ad.inside | Telegram ad exchange: estimate reach and cost with no account, then create ... |
| **hood. — .hood name service** | `http` | `none` | ag.hood | Resolve .hood names on Robinhood Chain   forward/reverse, text records, ava... |
| **Pre-Trip compliance scanner** | `stdio` | `none` | agency.kesey | Screen regulated-health marketing copy against source-cited rulesets, all 5... |
| **Trading** | `http` | `none` | agency.lona | AI-powered trading strategy development: backtesting, market data, and port... |
| **ABMeter** | `http` | `none` | ai.abmeter | Feature flagging and A/B testing platform with AI-first experimentation wor... |
| **Ideation** | `http` | `none` | ai.actwise | Actwise Ideation helps founders benchmark startup and product ideas before ... |
| **AdAdvisor MCP Server** | `http` | `none` | ai.adadvisor | Query Meta Ads performance data   accounts, campaigns, ad sets, ads, metric... |
| **Adeu** | `stdio` | `none` | ai.adeu | Automated DOCX Redlining Engine |
| **Beauty** | `http` | `none` | ai.adoraads | AI-native beauty ads, sponsored product discovery, and brand recommendation... |
| **Advisors AI Service Navigator** | `http` | `none` | ai.advisorsai | Read-only service discovery, public-page checks, and request-link preparati... |
| **Advisors AI Store Readiness Check** | `http` | `none` | ai.advisorsai | One read-only public-page readiness check with a signed, recheckable eviden... |
| **One-Page Readiness Check — 10 Signals, Arabic or English** | `http` | `none` | ai.advisorsai | Ten machine-readable signals on one public page: the top miss if any, and a... |
| *...and 47 more General servers* | - | - | - | See configs/mcp-library.json |

### Category: AI (58 Servers)
| Server Name | Transport | Auth Type | Publisher | Description |
|-------------|-----------|-----------|-----------|-------------|
| **Hugging Face** | `http` | `oauth` | huggingface | Hugging Face MCP — models, datasets, and Spaces tooling (remote). |
| **inference.sh** | `http` | `none` | ac.inference.sh | Run 150+ AI apps   image, video, audio, LLMs, 3D and more. Browse, execute,... |
| **Docs Mcp** | `http` | `none` | ac.tandem | Remote MCP server for Tandem docs, install guides, SDKs, workflows, and age... |
| **aTars MCP** | `http` | `none` | ai.aarna | Crypto market signals, technical indicators, and sentiment analysis for AI ... |
| **Agentberg** | `http` | `none` | ai.agentberg | Agent-to-agent trading intelligence exchange. Publish findings, vote on qua... |
| **AgentDM** | `http` | `none` | ai.agentdm | Agent-to-agent messaging platform using MCP for cross-model communication. |
| **AgentDM: Agent to Agent Communication Platform** | `http` | `none` | ai.agentdm | Agent communication platform for agent to agent messaging via MCP. Messages... |
| **Mcp** | `http` | `none` | ai.agentgates | Confidential compute and inference sold to agents over x402 USDC, plus an a... |
| **Agent Fabrication Network (UFP)** | `http` | `none` | ai.agenticfabricationnetwork | Turn designs into shipped parts: quote 3D printing, CNC, and decals, then c... |
| **Agentic Fabrication Network (AFN)** | `http` | `none` | ai.agenticfabricationnetwork | Turn designs into shipped parts: quote 3D printing, CNC, and decals, then c... |
| **Graffeo Coffee Roasting** | `http` | `none` | ai.agenticshelf | Live MCP catalog for Graffeo Coffee Roasting   North Beach SF specialty cof... |
| **Agentic Shelf** | `http` | `none` | ai.agenticshelf | Hosted MCP for e-commerce: live product catalog, stock, and pricing for AI ... |
| *...and 46 more AI servers* | - | - | - | See configs/mcp-library.json |

### Category: Search (25 Servers)
| Server Name | Transport | Auth Type | Publisher | Description |
|-------------|-----------|-----------|-----------|-------------|
| **Brave Search** | `stdio` | `none` | brave | Official Brave Search MCP — web search via Brave Search API (stdio). |
| **Exa** | `stdio` | `none` | exa | Exa MCP — neural web search and content retrieval for agents (stdio). |
| **Tavily** | `stdio` | `none` | tavily | Tavily MCP — AI search API for agents (stdio). |
| **Goji** | `http` | `none` | agency.goji | AEO, SEO, web and brand answers from a Melbourne agency's published glossar... |
| **1325.AI** | `http` | `headers` | ai.1325 | Verified directory of 44,000+ Black-owned U.S. businesses. Search, maps, lo... |
| **Adside** | `http` | `none` | ai.adside | AI agents that manage paid ads on Meta, LinkedIn, and Google Ads from any M... |
| **Agentic News** | `http` | `none` | ai.agentic-news | AI-powered news intelligence   21 tools for personalized monitoring, briefi... |
| **Agentic Terminal Directory** | `http` | `none` | ai.agenticterminal | Verified merchants accepting agentic payments on Lightning/L402/BOLT12/USDT... |
| **AgentUtility Web Probe** | `stdio` | `none` | ai.agentutility | MCP server for the @agentutility web-probe cluster   pay-per-call x402 tool... |
| **AI-Advisors** | `http` | `none` | ai.ai-advisors | Read-only AI search visibility data: citations, AEO audits, and advisor ins... |
| **AirShelf Catalog** | `http` | `none` | ai.airshelf | Cross-vendor B2B catalog for AI agents: search, compare, find equivalents, ... |
| **AppDeploy** | `http` | `none` | ai.appdeploy | AppDeploy turns app ideas described in AI chat into live full-stack web app... |
| *...and 13 more Search servers* | - | - | - | See configs/mcp-library.json |

### Category: Developer Tools (15 Servers)
| Server Name | Transport | Auth Type | Publisher | Description |
|-------------|-----------|-----------|-----------|-------------|
| **GitHub** | `http` | `oauth` | github | Official GitHub MCP — repos, issues, PRs, and code search via GitHub Copilo... |
| **Supabase** | `http` | `oauth` | supabase | Official Supabase MCP — manage projects, run SQL, and inspect schemas. |
| **Linear** | `sse` | `oauth` | linear | Official Linear MCP — issues, cycles, and project backlog over SSE. |
| **Vercel** | `http` | `oauth` | vercel | Official Vercel MCP — projects, deployments, and docs for your Vercel accou... |
| **Cloudflare** | `http` | `oauth` | cloudflare | Official Cloudflare MCP — Workers, DNS, and account tooling. |
| **Neon** | `http` | `oauth` | neon | Official Neon MCP — serverless Postgres projects, branches, and SQL. |
| **Context7** | `http` | `none` | context7 | Upstash Context7 MCP — live, version-specific library docs for coding agent... |
| **Filesystem** | `stdio` | `none` | modelcontextprotocol | Official MCP filesystem server — read/write local files (stdio). Set path v... |
| **GitLab** | `stdio` | `none` | gitlab | GitLab MCP — projects, MRs, and issues (stdio). |
| **Propick Integration MCP** | `http` | `none` | ae.propick | Manage your real-estate stock on Propick (Dubai): bulk listing sync, lookup... |
| **Google Ads** | `http` | `none` | ai.adplane | Google Ads reporting and campaign management. Everything it creates starts ... |
| **Affiliate Networks MCP** | `stdio` | `none` | ai.agenticaffiliate | Affiliate network reporting in your AI client. Bring your own keys. Most ad... |
| *...and 3 more Developer Tools servers* | - | - | - | See configs/mcp-library.json |

### Category: Productivity (8 Servers)
| Server Name | Transport | Auth Type | Publisher | Description |
|-------------|-----------|-----------|-----------|-------------|
| **Notion** | `http` | `oauth` | notion | Official Notion MCP — search and edit pages and databases in your workspace... |
| **Slack** | `http` | `oauth` | slack | Official Slack MCP — search workspace, read threads, and post updates. |
| **Atlassian** | `http` | `oauth` | atlassian | Official Atlassian MCP — Jira and Confluence context for agents. |
| **Asana** | `stdio` | `none` | asana | Asana MCP — tasks and projects (stdio). |
| **ClickUp** | `stdio` | `none` | clickup | ClickUp MCP — tasks and workspaces (stdio). |
| **Todoist** | `stdio` | `none` | todoist | Todoist MCP — personal task management (stdio). |
| **Aether Wealth** | `stdio` | `none` | ai.aetherwealth | Aether Wealth MCP for AI assistants: trades, alerts, market data, macro cal... |
| **File Storage** | `http` | `none` | ai.b77 | Upload files and get public CDN links in chat. |

### Category: Finance (2 Servers)
| Server Name | Transport | Auth Type | Publisher | Description |
|-------------|-----------|-----------|-----------|-------------|
| **Stripe** | `http` | `oauth` | stripe | Official Stripe MCP — customers, subscriptions, payments, and billing tools... |
| **PayPal** | `stdio` | `none` | paypal | PayPal MCP — payments and commerce APIs (stdio). |

### Category: Observability (2 Servers)
| Server Name | Transport | Auth Type | Publisher | Description |
|-------------|-----------|-----------|-----------|-------------|
| **Sentry** | `http` | `oauth` | sentry | Official Sentry MCP — error tracking, issues, and monitoring context. |
| **PostHog** | `stdio` | `none` | posthog | PostHog MCP — product analytics and feature flags (stdio). |

### Category: Automation (2 Servers)
| Server Name | Transport | Auth Type | Publisher | Description |
|-------------|-----------|-----------|-----------|-------------|
| **Playwright** | `stdio` | `none` | playwright | Official Playwright MCP — browser automation and web testing tools (stdio). |
| **AgentUtility Browser Workflow** | `stdio` | `none` | ai.agentutility | MCP server for the @agentutility browser-workflow cluster   pay-per-call x4... |

### Category: Communication (2 Servers)
| Server Name | Transport | Auth Type | Publisher | Description |
|-------------|-----------|-----------|-----------|-------------|
| **AnomalyArmor** | `stdio` | `headers` | ai.anomalyarmor | Data observability tools for engineering teams: alerts, freshness, schema d... |
| **Backengine Mcp** | `http` | `none` | ai.backengine | Surface customer & prospect context from Slack, email, transcripts and tick... |

### Category: Design (1 Servers)
| Server Name | Transport | Auth Type | Publisher | Description |
|-------------|-----------|-----------|-----------|-------------|
| **Figma** | `http` | `oauth` | figma | Official Figma MCP — design context, components, and Code Connect. |

### Category: CRM (1 Servers)
| Server Name | Transport | Auth Type | Publisher | Description |
|-------------|-----------|-----------|-----------|-------------|
| **HubSpot** | `http` | `oauth` | hubspot | Official HubSpot MCP — CRM contacts, companies, and deals (OAuth). |

### Category: E-commerce (1 Servers)
| Server Name | Transport | Auth Type | Publisher | Description |
|-------------|-----------|-----------|-----------|-------------|
| **Shopify** | `stdio` | `none` | shopify | Shopify Dev MCP — storefront and Admin API tooling for Shopify apps (stdio)... |

### Category: Communications (1 Servers)
| Server Name | Transport | Auth Type | Publisher | Description |
|-------------|-----------|-----------|-----------|-------------|
| **Twilio** | `stdio` | `none` | twilio | Twilio MCP — messaging and communications APIs (stdio). |

### Category: Data (1 Servers)
| Server Name | Transport | Auth Type | Publisher | Description |
|-------------|-----------|-----------|-----------|-------------|
| **Enforcement Database** | `http` | `none` | ai.argushq | Search Argus HQ public FDA enforcement data: warning letters, recalls, appr... |

---

## 6. How to Add & Install an MCP Server (Step-by-Step Tutorial)

UnifAI-la MCP server add panna rendu main methods irukku:

### Method A: Installing from Built-in MCP Library (Catalog Installation)

1. **Navigate to MCP Registry Library**:
   - Open `https://unifaiv2.dev-yp.com/workspace/mcp-registry/library`.
2. **Browse or Search for Server**:
   - Category filter (Developer Tools, Productivity, Search) use panni thedunga (e.g. GitHub, Notion, Brave Search, Filesystem).
3. **Click 'Install' Button**:
   - `mcpLibraryInstallSheet` open aagum.
4. **Configure Parameters**:
   - **Client Name**: Automatically slugified using `sanitizeServerName()` (e.g. `GitHub` -> `GitHub`, `Brave Search` -> `Brave_Search`).
   - **Credentials / Environment Variables**:
     - For HTTP servers with `headers` auth: Enter API Token / Bearer Key (e.g. GitHub Personal Access Token).
     - For STDIO servers: Enter required Envs (e.g., `BRAVE_API_KEY=bsA34...`).
5. **Click Save & Install**:
   - UnifAI backend runs an initial MCP `initialize` handshake, fetches the list of available tools, and registers the client.

### Method B: Adding a Custom MCP Server (Org-Wide Publishing)

Company-kulla oru private internal MCP server irundha, adha publish panna:

1. Open `/workspace/mcp-registry/library` and click **'Add Custom Server'** button.
2. In `mcpLibraryAddServerSheet`:
   - **Server Name**: `Internal-DB-MCP`
   - **Connection Type**: Select `http`, `sse`, or `stdio`.
   - **If HTTP/SSE**: Enter Connection URL (e.g., `https://mcp.internal.mycompany.com/v1/sse`).
   - **If STDIO**: Enter Command (`npx` or `uvx` or `python`), Arguments (comma-separated, e.g. `-y, @company/mcp-server`), and Environment Variable Names (e.g. `DB_URL, JWT_SECRET`).
   - **Authentication Type**: Select `none`, `headers`, `oauth`, `per_user_headers`, or `per_user_oauth`.
   - **Category & Description**: Enter description and tags.
3. Click **Publish Server** -> Org-wide library-la display aagum. Anyone in the team can now install it!

---

## 7. Concrete Real-World Examples from Codebase (Real Example Solli Kaatrom)

### Example 1: GitHub Copilot MCP Server (Remote HTTP Transport + OAuth/Bearer Token)

This is an official server present in `configs/mcp-library.json`:

```json
{
  "name": "GitHub",
  "category": "Developer Tools",
  "connection_type": "http",
  "connection_url": "https://api.githubcopilot.com/mcp/",
  "auth_type": "oauth",
  "publisher": "github",
  "docs_url": "https://github.com/github/github-mcp-server"
}
```
#### End-to-End Execution Flow (Epadi Work Aagudhu?):
1. **Installation**:
   - UnifAI Gateway connects to `https://api.githubcopilot.com/mcp/`.
   - Header: `Authorization: Bearer ghp_YourPersonalAccessToken123`
2. **Discovered Tools**:
   - `search_repositories`: Search code and repos across GitHub.
   - `get_file_contents`: Read code files from any branch.
   - `create_issue`: File a bug ticket or feature request.
   - `create_pull_request`: Submit PRs automatically.
3. **Connecting to a Tool Group & Virtual Key**:
   - Go to `/workspace/mcp-registry/tool-groups` -> Create Tool Group `DevTools`.
   - Select `GitHub` MCP Client.
   - Attach this Tool Group to Virtual Key `sk-live-prod-developer`.
4. **LLM Chat Request with Tool Calling**:
   ```bash
   curl -X POST https://unifaiv2.dev-yp.com/v1/chat/completions \
     -H "Authorization: Bearer sk-live-prod-developer" \
     -H "Content-Type: application/json" \
     -d '{
       "model": "gpt-4o",
       "messages": [{"role": "user", "content": "Check issues in repo myorg/auth-service and report top bugs"}],
       "tool_choice": "auto"
     }'
   ```
5. **Result & Logging**:
   - UnifAI intercepts the LLM's `create_issue` or `search_issues` tool call, executes it securely via GitHub MCP, returns the response back to the LLM, and streams the answer to the user.
   - Full request, latency, and response status are captured in `/workspace/mcp-logs`.

### Example 2: Filesystem / Database MCP Server (Local STDIO Transport)

This is an official STDIO server present in `configs/mcp-library.json`:

```json
{
  "name": "Filesystem",
  "category": "Developer Tools",
  "connection_type": "stdio",
  "stdio_config": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/data/reports"]
  },
  "auth_type": "none"
}
```
#### End-to-End Execution Flow:
1. **Installation**:
   - UnifAI daemon spawns a child process: `npx -y @modelcontextprotocol/server-filesystem /data/reports`.
   - Communicates over standard input/output (`stdin`/`stdout`) using JSON-RPC 2.0 messages.
2. **Discovered Tools**:
   - `read_file`: Reads specific content from sandbox directory.
   - `write_file`: Writes generated report file.
   - `list_directory`: Lists directory hierarchy.
3. **Security Isolation**:
   - UnifAI restricts file operations strictly to the `/data/reports` directory preventing path traversal attacks.
4. **Observability**:
   - Every read/write command is logged in `/workspace/mcp-logs` with duration, caller virtual key, and byte count.

---

## 8. Summary Table & Quick Reference (Mukiya Kuripugal)

| Feature | Details | Code Location |
|---|---|---|
| **Built-in Model Providers** | 93 Providers (OpenAI, Anthropic, Bedrock, Vertex, Sarvam, etc.) | `ui/lib/constants/logs.ts` |
| **Custom Model Providers** | Unlimited (Any OpenAI/Anthropic compatible HTTP endpoint) | `addNewCustomProviderSheet.tsx` |
| **Provider Logos** | Theme-aware dynamic SVGs & WebP assets | `ui/lib/constants/icons.tsx` |
| **MCP Server Library** | 178 Pre-configured servers (14 categories) | `configs/mcp-library.json` |
| **MCP Transports** | `stdio` (43 servers), `http` (132 servers), `sse` (3 servers) | `mcpLibraryAddServerSheet.tsx` |
| **MCP Auth Types** | `none`, `headers`, `oauth`, `per_user_headers`, `per_user_oauth` | `mcpLibraryInstallSheet.tsx` |
| **MCP Execution Logs** | Latency, status, tool calls, payloads | `/workspace/mcp-logs` |