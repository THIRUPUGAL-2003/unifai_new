import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";
import { Link, useNavigate } from "@tanstack/react-router";
import {
	Zap,
	Database,
	Shield,
	ArrowRight,
	Code,
	Lock,
	Activity,
	Terminal,
	CheckCircle,
	CheckCircle2,
	ExternalLink,
	Menu,
	X,
	Sparkles,
	Laptop,
	Key,
	Cpu,
	Layers,
	FileText,
	Eye,
	AlertTriangle,
	Calendar,
	Mail,
	Building2,
	Users,
	Check,
	Copy,
	Play,
	Flame,
	Globe,
	RefreshCw,
	Clock,
	ArrowUpRight,
	Sliders,
	Search,
	ChevronDown
} from "lucide-react";
import { useEffect, useState, useMemo } from "react";
import { getApiBaseUrl } from "@/lib/utils/port";
import { DOCS } from "@/lib/constants/docs";
import { COMPANY_LOGO, COMPANY_NAME } from "@/lib/constants/config";

export default function LandingPage() {
	const [isLoggedIn, setIsLoggedIn] = useState(false);
	const [codeTab, setCodeTab] = useState<"curl" | "python" | "node" | "guard">("python");
	const [consoleTab, setConsoleTab] = useState<"guard" | "gateway">("guard");
	const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
	const [copiedCode, setCopiedCode] = useState(false);
	const [openFaq, setOpenFaq] = useState<number | null>(0);
	const navigate = useNavigate();

	// Demo Booking Modal State
	const [isDemoModalOpen, setIsDemoModalOpen] = useState(false);
	const [demoSubmitted, setDemoSubmitted] = useState(false);
	const [demoForm, setDemoForm] = useState({
		fullName: "",
		email: "",
		company: "",
		teamSize: "50-250",
		interest: "both",
		notes: "",
	});

	// Interactive Sandbox / DLP Tester State
	const samplePrompts = useMemo(() => [
		{
			id: "secrets",
			title: "AWS & Stripe Keys",
			raw: "Help me debug this lambda. AWS_SECRET=AKIAIOSFODNN7EXAMPLE and STRIPE_KEY=sk_live_51Mzxyz89234",
			redacted: "Help me debug this lambda. AWS_SECRET=[REDACTED_API_KEY] and STRIPE_KEY=[REDACTED_SECRET_KEY]",
			policy: "Secrets & Credentials Protection (Rule #12)",
			action: "REDACTED",
			actionColor: "text-amber-400 bg-amber-400/10 border-amber-400/30",
		},
		{
			id: "pci",
			title: "Customer Credit Card",
			raw: "Analyze customer refund request for John Doe, Card: 4532-8921-4432-9011, Exp: 08/29, CVV: 891",
			redacted: "Analyze customer refund request for John Doe, Card: [REDACTED_PCI_CARD], Exp: [REDACTED], CVV: [***]",
			policy: "PCI-DSS v4.0 Compliance Shield",
			action: "REDACTED",
			actionColor: "text-amber-400 bg-amber-400/10 border-amber-400/30",
		},
		{
			id: "code",
			title: "Proprietary Core Algorithm",
			raw: "Here is our proprietary trading engine backend SQL and auth tokens: SELECT * FROM users_credentials WHERE ...",
			redacted: "BLOCKED: Prompt contains corporate proprietary database schema and credential dump.",
			policy: "Corporate Source & Data Exfiltration Rule",
			action: "BLOCKED",
			actionColor: "text-rose-400 bg-rose-400/10 border-rose-400/30",
		},
		{
			id: "safe",
			title: "Normal Engineering Prompt",
			raw: "Summarize the key differences between PostgreSQL JSONB indexing and MySQL virtual columns.",
			redacted: "Summarize the key differences between PostgreSQL JSONB indexing and MySQL virtual columns.",
			policy: "Standard Developer Policy (Allowed)",
			action: "ALLOWED",
			actionColor: "text-emerald-400 bg-emerald-400/10 border-emerald-400/30",
		},
	], []);

	const [selectedSample, setSelectedSample] = useState(samplePrompts[0]);
	const [customPrompt, setCustomPrompt] = useState(samplePrompts[0].raw);

	useEffect(() => {
		fetch(`${getApiBaseUrl()}/session/is-auth-enabled`, {
			credentials: "include",
		})
			.then((res) => (res.ok ? res.json() : null))
			.then((data) => {
				if (data && (!data.is_auth_enabled || data.has_valid_token)) {
					setIsLoggedIn(true);
				}
			})
			.catch(() => {});
	}, []);

	const handleCopyCode = (text: string) => {
		navigator.clipboard.writeText(text);
		setCopiedCode(true);
		setTimeout(() => setCopiedCode(false), 2000);
	};

	const handleDemoSubmit = (e: React.FormEvent) => {
		e.preventDefault();
		if (!demoForm.fullName || !demoForm.email) return;
		setDemoSubmitted(true);
	};

	const resetDemoModal = () => {
		setDemoSubmitted(false);
		setIsDemoModalOpen(false);
		setDemoForm({
			fullName: "",
			email: "",
			company: "",
			teamSize: "50-250",
			interest: "both",
			notes: "",
		});
	};

	const codeExamples = {
		python: `from openai import OpenAI

# Simply route through UnifAI Gateway (1-line change)
client = OpenAI(
    base_url="https://unifai.yourcompany.com/v1",
    api_key="unifai_vk_live_enterprise"
)

response = client.chat.completions.create(
    model="anthropic/claude-3-7-sonnet", # Or gpt-4o, grok-2, gemini-2-flash
    messages=[{"role": "user", "content": "Analyze our enterprise compliance log"}]
)

print(response.choices[0].message.content)`,
		curl: `curl -X POST https://unifai.yourcompany.com/v1/chat/completions \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer unifai_vk_live_enterprise" \\
  -d '{
    "model": "openai/gpt-4o",
    "messages": [
      {
        "role": "user",
        "content": "Evaluate our security guardrails and semantic caching"
      }
    ]
  }'`,
		node: `import OpenAI from "openai";

// Drop-in replacement with OpenAI standard SDK
const openai = new OpenAI({
  baseURL: "https://unifai.yourcompany.com/v1",
  apiKey: "unifai_vk_live_enterprise"
});

const response = await openai.chat.completions.create({
  model: "claude-3-7-sonnet",
  messages: [{ role: "user", content: "Optimize our multi-model LLM architecture" }]
});

console.log(response.choices[0].message.content);`,
		guard: `# Silent Enterprise Deployment via MDM (Intune / Jamf / GPO)
# Windows Silent Install:
UnifAI_Guard_Setup.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART

# macOS Silent Command:
sudo ./Install_UnifAI_Guard.command --silent

# Automatically shields ChatGPT, Claude, Grok, Gemini, Perplexity with zero user friction.`
	};

	const faqs = [
		{
			q: "Does Browser Guard slow down employee web browsing?",
			a: "No. UnifAI Browser Guard uses an ultra-fast local PAC proxy engine that operates in < 1.2 milliseconds. It only inspects traffic directed at your designated enterprise AI target websites (ChatGPT, Grok, Claude, etc.), leaving all standard corporate browsing completely untouched at full native network speeds."
		},
		{
			q: "How does Semantic Caching reduce our OpenAI and Anthropic bills?",
			a: "UnifAI maintains an intelligent vector embedding cache. When an employee or backend system sends a prompt semantically similar to an earlier request, UnifAI instantly returns the cached response with 0ms LLM processing time and $0.00 model token cost, cutting API expenditure by up to 85%."
		},
		{
			q: "Can UnifAI be hosted on-premise or in our own AWS / Azure VPC?",
			a: "Yes. UnifAI is built with a lightweight, high-throughput Go backend and standard PostgreSQL architecture. You can deploy it inside your air-gapped data center, private VPC, Kubernetes cluster, or Docker environment so your corporate data never leaves your perimeter."
		},
		{
			q: "How does Browser Guard handle file uploads, PDFs, and voice prompts?",
			a: "Browser Guard intercepts multipart file uploads and media requests before they leave the browser. It extracts embedded text from PDFs, CSVs, text documents, and voice streams, running DLP filters in memory and blocking or redacting sensitive contents instantly."
		},
		{
			q: "How easy is it to migrate our existing codebase to the UnifAI Gateway?",
			a: "It takes literally 1 line of code. Because UnifAI provides full 100% OpenAI API compatibility, you simply change your client's baseURL to point to your UnifAI endpoint. No code refactoring, no SDK changes, and no retraining required."
		},
		{
			q: "What enterprise compliance standards does UnifAI adhere to?",
			a: "UnifAI is engineered for SOC2 Type II, HIPAA, GDPR, and ISO 27001 readiness. It provides immutable audit trails, comprehensive role-based access control (RBAC), and configurable zero-data retention policies."
		}
	];

	const companyLogoSrc = COMPANY_LOGO;
	const productName = "UnifAI";
	const companyFullName = COMPANY_NAME;

	return (
		<div className="bg-[#07090e] text-[#e1e4ea] min-h-screen font-sans selection:bg-[#00f2fe]/25 selection:text-white overflow-x-hidden relative">
			{/* Ambient Gradient Glows */}
			<div className="absolute top-0 left-1/2 -translate-x-1/2 w-[1000px] h-[550px] bg-gradient-to-b from-[#00f2fe]/10 via-[#4facfe]/5 to-transparent rounded-full blur-[140px] pointer-events-none" />
			<div className="absolute top-[800px] -left-48 w-[600px] h-[600px] bg-[#6366f1]/8 rounded-full blur-[160px] pointer-events-none" />
			<div className="absolute top-[1600px] -right-48 w-[600px] h-[600px] bg-[#00f2fe]/8 rounded-full blur-[160px] pointer-events-none" />

			{/* Top Announcement Banner */}
			<div className="bg-gradient-to-r from-[#0d1527] via-[#091e3a] to-[#0d1527] border-b border-[#1e293b]/70 py-2.5 px-4 text-center text-xs sm:text-sm">
				<div className="max-w-7xl mx-auto flex items-center justify-center gap-2 flex-wrap text-slate-300">
					<span className="inline-flex items-center gap-1 font-semibold text-[#00f2fe] bg-[#00f2fe]/10 px-2 py-0.5 rounded-full border border-[#00f2fe]/20">
						<Sparkles className="h-3 w-3 animate-pulse" />
						What's New
					</span>
					<span>
						<strong className="text-white">UnifAI Browser Guard v1.1 Live</strong> — Enterprise DLP support for Grok, ChatGPT, Claude, and custom AI tools.
					</span>
					<button
						onClick={() => setIsDemoModalOpen(true)}
						className="inline-flex items-center gap-1 font-semibold text-[#00f2fe] hover:text-white hover:underline underline-offset-2 ml-1 cursor-pointer"
					>
						Schedule a 15-min Demo <ArrowRight className="h-3 w-3" />
					</button>
				</div>
			</div>

			{/* Sticky Glassmorphic Navbar */}
			<nav className="sticky top-0 z-50 border-b border-[#1e293b]/80 bg-[#07090e]/85 backdrop-blur-xl transition-all duration-200">
				<div className="max-w-7xl mx-auto px-6 h-[4.5rem] flex items-center justify-between">
					<a href="/" className="flex items-center gap-3" aria-label={productName}>
						<img
							src={companyLogoSrc}
							alt={companyFullName}
							className="h-10 sm:h-11 w-auto max-w-[min(46vw,200px)] shrink-0 object-contain"
							onError={(e) => {
								const target = e.currentTarget;
								if (!target.src.endsWith("/header_logo.png")) {
									target.src = "/header_logo.png";
								}
							}}
						/>
						<span className="text-xl font-extrabold tracking-tight text-white flex items-center gap-1.5">
							{productName}
							<span className="text-[10px] font-mono tracking-widest text-[#00f2fe] bg-[#00f2fe]/10 border border-[#00f2fe]/20 px-1.5 py-0.5 rounded">
								ENTERPRISE
							</span>
						</span>
					</a>

					{/* Desktop Navigation Links */}
					<div className="hidden lg:flex items-center gap-7 text-sm font-medium text-slate-300">
						<a href="#products" className="hover:text-[#00f2fe] transition-colors">Products</a>
						<a href="#simulator" className="hover:text-[#00f2fe] transition-colors">Live DLP Simulator</a>
						<a href="#features" className="hover:text-[#00f2fe] transition-colors">Platform Features</a>
						<a href="#comparison" className="hover:text-[#00f2fe] transition-colors">Why UnifAI</a>
						<a href="#code" className="hover:text-[#00f2fe] transition-colors">Quickstart</a>
						<a href={DOCS.home} target="_blank" rel="noopener noreferrer" className="hover:text-[#00f2fe] transition-colors flex items-center gap-1">
							Docs <ExternalLink className="h-3 w-3 opacity-60" />
						</a>
					</div>

					{/* Header Action Buttons */}
					<div className="hidden md:flex items-center gap-3">
						<button
							onClick={() => setIsDemoModalOpen(true)}
							className="text-xs sm:text-sm font-semibold text-slate-300 hover:text-white border border-[#334155] hover:border-[#00f2fe]/50 bg-[#0f172a]/60 hover:bg-[#1e293b] px-4 py-2 rounded-lg transition-all flex items-center gap-1.5 cursor-pointer"
						>
							<Calendar className="h-3.5 w-3.5 text-[#00f2fe]" />
							Book a Demo
						</button>

						{isLoggedIn ? (
							<Button
								onClick={() => navigate({ to: "/workspace" })}
								className="bg-gradient-to-r from-[#00f2fe] to-[#4facfe] text-[#07090e] hover:opacity-95 font-bold shadow-[0_0_20px_rgba(0,242,254,0.3)] rounded-lg h-9 px-5 transition-all hover:scale-[1.02]"
							>
								Dashboard
								<ArrowRight className="h-4 w-4 ml-1.5" />
							</Button>
						) : (
							<>
								<Link to="/login" className="text-sm font-semibold text-slate-300 hover:text-white px-3 py-1.5">
									Sign In
								</Link>
								<Button
									onClick={() => navigate({ to: "/signup" })}
									className="bg-gradient-to-r from-[#00f2fe] to-[#4facfe] text-[#07090e] hover:opacity-95 font-bold shadow-[0_0_20px_rgba(0,242,254,0.3)] rounded-lg h-9 px-4 transition-all hover:scale-[1.02]"
								>
									Start Free
								</Button>
							</>
						)}
					</div>

					{/* Mobile Menu Button */}
					<button
						onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
						className="lg:hidden text-white p-2 rounded-lg hover:bg-slate-800/60 focus:outline-none"
						aria-label="Toggle menu"
					>
						{mobileMenuOpen ? <X className="h-6 w-6 text-[#00f2fe]" /> : <Menu className="h-6 w-6" />}
					</button>
				</div>

				{/* Mobile Navigation Drawer */}
				{mobileMenuOpen && (
					<div className="lg:hidden border-b border-[#1e293b] bg-[#07090e]/98 px-6 py-6 space-y-4 animate-in fade-in duration-150">
						<a href="#products" onClick={() => setMobileMenuOpen(false)} className="block py-2 text-base text-slate-300 hover:text-[#00f2fe]">Products</a>
						<a href="#simulator" onClick={() => setMobileMenuOpen(false)} className="block py-2 text-base text-slate-300 hover:text-[#00f2fe]">Live DLP Simulator</a>
						<a href="#features" onClick={() => setMobileMenuOpen(false)} className="block py-2 text-base text-slate-300 hover:text-[#00f2fe]">Platform Features</a>
						<a href="#comparison" onClick={() => setMobileMenuOpen(false)} className="block py-2 text-base text-slate-300 hover:text-[#00f2fe]">Why UnifAI</a>
						<a href="#code" onClick={() => setMobileMenuOpen(false)} className="block py-2 text-base text-slate-300 hover:text-[#00f2fe]">Quickstart</a>
						<a href={DOCS.home} target="_blank" rel="noopener noreferrer" className="block py-2 text-base text-slate-300 hover:text-[#00f2fe] flex items-center gap-1.5">
							Documentation <ExternalLink className="h-4 w-4 opacity-60" />
						</a>

						<div className="pt-4 border-t border-[#1e293b] flex flex-col gap-3">
							<button
								onClick={() => { setMobileMenuOpen(false); setIsDemoModalOpen(true); }}
								className="w-full py-2.5 rounded-lg border border-[#00f2fe]/40 text-[#00f2fe] bg-[#00f2fe]/10 font-semibold text-center flex items-center justify-center gap-2 cursor-pointer"
							>
								<Calendar className="h-4 w-4" />
								Book an Enterprise Demo
							</button>
							{isLoggedIn ? (
								<Button
									onClick={() => { setMobileMenuOpen(false); navigate({ to: "/workspace" }); }}
									className="w-full bg-[#00f2fe] text-[#07090e] font-bold h-11"
								>
									Open Workspace
								</Button>
							) : (
								<div className="grid grid-cols-2 gap-3 pt-1">
									<Link
										to="/login"
										onClick={() => setMobileMenuOpen(false)}
										className="border border-[#334155] text-center font-semibold text-white py-2.5 rounded-lg hover:bg-slate-800 transition-colors"
									>
										Sign In
									</Link>
									<Button
										onClick={() => { setMobileMenuOpen(false); navigate({ to: "/signup" }); }}
										className="bg-gradient-to-r from-[#00f2fe] to-[#4facfe] text-[#07090e] font-bold h-11 rounded-lg"
									>
										Sign Up
									</Button>
								</div>
							)}
						</div>
					</div>
				)}
			</nav>

			{/* Hero Section */}
			<section className="relative pt-16 pb-20 md:pt-24 md:pb-32 px-6 max-w-7xl mx-auto flex flex-col items-center text-center">
				{/* Category Badge */}
				<div className="inline-flex items-center gap-2 px-4 py-1.5 bg-[#0f172a]/90 border border-[#00f2fe]/30 rounded-full text-xs sm:text-sm font-semibold text-[#00f2fe] mb-8 shadow-[0_0_20px_rgba(0,242,254,0.15)]">
					<Shield className="h-4 w-4" />
					<span>Enterprise AI Security & Unified Gateway Platform</span>
				</div>

				{/* Main Headline */}
				<h1 className="text-4xl sm:text-6xl md:text-7xl font-extrabold tracking-tight text-white mb-6 leading-[1.12] max-w-5xl">
					Govern, Secure & Accelerate <br className="hidden sm:inline" />
					<span className="bg-gradient-to-r from-[#00f2fe] via-[#38bdf8] to-[#818cf8] bg-clip-text text-transparent">
						Every AI Interaction
					</span> Across Your Enterprise
				</h1>

				{/* Subheadline */}
				<p className="text-lg sm:text-xl text-slate-400 max-w-3xl mb-10 leading-relaxed font-normal">
					The all-in-one platform providing <strong>real-time DLP Browser Guard</strong> for employee web AI usage (Grok, ChatGPT, Claude) alongside a <strong>high-throughput AI Gateway</strong> with semantic caching, virtual keys, and zero-latency routing.
				</p>

				{/* Action CTAs */}
				<div className="flex flex-col sm:flex-row items-center gap-4 w-full justify-center max-w-md sm:max-w-none">
					<button
						onClick={() => setIsDemoModalOpen(true)}
						className="w-full sm:w-auto h-12 px-8 bg-gradient-to-r from-[#00f2fe] to-[#4facfe] text-[#07090e] hover:brightness-110 font-bold rounded-xl text-base shadow-[0_0_30px_rgba(0,242,254,0.35)] transition-all hover:scale-[1.02] flex items-center justify-center gap-2 cursor-pointer"
					>
						<Calendar className="h-5 w-5" />
						Book a Live Demo
					</button>

					{isLoggedIn ? (
						<Button
							onClick={() => navigate({ to: "/workspace" })}
							className="w-full sm:w-auto h-12 px-8 bg-[#0f172a] hover:bg-[#1e293b] border border-[#334155] text-white font-semibold rounded-xl text-base transition-all"
						>
							Enter Workspace Dashboard
							<ArrowRight className="h-5 w-5 ml-2 text-[#00f2fe]" />
						</Button>
					) : (
						<Button
							onClick={() => navigate({ to: "/signup" })}
							className="w-full sm:w-auto h-12 px-8 bg-[#0f172a] hover:bg-[#1e293b] border border-[#334155] text-white font-semibold rounded-xl text-base transition-all"
						>
							Start Free Trial
							<ArrowRight className="h-5 w-5 ml-2 text-[#00f2fe]" />
						</Button>
					)}

					<a
						href="#simulator"
						className="w-full sm:w-auto h-12 px-6 flex items-center justify-center text-slate-400 hover:text-white font-medium text-sm transition-colors gap-1.5"
					>
						<Play className="h-4 w-4 text-[#00f2fe]" />
						Explore Live Interactive Demo
					</a>
				</div>

				{/* Interactive Live Platform Console Preview */}
				<div className="w-full mt-14 md:mt-20 border border-[#1e293b] rounded-2xl bg-[#0b0f19] shadow-[0_25px_60px_rgba(0,0,0,0.8)] overflow-hidden text-left">
					{/* Window Control Bar & Tab Switcher */}
					<div className="border-b border-[#1e293b] bg-[#0c1222] px-4 py-3 flex flex-wrap items-center justify-between gap-3">
						<div className="flex items-center gap-2">
							<div className="w-3 h-3 rounded-full bg-[#ef4444]/90" />
							<div className="w-3 h-3 rounded-full bg-[#f59e0b]/90" />
							<div className="w-3 h-3 rounded-full bg-[#10b981]/90" />
							<span className="text-xs font-mono text-slate-400 ml-2 hidden sm:inline">unifai-core-v1.1 // console</span>
						</div>

						{/* Console Mode Switcher */}
						<div className="flex items-center bg-[#07090e] p-1 rounded-lg border border-[#1e293b]">
							<button
								onClick={() => setConsoleTab("guard")}
								className={`px-3 py-1 text-xs font-semibold rounded-md transition-all flex items-center gap-1.5 cursor-pointer ${
									consoleTab === "guard"
										? "bg-[#00f2fe]/15 text-[#00f2fe] border border-[#00f2fe]/30"
										: "text-slate-400 hover:text-white"
								}`}
							>
								<Shield className="h-3.5 w-3.5" />
								Browser Guard DLP Active
							</button>
							<button
								onClick={() => setConsoleTab("gateway")}
								className={`px-3 py-1 text-xs font-semibold rounded-md transition-all flex items-center gap-1.5 cursor-pointer ${
									consoleTab === "gateway"
										? "bg-[#00f2fe]/15 text-[#00f2fe] border border-[#00f2fe]/30"
										: "text-slate-400 hover:text-white"
								}`}
							>
								<Zap className="h-3.5 w-3.5" />
								AI Gateway Proxy Engine
							</button>
						</div>
					</div>

					{/* Console Content Area */}
					{consoleTab === "guard" ? (
						<div className="p-5 md:p-7 space-y-6">
							<div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-[#1e293b]/70">
								<div className="flex items-center gap-3">
									<div className="h-9 w-9 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
										<Shield className="h-5 w-5" />
									</div>
									<div>
										<div className="flex items-center gap-2">
											<span className="font-semibold text-white text-sm sm:text-base">Real-Time Endpoint Interception</span>
											<Badge variant="outline" className="text-emerald-400 border-emerald-500/30 bg-emerald-500/10 text-[10px] font-mono">
												ONLINE (PAC :8085)
											</Badge>
										</div>
										<p className="text-xs text-slate-400">Target: <strong className="text-slate-200">grok.com</strong>, <strong className="text-slate-200">chatgpt.com</strong>, <strong className="text-slate-200">claude.ai</strong></p>
									</div>
								</div>
								<div className="text-right text-xs font-mono text-slate-400">
									<div>Latency Added: <span className="text-[#00f2fe] font-bold">0.7 ms</span></div>
									<div>Rule Engine: <span className="text-emerald-400 font-bold">PCI & Secrets Active</span></div>
								</div>
							</div>

							<div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
								<div className="bg-[#07090e] border border-[#1e293b] rounded-xl p-4 font-mono text-xs space-y-3">
									<div className="flex items-center justify-between text-slate-400 pb-2 border-b border-[#1e293b]">
										<span className="flex items-center gap-1.5 text-rose-400">
											<AlertTriangle className="h-3.5 w-3.5" />
											Employee Prompt in Browser (Raw Input)
										</span>
										<span className="text-[10px] text-slate-500">POST /rest/app-chat</span>
									</div>
									<div className="text-slate-300 leading-relaxed break-all">
										"Please analyze this quarterly cloud cost leak. AWS_SECRET=<span className="bg-rose-500/20 text-rose-300 px-1 py-0.5 rounded border border-rose-500/30 font-bold">AKIAIOSFODNN7EXAMPLE</span> and credit card for billing is <span className="bg-rose-500/20 text-rose-300 px-1 py-0.5 rounded border border-rose-500/30 font-bold">4532-8921-9982-1209</span>."
									</div>
								</div>

								<div className="bg-[#07090e] border border-[#00f2fe]/30 rounded-xl p-4 font-mono text-xs space-y-3 relative overflow-hidden">
									<div className="absolute top-0 right-0 w-24 h-24 bg-[#00f2fe]/5 rounded-full blur-xl pointer-events-none" />
									<div className="flex items-center justify-between text-slate-400 pb-2 border-b border-[#1e293b]">
										<span className="flex items-center gap-1.5 text-[#00f2fe]">
											<CheckCircle2 className="h-3.5 w-3.5" />
											Sanitized Payload Dispatched to LLM
										</span>
										<span className="text-[10px] font-bold text-amber-400 bg-amber-400/10 px-2 py-0.5 rounded border border-amber-400/30">
											ACTION: REDACTED
										</span>
									</div>
									<div className="text-slate-200 leading-relaxed break-all">
										"Please analyze this quarterly cloud cost leak. AWS_SECRET=<span className="bg-[#00f2fe]/20 text-[#00f2fe] px-1 py-0.5 rounded border border-[#00f2fe]/40 font-bold">[REDACTED_API_KEY]</span> and credit card for billing is <span className="bg-[#00f2fe]/20 text-[#00f2fe] px-1 py-0.5 rounded border border-[#00f2fe]/40 font-bold">[REDACTED_PCI_CARD]</span>."
									</div>
								</div>
							</div>

							<div className="flex flex-wrap items-center justify-between text-xs text-slate-400 font-mono bg-[#0c1222]/80 px-4 py-2.5 rounded-lg border border-[#1e293b]/80">
								<span>🛡️ Triggered: Rule #41 (Cloud API Credential) + Rule #104 (PCI-DSS PAN)</span>
								<span className="text-emerald-400 font-semibold">Audit Logged with Device ID #W10-ENT-883</span>
							</div>
						</div>
					) : (
						<div className="p-5 md:p-7 space-y-6">
							<div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-[#1e293b]/70">
								<div className="flex items-center gap-3">
									<div className="h-9 w-9 rounded-lg bg-[#00f2fe]/10 border border-[#00f2fe]/20 flex items-center justify-center text-[#00f2fe]">
										<Zap className="h-5 w-5" />
									</div>
									<div>
										<div className="flex items-center gap-2">
											<span className="font-semibold text-white text-sm sm:text-base">High-Performance LLM Gateway</span>
											<Badge variant="outline" className="text-[#00f2fe] border-[#00f2fe]/30 bg-[#00f2fe]/10 text-[10px] font-mono">
												100+ MODELS UNIFIED
											</Badge>
										</div>
										<p className="text-xs text-slate-400">Standard OpenAI Compatible Interface (HTTP / SSE Streams)</p>
									</div>
								</div>
								<div className="text-right text-xs font-mono text-slate-400">
									<div>Semantic Cache Hit Rate: <span className="text-emerald-400 font-bold">48.2%</span></div>
									<div>Estimated Monthly Savings: <span className="text-[#00f2fe] font-bold">$14,280</span></div>
								</div>
							</div>

							<div className="grid grid-cols-1 md:grid-cols-3 gap-4 font-mono text-xs">
								<div className="bg-[#07090e] border border-[#1e293b] p-4 rounded-xl space-y-2">
									<span className="text-slate-400 text-[11px] block">ACTIVE ROUTING</span>
									<div className="text-white font-bold text-sm flex items-center justify-between">
										<span>Claude 3.7 Sonnet</span>
										<span className="text-emerald-400 text-xs">Primary</span>
									</div>
									<div className="text-slate-400 text-[11px] pt-1">
										Fallback: OpenAI GPT-4o
									</div>
								</div>

								<div className="bg-[#07090e] border border-[#1e293b] p-4 rounded-xl space-y-2">
									<span className="text-slate-400 text-[11px] block">VIRTUAL KEY QUOTA</span>
									<div className="text-white font-bold text-sm flex items-center justify-between">
										<span>sk-unifai-prod-09</span>
										<span className="text-[#00f2fe] text-xs">82% Used</span>
									</div>
									<div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
										<div className="bg-[#00f2fe] h-full w-[82%]" />
									</div>
								</div>

								<div className="bg-[#07090e] border border-[#1e293b] p-4 rounded-xl space-y-2">
									<span className="text-slate-400 text-[11px] block">VECTOR CACHE ENGINE</span>
									<div className="text-emerald-400 font-bold text-sm flex items-center justify-between">
										<span>CACHE HIT (Zero Latency)</span>
										<span className="text-xs">$0.00</span>
									</div>
									<div className="text-slate-400 text-[11px]">
										PostgreSQL pgvector Semantic Match (0.94 score)
									</div>
								</div>
							</div>
						</div>
					)}
				</div>
			</section>

			{/* Enterprise Trust & Social Proof Metrics */}
			<section className="border-y border-[#1e293b]/70 bg-[#090d16]/70 py-12 px-6">
				<div className="max-w-7xl mx-auto">
					<div className="grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
						<div className="space-y-1">
							<div className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight bg-gradient-to-r from-white to-slate-300 bg-clip-text text-transparent">
								50M+
							</div>
							<div className="text-xs sm:text-sm text-slate-400 font-medium">Enterprise Prompts Protected</div>
						</div>

						<div className="space-y-1">
							<div className="text-3xl sm:text-4xl font-extrabold text-[#00f2fe] tracking-tight">
								&lt; 1.2ms
							</div>
							<div className="text-xs sm:text-sm text-slate-400 font-medium">Loopback Interception Overhead</div>
						</div>

						<div className="space-y-1">
							<div className="text-3xl sm:text-4xl font-extrabold text-emerald-400 tracking-tight">
								85%
							</div>
							<div className="text-xs sm:text-sm text-slate-400 font-medium">LLM Cost Reduction via Cache</div>
						</div>

						<div className="space-y-1">
							<div className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
								99.99%
							</div>
							<div className="text-xs sm:text-sm text-slate-400 font-medium">Guaranteed Enterprise Uptime</div>
						</div>
					</div>

					{/* Security Compliance Pills */}
					<div className="mt-10 pt-8 border-t border-[#1e293b]/50 flex flex-wrap items-center justify-center gap-3 text-xs text-slate-400">
						<span className="font-semibold text-slate-300">Enterprise Compliance & Security:</span>
						<span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#0f172a] border border-[#334155]/60 text-slate-300">
							<CheckCircle className="h-3 w-3 text-[#00f2fe]" /> SOC2 Type II Ready
						</span>
						<span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#0f172a] border border-[#334155]/60 text-slate-300">
							<CheckCircle className="h-3 w-3 text-[#00f2fe]" /> HIPAA Compliant
						</span>
						<span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#0f172a] border border-[#334155]/60 text-slate-300">
							<CheckCircle className="h-3 w-3 text-[#00f2fe]" /> GDPR / CCPA Ready
						</span>
						<span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#0f172a] border border-[#334155]/60 text-slate-300">
							<CheckCircle className="h-3 w-3 text-[#00f2fe]" /> Zero-Trust Network Architecture
						</span>
					</div>
				</div>
			</section>

			{/* Core Dual Product Pillars (Bento Grid) */}
			<section id="products" className="py-24 px-6 max-w-7xl mx-auto">
				<div className="text-center max-w-3xl mx-auto mb-16">
					<span className="text-xs font-bold font-mono tracking-widest text-[#00f2fe] uppercase bg-[#00f2fe]/10 px-3 py-1 rounded-full border border-[#00f2fe]/20">
						Two Pillars • One Unified Platform
					</span>
					<h2 className="text-3xl sm:text-5xl font-extrabold tracking-tight text-white mt-4 mb-4">
						Complete Coverage Across Endpoint & Cloud
					</h2>
					<p className="text-slate-400 text-base sm:text-lg">
						Whether an employee opens Grok in a browser or an engineer calls an LLM API from backend microservices, UnifAI governs, logs, and protects the interaction.
					</p>
				</div>

				<div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
					{/* Pillar 1: Browser Guard */}
					<div className="border border-[#1e293b] rounded-2xl bg-gradient-to-b from-[#0e1424] to-[#080c14] p-8 space-y-6 relative overflow-hidden group hover:border-[#00f2fe]/40 transition-all duration-300 shadow-xl">
						<div className="h-12 w-12 rounded-xl bg-[#00f2fe]/10 border border-[#00f2fe]/30 flex items-center justify-center text-[#00f2fe]">
							<Shield className="h-6 w-6" />
						</div>
						<div className="space-y-2">
							<div className="inline-flex items-center gap-2 text-xs font-mono font-semibold text-[#00f2fe]">
								<span>PILLAR 01</span> • <span>WINDOWS & MACOS AGENT</span>
							</div>
							<h3 className="text-2xl sm:text-3xl font-bold text-white">
								UnifAI Browser Guard
							</h3>
							<p className="text-slate-400 text-sm sm:text-base leading-relaxed">
								Endpoint AI Data Loss Prevention (DLP) deployed via MDM. Automatically monitors employee interactions with consumer and enterprise AI platforms.
							</p>
						</div>

						<div className="space-y-3 pt-2">
							{[
								{
									title: "Universal Chat Interception",
									desc: "Zero-latency prompt capture for Grok, ChatGPT, Claude, Gemini, Perplexity, and custom AI web apps."
								},
								{
									title: "In-Flight Data Redaction & Blocking",
									desc: "Sanitize API keys, credit cards, SSNs, and passwords before packets leave the local workstation."
								},
								{
									title: "Multi-File Upload & Voice DLP",
									desc: "Inspect attached documents (PDFs, CSVs) and audio prompts seamlessly before AI ingestion."
								},
								{
									title: "Centralized Policy Distribution",
									desc: "Sync compliance rules and target website policies across your entire fleet in seconds."
								}
							].map((item, idx) => (
								<div key={idx} className="flex items-start gap-3 bg-[#07090e]/50 p-3.5 rounded-xl border border-[#1e293b]/60">
									<CheckCircle className="h-5 w-5 text-[#00f2fe] shrink-0 mt-0.5" />
									<div>
										<h4 className="text-sm font-semibold text-white">{item.title}</h4>
										<p className="text-xs text-slate-400 mt-0.5">{item.desc}</p>
									</div>
								</div>
							))}
						</div>

						<div className="pt-2">
							<button
								onClick={() => setIsDemoModalOpen(true)}
								className="text-xs font-semibold text-[#00f2fe] hover:underline flex items-center gap-1.5 cursor-pointer"
							>
								Schedule Browser Guard Fleet Demo <ArrowRight className="h-3.5 w-3.5" />
							</button>
						</div>
					</div>

					{/* Pillar 2: AI Gateway */}
					<div className="border border-[#1e293b] rounded-2xl bg-gradient-to-b from-[#0e1424] to-[#080c14] p-8 space-y-6 relative overflow-hidden group hover:border-[#00f2fe]/40 transition-all duration-300 shadow-xl">
						<div className="h-12 w-12 rounded-xl bg-[#4facfe]/10 border border-[#4facfe]/30 flex items-center justify-center text-[#4facfe]">
							<Zap className="h-6 w-6" />
						</div>
						<div className="space-y-2">
							<div className="inline-flex items-center gap-2 text-xs font-mono font-semibold text-[#4facfe]">
								<span>PILLAR 02</span> • <span>DEVELOPER & CLOUD GATEWAY</span>
							</div>
							<h3 className="text-2xl sm:text-3xl font-bold text-white">
								UnifAI AI Gateway
							</h3>
							<p className="text-slate-400 text-sm sm:text-base leading-relaxed">
								A lightning-fast, unified reverse proxy for your applications. Replace dozens of provider SDKs with one resilient, observable control plane.
							</p>
						</div>

						<div className="space-y-3 pt-2">
							{[
								{
									title: "1-Line OpenAI Drop-in SDK",
									desc: "Switch provider endpoints with zero codebase refactoring. Works with Python, Node.js, Go, and cURL."
								},
								{
									title: "Semantic Vector Caching",
									desc: "Cut API bills by up to 85% by caching semantically identical prompts using high-speed vector embeddings."
								},
								{
									title: "Virtual Keys & Team Budgets",
									desc: "Issue scoped API keys with strict monthly spend limits, token quotas, and model restrictions."
								},
								{
									title: "Smart Fallbacks & Load Balancing",
									desc: "Automatic failover across providers to prevent 502/503 rate limit downtime during peak traffic."
								}
							].map((item, idx) => (
								<div key={idx} className="flex items-start gap-3 bg-[#07090e]/50 p-3.5 rounded-xl border border-[#1e293b]/60">
									<CheckCircle className="h-5 w-5 text-[#4facfe] shrink-0 mt-0.5" />
									<div>
										<h4 className="text-sm font-semibold text-white">{item.title}</h4>
										<p className="text-xs text-slate-400 mt-0.5">{item.desc}</p>
									</div>
								</div>
							))}
						</div>

						<div className="pt-2">
							<button
								onClick={() => setIsDemoModalOpen(true)}
								className="text-xs font-semibold text-[#4facfe] hover:underline flex items-center gap-1.5 cursor-pointer"
							>
								Schedule Gateway Architecture Demo <ArrowRight className="h-3.5 w-3.5" />
							</button>
						</div>
					</div>
				</div>
			</section>

			{/* Interactive Live DLP Tester / Sandbox Section */}
			<section id="simulator" className="py-24 px-6 border-y border-[#1e293b]/70 bg-[#090e18]/80">
				<div className="max-w-7xl mx-auto">
					<div className="text-center max-w-3xl mx-auto mb-14">
						<span className="text-xs font-bold font-mono tracking-widest text-emerald-400 uppercase bg-emerald-400/10 px-3 py-1 rounded-full border border-emerald-400/20">
							Interactive Sandbox
						</span>
						<h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-white mt-4 mb-3">
							Test Prompt Guardrails Live
						</h2>
						<p className="text-slate-400 text-sm sm:text-base">
							Select a scenario below or type your own test prompt to see how UnifAI Browser Guard identifies threats, applies redaction, and halts corporate data leaks in real-time.
						</p>

						{/* Presets */}
						<div className="flex flex-wrap items-center justify-center gap-2 mt-6">
							{samplePrompts.map((preset) => (
								<button
									key={preset.id}
									onClick={() => {
										setSelectedSample(preset);
										setCustomPrompt(preset.raw);
									}}
									className={`text-xs font-medium px-3.5 py-1.5 rounded-lg border transition-all cursor-pointer ${
										selectedSample.id === preset.id
											? "border-[#00f2fe] bg-[#00f2fe]/10 text-white font-semibold shadow-[0_0_12px_rgba(0,242,254,0.2)]"
											: "border-[#1e293b] bg-[#0c1222] text-slate-400 hover:text-white"
									}`}
								>
									{preset.title}
								</button>
							))}
						</div>
					</div>

					{/* Live Simulator View */}
					<div className="border border-[#1e293b] rounded-2xl bg-[#070a12] p-6 sm:p-8 grid grid-cols-1 lg:grid-cols-2 gap-8 shadow-2xl">
						{/* Input Box */}
						<div className="space-y-4">
							<div className="flex items-center justify-between">
								<label className="text-sm font-semibold text-slate-200 flex items-center gap-2">
									<Terminal className="h-4 w-4 text-[#00f2fe]" />
									Interactive User Input
								</label>
								<span className="text-xs text-slate-500 font-mono">Simulating Browser Chat Box</span>
							</div>

							<textarea
								value={customPrompt}
								onChange={(e) => setCustomPrompt(e.target.value)}
								rows={7}
								className="w-full bg-[#0d1322] border border-[#1e293b] rounded-xl p-4 text-slate-200 font-mono text-xs sm:text-sm focus:outline-none focus:border-[#00f2fe] transition-colors leading-relaxed resize-none"
								placeholder="Type or paste any sensitive prompt here..."
							/>

							<div className="flex items-center justify-between text-xs text-slate-400">
								<span>Target Engine: <strong className="text-white">Grok / ChatGPT Web</strong></span>
								<button
									onClick={() => setCustomPrompt(selectedSample.raw)}
									className="text-[#00f2fe] hover:underline flex items-center gap-1 cursor-pointer"
								>
									<RefreshCw className="h-3 w-3" /> Reset to preset
								</button>
							</div>
						</div>

						{/* Output Result */}
						<div className="space-y-4 bg-[#0a0f1d] border border-[#1e293b] rounded-xl p-5 flex flex-col justify-between">
							<div className="space-y-3">
								<div className="flex items-center justify-between pb-3 border-b border-[#1e293b]">
									<span className="text-xs font-mono font-semibold text-slate-300">SECURITY ACTION APPLIED</span>
									<span className={`text-xs font-mono font-bold px-2.5 py-1 rounded-md border ${selectedSample.actionColor}`}>
										{selectedSample.action}
									</span>
								</div>

								<div className="space-y-1">
									<span className="text-[11px] font-mono text-slate-400">TRIGGERED POLICY:</span>
									<div className="text-xs sm:text-sm font-semibold text-white flex items-center gap-2">
										<Shield className="h-4 w-4 text-[#00f2fe]" />
										{selectedSample.policy}
									</div>
								</div>

								<div className="space-y-1 pt-2">
									<span className="text-[11px] font-mono text-slate-400">SANITIZED PAYLOAD FORWARDED:</span>
									<div className="bg-[#07090e] border border-[#1e293b] rounded-lg p-3.5 font-mono text-xs text-slate-300 break-all leading-relaxed max-h-36 overflow-y-auto">
										{selectedSample.redacted}
									</div>
								</div>
							</div>

							<div className="pt-3 border-t border-[#1e293b] flex items-center justify-between text-xs font-mono text-slate-400">
								<span>Interception: <strong className="text-emerald-400">0.6 ms</strong></span>
								<span>Compliance Log: <strong className="text-[#00f2fe]">Stored in Audit Trail</strong></span>
							</div>
						</div>
					</div>
				</div>
			</section>

			{/* Feature Deep Dive Grid */}
			<section id="features" className="py-24 px-6 max-w-7xl mx-auto">
				<div className="text-center max-w-3xl mx-auto mb-16">
					<h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-white mb-4">
						Everything Enterprise IT & Security Demands
					</h2>
					<p className="text-slate-400 text-lg">
						Engineered from the ground up for high reliability, zero data leakage, and friction-free employee adoption.
					</p>
				</div>

				<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
					{[
						{
							icon: <Lock className="h-5 w-5 text-[#00f2fe]" />,
							title: "Zero-Trust Architecture",
							desc: "No sensitive plaintext ever leaves your local network uninspected. Policies execute on-device or within your private cluster."
						},
						{
							icon: <Database className="h-5 w-5 text-[#00f2fe]" />,
							title: "Semantic Vector Cache",
							desc: "Vectorized embeddings match duplicate or semantically equivalent questions, serving cached replies at zero cost."
						},
						{
							icon: <Key className="h-5 w-5 text-[#00f2fe]" />,
							title: "Virtual Keys & Team Budgets",
							desc: "Provision dedicated API keys for teams, projects, or applications with hard dollar caps and rate limits."
						},
						{
							icon: <Laptop className="h-5 w-5 text-[#00f2fe]" />,
							title: "Multi-Platform Agents",
							desc: "Single lightweight binary for Windows and macOS. Silent MSI/PKG installations compatible with Jamf and Intune."
						},
						{
							icon: <Activity className="h-5 w-5 text-[#00f2fe]" />,
							title: "Comprehensive Audit Trail",
							desc: "Granular logging of all AI activity across your company, including prompt contents, timestamps, and model costs."
						},
						{
							icon: <Cpu className="h-5 w-5 text-[#00f2fe]" />,
							title: "Model Context Protocol (MCP)",
							desc: "First-class support for connected MCP servers, enabling secure tool execution and internal database querying."
						}
					].map((feature, idx) => (
						<div
							key={idx}
							className="border border-[#1e293b] rounded-xl bg-[#0c101c]/70 p-6 hover:border-[#00f2fe]/40 transition-all hover:-translate-y-1 duration-200"
						>
							<div className="h-10 w-10 rounded-lg bg-[#00f2fe]/10 border border-[#00f2fe]/20 flex items-center justify-center mb-4">
								{feature.icon}
							</div>
							<h3 className="text-lg font-bold text-white mb-2">{feature.title}</h3>
							<p className="text-slate-400 text-sm leading-relaxed">{feature.desc}</p>
						</div>
					))}
				</div>
			</section>

			{/* Comparison Table */}
			<section id="comparison" className="py-20 px-6 border-t border-[#1e293b]/70 bg-[#090d16]/70">
				<div className="max-w-7xl mx-auto">
					<div className="text-center max-w-3xl mx-auto mb-14">
						<span className="text-xs font-bold font-mono tracking-widest text-[#00f2fe] uppercase bg-[#00f2fe]/10 px-3 py-1 rounded-full border border-[#00f2fe]/20">
							Head to Head Comparison
						</span>
						<h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-white mt-4 mb-3">
							Why Enterprises Choose UnifAI
						</h2>
						<p className="text-slate-400 text-sm sm:text-base">
							See how UnifAI combines endpoint web AI DLP with high-performance gateway infrastructure where legacy tools fall short.
						</p>
					</div>

					<div className="border border-[#1e293b] rounded-2xl bg-[#07090e] overflow-hidden overflow-x-auto shadow-2xl">
						<table className="w-full text-left border-collapse text-sm">
							<thead>
								<tr className="border-b border-[#1e293b] bg-[#0c1222]">
									<th className="p-4 sm:p-5 font-bold text-white">Platform Capability</th>
									<th className="p-4 sm:p-5 font-bold text-[#00f2fe] bg-[#00f2fe]/5 border-x border-[#00f2fe]/20">
										UnifAI Platform
									</th>
									<th className="p-4 sm:p-5 font-semibold text-slate-400">Legacy API Proxies</th>
									<th className="p-4 sm:p-5 font-semibold text-slate-400">Raw Provider APIs</th>
								</tr>
							</thead>
							<tbody className="divide-y divide-[#1e293b]/60">
								{[
									{
										feature: "Desktop Browser Guard (Grok, ChatGPT, Claude DLP)",
										unifai: "Full Support (Win & Mac)",
										legacy: "None (API only)",
										raw: "None"
									},
									{
										feature: "In-Flight Prompt Redaction & Blocking",
										unifai: "Real-time (< 1.2ms)",
										legacy: "Heavy regex latency",
										raw: "None"
									},
									{
										feature: "Multi-File Upload & Voice Audio DLP",
										unifai: "Automated OCR & Parsers",
										legacy: "None",
										raw: "None"
									},
									{
										feature: "Semantic Vector Caching",
										unifai: "Built-in pgvector (85% savings)",
										legacy: "Basic Exact Match Only",
										raw: "None"
									},
									{
										feature: "Unified 1-Line Drop-in SDK Migration",
										unifai: "OpenAI Compatible BaseURL",
										legacy: "Complex Custom Gateways",
										raw: "Separate SDK per vendor"
									},
									{
										feature: "Virtual Keys, Quotas & Token Spend Caps",
										unifai: "Centralized Admin UI",
										legacy: "Rudimentary Rate Limits",
										raw: "Billing account level only"
									},
									{
										feature: "Self-Hostable (Air-Gapped / Private VPC)",
										unifai: "100% Self-Contained",
										legacy: "Vendor Lock-in Cloud",
										raw: "Cloud Only"
									}
								].map((row, idx) => (
									<tr key={idx} className="hover:bg-slate-900/40 transition-colors">
										<td className="p-4 sm:p-5 font-medium text-white">{row.feature}</td>
										<td className="p-4 sm:p-5 font-semibold text-[#00f2fe] bg-[#00f2fe]/5 border-x border-[#00f2fe]/20 flex items-center gap-1.5">
											<CheckCircle2 className="h-4 w-4 text-[#00f2fe] shrink-0" />
											{row.unifai}
										</td>
										<td className="p-4 sm:p-5 text-slate-400">{row.legacy}</td>
										<td className="p-4 sm:p-5 text-slate-400">{row.raw}</td>
									</tr>
								))}
							</tbody>
						</table>
					</div>
				</div>
			</section>

			{/* One-Line Code Integration Explorer */}
			<section id="code" className="py-24 px-6 max-w-7xl mx-auto">
				<div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
					<div className="space-y-6">
						<span className="text-xs font-bold font-mono tracking-widest text-[#00f2fe] uppercase bg-[#00f2fe]/10 px-3 py-1 rounded-full border border-[#00f2fe]/20">
							Developer Simplicity
						</span>
						<h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-white leading-tight">
							One Line of Code to Protect & Unify Everything
						</h2>
						<p className="text-slate-400 text-base sm:text-lg leading-relaxed">
							UnifAI mirrors the standard OpenAI API specification. You never have to rewrite your application logic or re-train your engineers. Simply swap your baseURL.
						</p>

						<div className="space-y-3 pt-2">
							{[
								"100% Drop-in replacement for OpenAI SDKs",
								"Dynamic model swapping across Anthropic, Google, and xAI",
								"Seamless silent deployment script for endpoint Browser Guard"
							].map((item, idx) => (
								<div key={idx} className="flex items-center gap-3">
									<CheckCircle className="h-5 w-5 text-[#00f2fe] shrink-0" />
									<span className="text-sm font-medium text-white">{item}</span>
								</div>
							))}
						</div>

						<div className="pt-3">
							<button
								onClick={() => setIsDemoModalOpen(true)}
								className="text-sm font-semibold text-white bg-[#1e293b] hover:bg-[#334155] border border-[#334155] px-5 py-2.5 rounded-lg transition-all flex items-center gap-2 cursor-pointer"
							>
								<Calendar className="h-4 w-4 text-[#00f2fe]" />
								Request Guided Implementation Call
							</button>
						</div>
					</div>

					{/* Code Box */}
					<div className="border border-[#1e293b] rounded-xl bg-[#090e1a] overflow-hidden shadow-2xl">
						<div className="flex bg-[#060a12] border-b border-[#1e293b] px-4 py-2.5 justify-between items-center">
							<div className="flex gap-1.5">
								<button
									onClick={() => setCodeTab("python")}
									className={`text-xs font-semibold px-3 py-1.5 rounded-md transition-colors cursor-pointer ${
										codeTab === "python" ? "bg-[#1e293b] text-white" : "text-slate-400 hover:text-white"
									}`}
								>
									Python SDK
								</button>
								<button
									onClick={() => setCodeTab("node")}
									className={`text-xs font-semibold px-3 py-1.5 rounded-md transition-colors cursor-pointer ${
										codeTab === "node" ? "bg-[#1e293b] text-white" : "text-slate-400 hover:text-white"
									}`}
								>
									Node.js
								</button>
								<button
									onClick={() => setCodeTab("curl")}
									className={`text-xs font-semibold px-3 py-1.5 rounded-md transition-colors cursor-pointer ${
										codeTab === "curl" ? "bg-[#1e293b] text-white" : "text-slate-400 hover:text-white"
									}`}
								>
									cURL
								</button>
								<button
									onClick={() => setCodeTab("guard")}
									className={`text-xs font-semibold px-3 py-1.5 rounded-md transition-colors cursor-pointer ${
										codeTab === "guard" ? "bg-[#00f2fe]/20 text-[#00f2fe] border border-[#00f2fe]/30" : "text-slate-400 hover:text-white"
									}`}
								>
									Browser Guard
								</button>
							</div>

							<button
								onClick={() => handleCopyCode(codeExamples[codeTab])}
								className="text-xs text-slate-400 hover:text-white flex items-center gap-1 font-mono p-1 cursor-pointer"
								title="Copy code"
							>
								{copiedCode ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
								<span>{copiedCode ? "Copied" : "Copy"}</span>
							</button>
						</div>

						<div className="p-5 overflow-x-auto text-[13px] font-mono leading-relaxed bg-[#070b14] text-slate-300 max-h-[340px]">
							<pre className="whitespace-pre">{codeExamples[codeTab]}</pre>
						</div>
					</div>
				</div>
			</section>

			{/* Enterprise FAQ Section */}
			<section className="py-20 px-6 border-t border-[#1e293b]/70 bg-[#090d16]/70">
				<div className="max-w-4xl mx-auto">
					<div className="text-center mb-14">
						<span className="text-xs font-bold font-mono tracking-widest text-[#00f2fe] uppercase bg-[#00f2fe]/10 px-3 py-1 rounded-full border border-[#00f2fe]/20">
							Got Questions?
						</span>
						<h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-white mt-4 mb-3">
							Frequently Asked Questions
						</h2>
						<p className="text-slate-400 text-sm sm:text-base">
							Everything you need to know about UnifAI deployment, compliance, and DLP architecture.
						</p>
					</div>

					<div className="space-y-4">
						{faqs.map((faq, idx) => (
							<div
								key={idx}
								className="border border-[#1e293b] rounded-xl bg-[#0c1222]/80 overflow-hidden transition-all"
							>
								<button
									onClick={() => setOpenFaq(openFaq === idx ? null : idx)}
									className="w-full p-5 text-left font-semibold text-white flex items-center justify-between gap-4 hover:text-[#00f2fe] transition-colors cursor-pointer"
								>
									<span>{faq.q}</span>
									<span className="text-slate-400 shrink-0">
										{openFaq === idx ? <X className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
									</span>
								</button>
								{openFaq === idx && (
									<div className="px-5 pb-5 text-sm text-slate-300 leading-relaxed border-t border-[#1e293b]/50 pt-3">
										{faq.a}
									</div>
								)}
							</div>
						))}
					</div>
				</div>
			</section>

			{/* High-Impact Call to Action Banner */}
			<section className="py-24 px-6 text-center relative overflow-hidden bg-gradient-to-b from-[#0a0f1d] to-[#07090e] border-t border-[#1e293b]">
				<div className="absolute inset-0 bg-gradient-to-r from-[#00f2fe]/5 via-transparent to-[#4facfe]/5 pointer-events-none" />
				<div className="max-w-4xl mx-auto space-y-6 relative z-10">
					<h2 className="text-3xl sm:text-5xl font-extrabold tracking-tight text-white leading-tight">
						Ready to Secure and Standardize <br />
						Your Enterprise AI Fleet?
					</h2>
					<p className="text-slate-400 text-lg max-w-2xl mx-auto">
						Start running the UnifAI Gateway in production or deploy Browser Guard to your endpoints in minutes.
					</p>

					<div className="pt-4 flex flex-col sm:flex-row items-center gap-4 justify-center">
						<button
							onClick={() => setIsDemoModalOpen(true)}
							className="w-full sm:w-auto h-12 px-8 bg-gradient-to-r from-[#00f2fe] to-[#4facfe] text-[#07090e] hover:brightness-110 font-bold rounded-xl text-base shadow-[0_0_25px_rgba(0,242,254,0.3)] transition-all hover:scale-[1.02] flex items-center justify-center gap-2 cursor-pointer"
						>
							<Calendar className="h-5 w-5" />
							Schedule a Live Demo
						</button>

						{isLoggedIn ? (
							<Button
								onClick={() => navigate({ to: "/workspace" })}
								className="w-full sm:w-auto h-12 px-8 bg-[#0f172a] hover:bg-[#1e293b] border border-[#334155] text-white font-semibold rounded-xl text-base"
							>
								Go to Dashboard
							</Button>
						) : (
							<Button
								onClick={() => navigate({ to: "/signup" })}
								className="w-full sm:w-auto h-12 px-8 bg-[#0f172a] hover:bg-[#1e293b] border border-[#334155] text-white font-semibold rounded-xl text-base"
							>
								Create Free Account
							</Button>
						)}
					</div>
				</div>
			</section>

			{/* Comprehensive Footer */}
			<footer className="border-t border-[#1e293b] bg-[#05070c] py-14 px-6">
				<div className="max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-4 gap-10 text-sm text-slate-400 mb-12">
					<div className="space-y-4 md:col-span-1">
						<div className="flex items-center gap-3">
							<img src={companyLogoSrc} alt={companyFullName} className="h-8 w-auto object-contain" />
							<span className="font-extrabold text-white text-base">{productName}</span>
						</div>
						<p className="text-xs text-slate-400 leading-relaxed">
							Enterprise AI Security, Endpoint DLP Browser Guard, and High-Throughput Universal AI Gateway.
						</p>
						<div className="flex items-center gap-2 text-xs text-emerald-400 font-mono">
							<span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
							All Systems Operational
						</div>
					</div>

					<div>
						<h4 className="font-semibold text-white text-sm mb-3">Products & Solutions</h4>
						<ul className="space-y-2 text-xs">
							<li><a href="#products" className="hover:text-[#00f2fe] transition-colors">Browser Guard (Win & Mac)</a></li>
							<li><a href="#products" className="hover:text-[#00f2fe] transition-colors">Universal AI Gateway</a></li>
							<li><a href="#simulator" className="hover:text-[#00f2fe] transition-colors">Real-Time DLP Sandbox</a></li>
							<li><a href="#features" className="hover:text-[#00f2fe] transition-colors">Semantic Vector Caching</a></li>
							<li><a href="#features" className="hover:text-[#00f2fe] transition-colors">Virtual Keys & Budgets</a></li>
						</ul>
					</div>

					<div>
						<h4 className="font-semibold text-white text-sm mb-3">Resources & Docs</h4>
						<ul className="space-y-2 text-xs">
							<li><a href={DOCS.home} target="_blank" rel="noopener noreferrer" className="hover:text-[#00f2fe] transition-colors">Documentation</a></li>
							<li><a href={DOCS.architecture} target="_blank" rel="noopener noreferrer" className="hover:text-[#00f2fe] transition-colors">System Architecture</a></li>
							<li><a href="#code" className="hover:text-[#00f2fe] transition-colors">API Reference & Quickstart</a></li>
							<li><a href={DOCS.mcp} target="_blank" rel="noopener noreferrer" className="hover:text-[#00f2fe] transition-colors">Model Context Protocol (MCP)</a></li>
						</ul>
					</div>

					<div>
						<h4 className="font-semibold text-white text-sm mb-3">Enterprise Engagement</h4>
						<ul className="space-y-2 text-xs">
							<li>
								<button onClick={() => setIsDemoModalOpen(true)} className="text-[#00f2fe] hover:underline flex items-center gap-1 cursor-pointer">
									<Calendar className="h-3 w-3" /> Book an Architecture Demo
								</button>
							</li>
							<li><a href={`mailto:support@${companyFullName.toLowerCase().replace(/[^a-z0-9]/g, '')}.com`} className="hover:text-[#00f2fe] transition-colors">Contact Support</a></li>
							<li><span className="text-slate-400">SOC2 Type II • HIPAA • Zero-Trust</span></li>
						</ul>
					</div>
				</div>

				<div className="max-w-7xl mx-auto pt-8 border-t border-[#1e293b]/60 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-500">
					<div>&copy; 2026 {companyFullName}. All rights reserved.</div>
					<div className="flex items-center gap-4">
						<span>Privacy Policy</span>
						<span>Terms of Service</span>
						<span>Security Whitepaper</span>
					</div>
				</div>
			</footer>

			{/* Interactive "Book a Demo" Modal */}
			<Dialog open={isDemoModalOpen} onOpenChange={setIsDemoModalOpen}>
				<DialogContent className="bg-[#0b0f19] border border-[#1e293b] text-slate-200 sm:max-w-lg p-6 shadow-2xl">
					<DialogHeader>
						<DialogTitle className="text-xl font-bold text-white flex items-center gap-2">
							<Calendar className="h-5 w-5 text-[#00f2fe]" />
							Schedule an Enterprise Demo
						</DialogTitle>
						<DialogDescription className="text-slate-400 text-xs">
							Speak with a security engineer and see UnifAI Browser Guard and AI Gateway live in action tailored to your architecture.
						</DialogDescription>
					</DialogHeader>

					{demoSubmitted ? (
						<div className="py-8 text-center space-y-4">
							<div className="h-14 w-14 rounded-full bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 mx-auto">
								<CheckCircle2 className="h-8 w-8" />
							</div>
							<div className="space-y-1.5">
								<h3 className="text-lg font-bold text-white">Demo Request Received!</h3>
								<p className="text-xs text-slate-400 max-w-sm mx-auto leading-relaxed">
									Thank you, <strong className="text-slate-200">{demoForm.fullName}</strong>. A member of our enterprise engineering team has sent an invitation to <strong className="text-slate-200">{demoForm.email}</strong>.
								</p>
							</div>
							<div className="pt-2">
								<Button
									onClick={resetDemoModal}
									className="bg-gradient-to-r from-[#00f2fe] to-[#4facfe] text-[#07090e] font-bold text-xs h-9 px-5"
								>
									Done
								</Button>
							</div>
						</div>
					) : (
						<form onSubmit={handleDemoSubmit} className="space-y-4 mt-2">
							<div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
								<div className="space-y-1.5">
									<label className="text-xs font-medium text-slate-300">Your Full Name *</label>
									<Input
										required
										placeholder="e.g. Sarah Connor"
										value={demoForm.fullName}
										onChange={(e) => setDemoForm({ ...demoForm, fullName: e.target.value })}
										className="bg-[#070a12] border-[#1e293b] text-white text-xs h-9 focus:border-[#00f2fe]"
									/>
								</div>

								<div className="space-y-1.5">
									<label className="text-xs font-medium text-slate-300">Work Email *</label>
									<Input
										type="email"
										required
										placeholder="sarah@company.com"
										value={demoForm.email}
										onChange={(e) => setDemoForm({ ...demoForm, email: e.target.value })}
										className="bg-[#070a12] border-[#1e293b] text-white text-xs h-9 focus:border-[#00f2fe]"
									/>
								</div>
							</div>

							<div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
								<div className="space-y-1.5">
									<label className="text-xs font-medium text-slate-300">Company Name</label>
									<Input
										placeholder="Acme Corp"
										value={demoForm.company}
										onChange={(e) => setDemoForm({ ...demoForm, company: e.target.value })}
										className="bg-[#070a12] border-[#1e293b] text-white text-xs h-9 focus:border-[#00f2fe]"
									/>
								</div>

								<div className="space-y-1.5">
									<label className="text-xs font-medium text-slate-300">Team / Fleet Size</label>
									<select
										value={demoForm.teamSize}
										onChange={(e) => setDemoForm({ ...demoForm, teamSize: e.target.value })}
										className="w-full bg-[#070a12] border border-[#1e293b] text-white text-xs h-9 rounded-md px-2.5 focus:outline-none focus:border-[#00f2fe]"
									>
										<option value="1-50">1 - 50 Employees</option>
										<option value="50-250">50 - 250 Employees</option>
										<option value="250-1000">250 - 1,000 Employees</option>
										<option value="1000+">1,000+ Enterprise Fleet</option>
									</select>
								</div>
							</div>

							<div className="space-y-1.5">
								<label className="text-xs font-medium text-slate-300">Primary Product Interest</label>
								<div className="grid grid-cols-3 gap-2 text-xs">
									{[
										{ id: "guard", label: "Browser Guard DLP" },
										{ id: "gateway", label: "AI Gateway Hub" },
										{ id: "both", label: "Both Solutions" },
									].map((opt) => (
										<button
											type="button"
											key={opt.id}
											onClick={() => setDemoForm({ ...demoForm, interest: opt.id })}
											className={`py-2 px-2 text-center rounded-lg border font-medium transition-all cursor-pointer ${
												demoForm.interest === opt.id
													? "border-[#00f2fe] bg-[#00f2fe]/15 text-[#00f2fe]"
													: "border-[#1e293b] bg-[#070a12] text-slate-400 hover:text-white"
											}`}
										>
											{opt.label}
										</button>
									))}
								</div>
							</div>

							<div className="space-y-1.5">
								<label className="text-xs font-medium text-slate-300">Notes / Specific AI Security Requirements (Optional)</label>
								<textarea
									rows={2}
									placeholder="e.g. Need to protect employee ChatGPT usage & migrate from OpenAI to Claude with semantic caching..."
									value={demoForm.notes}
									onChange={(e) => setDemoForm({ ...demoForm, notes: e.target.value })}
									className="w-full bg-[#070a12] border border-[#1e293b] rounded-lg p-2.5 text-white text-xs focus:outline-none focus:border-[#00f2fe] resize-none"
								/>
							</div>

							<div className="pt-2 flex items-center justify-end gap-2">
								<Button
									type="button"
									variant="ghost"
									onClick={() => setIsDemoModalOpen(false)}
									className="text-xs h-9 text-slate-400 hover:text-white"
								>
									Cancel
								</Button>
								<Button
									type="submit"
									className="bg-gradient-to-r from-[#00f2fe] to-[#4facfe] text-[#07090e] font-bold text-xs h-9 px-5 shadow-[0_0_15px_rgba(0,242,254,0.3)] hover:brightness-110"
								>
									Confirm Demo Booking
								</Button>
							</div>
						</form>
					)}
				</DialogContent>
			</Dialog>
		</div>
	);
}
