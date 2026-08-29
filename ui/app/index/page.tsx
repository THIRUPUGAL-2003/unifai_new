import { Button } from "@/components/ui/button";
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
	ExternalLink,
	Menu,
	X
} from "lucide-react";
import { useEffect, useState } from "react";
import { getApiBaseUrl } from "@/lib/utils/port";

export default function LandingPage() {
	const [isLoggedIn, setIsLoggedIn] = useState(false);
	const [activeTab, setActiveTab] = useState<"curl" | "python" | "node">("curl");
	const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
	const navigate = useNavigate();

	useEffect(() => {
		// Check if the user is already authenticated
		fetch(`${getApiBaseUrl()}/session/is-auth-enabled`, {
			credentials: "include",
		})
			.then((res) => (res.ok ? res.json() : null))
			.then((data) => {
				if (data && (!data.is_auth_enabled || data.has_valid_token)) {
					setIsLoggedIn(true);
				}
			})
			.catch(() => {
				// Ignore errors, default to false
			});
	}, []);

	const codeExamples = {
		curl: `curl -X POST http://localhost:8080/v1/chat/completions \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer sk-UnifAI-key" \\
  -d '{
    "model": "openai/gpt-4o",
    "messages": [
      {
        "role": "user",
        "content": "List files in the workspace"
      }
    ]
  }'`,
		python: `from openai import OpenAI

# Simply change the base_url to point to UnifAI
client = OpenAI(
    base_url="http://localhost:8080/v1",
    api_key="sk-UnifAI-key"
)

response = client.chat.completions.create(
    model="openai/gpt-4o",
    messages=[{"role": "user", "content": "List files in the workspace"}]
)
print(response.choices[0].message.content)`,
		node: `import OpenAI from "openai";

// Simply change the baseURL to point to UnifAI
const openai = new OpenAI({
  baseURL: "http://localhost:8080/v1",
  apiKey: "sk-UnifAI-key"
});

const response = await openai.chat.completions.create({
  model: "openai/gpt-4o",
  messages: [{ role: "user", content: "List files in the workspace" }]
});
console.log(response.choices[0].message.content);`
	};

	const companyLogoSrc = "/yes-panchi-logo.png";
	const companyName = "YesPanchi";
	const companyFullName = "YesPanchi Group of Companies";

	return (
		<div className="bg-[#0b0c10] text-[#c5c6c7] min-h-screen font-sans selection:bg-[#45f3ff]/30 selection:text-white overflow-x-hidden">
			{/* Top glow effects */}
			<div className="absolute top-0 left-1/4 w-[500px] h-[500px] bg-[#1f2833]/30 rounded-full blur-[120px] pointer-events-none -translate-y-1/2" />
			<div className="absolute top-0 right-1/4 w-[400px] h-[400px] bg-[#45f3ff]/5 rounded-full blur-[100px] pointer-events-none -translate-y-1/2" />

			{/* Navbar */}
			<nav className="sticky top-0 z-50 border-b border-[#1f2833]/60 bg-[#0b0c10]/80 backdrop-blur-md transition-all duration-300">
				<div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
					<div className="flex items-center gap-3">
						<div className="flex h-9 w-9 items-center justify-center overflow-hidden rounded-lg border border-[#c5a962]/30 bg-[#0b0c10] shadow-[0_0_15px_rgba(197,169,98,0.2)]">
							<img src={companyLogoSrc} alt="" className="h-full w-full object-contain p-0.5" />
						</div>
						<span className="text-xl font-bold tracking-tight text-white">{companyName}</span>
					</div>

					{/* Desktop Nav */}
					<div className="hidden md:flex items-center gap-8 text-sm font-medium">
						<a href="#features" className="hover:text-[#45f3ff] transition-colors">Features</a>
						<a href="#code" className="hover:text-[#45f3ff] transition-colors">Quickstart</a>
						<a href="#architecture" className="hover:text-[#45f3ff] transition-colors">Architecture</a>
						<a href="/workspace/docs" className="hover:text-[#45f3ff] transition-colors flex items-center gap-1">
							Docs <ExternalLink className="h-3 w-3" />
						</a>
					</div>

					<div className="hidden md:flex items-center gap-4">
						{isLoggedIn ? (
							<Button
								onClick={() => navigate({ to: "/workspace" })}
								className="bg-[#45f3ff] text-[#0b0c10] hover:bg-[#45f3ff]/90 font-semibold shadow-[0_0_15px_rgba(69,243,255,0.25)] rounded-md h-9 px-5 transition-all hover:scale-[1.02]"
							>
								Go to Workspace
							</Button>
						) : (
							<>
								<Link to="/login" className="text-sm font-semibold hover:text-[#45f3ff] transition-colors px-3 py-1.5">
									Sign In
								</Link>
								<Button
									onClick={() => navigate({ to: "/signup" })}
									className="bg-transparent text-white border border-[#45f3ff] hover:bg-[#45f3ff]/10 font-semibold rounded-md h-9 px-5 transition-all"
								>
									Sign Up
								</Button>
							</>
						)}
					</div>

					{/* Mobile Menu Trigger */}
					<button
						onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
						className="md:hidden text-white focus:outline-none hover:text-[#45f3ff] p-1"
					>
						{mobileMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
					</button>
				</div>

				{/* Mobile Menu */}
				{mobileMenuOpen && (
					<div className="md:hidden border-b border-[#1f2833]/60 bg-[#0b0c10]/95 backdrop-blur-lg px-6 py-6 space-y-4 animate-in fade-in slide-in-from-top-5 duration-200">
						<a href="#features" onClick={() => setMobileMenuOpen(false)} className="block py-2 text-lg hover:text-[#45f3ff]">Features</a>
						<a href="#code" onClick={() => setMobileMenuOpen(false)} className="block py-2 text-lg hover:text-[#45f3ff]">Quickstart</a>
						<a href="#architecture" onClick={() => setMobileMenuOpen(false)} className="block py-2 text-lg hover:text-[#45f3ff]">Architecture</a>
						<a href="/workspace/docs" className="block py-2 text-lg hover:text-[#45f3ff] flex items-center gap-1.5">
							Docs <ExternalLink className="h-4 w-4" />
						</a>
						<div className="h-px bg-[#1f2833]/60 my-4" />
						{isLoggedIn ? (
							<Button
								onClick={() => { setMobileMenuOpen(false); navigate({ to: "/workspace" }); }}
								className="w-full bg-[#45f3ff] text-[#0b0c10] hover:bg-[#45f3ff]/90 font-semibold shadow-[0_0_15px_rgba(69,243,255,0.25)] rounded-md h-10 px-5"
							>
								Go to Workspace
							</Button>
						) : (
							<div className="flex flex-col gap-3">
								<Link
									to="/login"
									onClick={() => setMobileMenuOpen(false)}
									className="text-center font-semibold text-white py-2 hover:text-[#45f3ff] transition-colors"
								>
									Sign In
								</Link>
								<Button
									onClick={() => { setMobileMenuOpen(false); navigate({ to: "/signup" }); }}
									className="w-full bg-transparent text-white border border-[#45f3ff] hover:bg-[#45f3ff]/10 font-semibold rounded-md h-10 px-5"
								>
									Sign Up
								</Button>
							</div>
						)}
					</div>
				)}
			</nav>

			{/* Hero Section */}
			<section className="relative pt-20 pb-24 md:pt-32 md:pb-36 flex flex-col items-center text-center px-6 max-w-5xl mx-auto">
				<div className="flex flex-col items-center gap-3 mb-8">
					<img
						src={companyLogoSrc}
						alt={companyFullName}
						className="h-20 sm:h-28 w-auto max-w-[min(100%,420px)] object-contain"
					/>
					<p className="text-sm sm:text-base font-semibold tracking-[0.22em] text-[#c5a962] uppercase">
						{companyFullName}
					</p>
				</div>

				<div className="inline-flex items-center gap-2 px-3 py-1 bg-[#1f2833]/40 border border-[#1f2833] rounded-full text-xs font-semibold tracking-wide text-[#45f3ff] mb-8 shadow-[inset_0_1px_12px_rgba(69,243,255,0.05)]">
					<Zap className="h-3.5 w-3.5 fill-[#45f3ff]" />
					<span>Enterprise AI Gateway Platform</span>
				</div>

				<h1 className="text-4xl sm:text-6xl md:text-7xl font-extrabold tracking-tight text-white mb-6 leading-[1.1] max-w-4xl">
					The Smart Gateway for <br className="hidden sm:inline" />
					<span className="bg-gradient-to-r from-[#45f3ff] via-[#66fcf1] to-[#1f2833] bg-clip-text text-transparent drop-shadow-sm">
						Your AI Infrastructure
					</span>
				</h1>

				<p className="text-lg sm:text-xl text-[#8b949e] max-w-2xl mb-10 leading-relaxed">
					Connect all your LLM providers, manage Model Context Protocol (MCP) servers, enforce semantic caching, and govern access through one unified endpoint.
				</p>

				<div className="flex flex-col sm:flex-row items-center gap-4 w-full justify-center">
					{isLoggedIn ? (
						<Button
							onClick={() => navigate({ to: "/workspace" })}
							className="w-full sm:w-auto h-12 px-8 bg-[#45f3ff] text-[#0b0c10] hover:bg-[#45f3ff]/90 font-bold rounded-lg text-base shadow-[0_0_25px_rgba(69,243,255,0.3)] transition-all hover:scale-[1.03]"
						>
							Enter Gateway Dashboard
							<ArrowRight className="h-5 w-5 ml-2" />
						</Button>
					) : (
						<>
							<Button
								onClick={() => navigate({ to: "/signup" })}
								className="w-full sm:w-auto h-12 px-8 bg-[#45f3ff] text-[#0b0c10] hover:bg-[#45f3ff]/90 font-bold rounded-lg text-base shadow-[0_0_25px_rgba(69,243,255,0.3)] transition-all hover:scale-[1.03]"
							>
								Get Started Instantly
								<ArrowRight className="h-5 w-5 ml-2" />
							</Button>
							<a
								href="/workspace/docs"
								className="w-full sm:w-auto h-12 px-8 flex items-center justify-center border border-[#1f2833] bg-[#0b0c10]/40 hover:bg-[#1f2833]/30 font-semibold text-white rounded-lg text-base transition-colors"
							>
								Read the Docs
							</a>
						</>
					)}
				</div>

				{/* Dashboard Mockup */}
				<div className="w-full mt-20 md:mt-24 border border-[#1f2833]/80 rounded-xl bg-[#0b0c10] shadow-[0_20px_50px_rgba(0,0,0,0.7)] overflow-hidden group">
					<div className="border-b border-[#1f2833]/80 bg-[#12141c] px-4 py-3 flex items-center gap-2">
						<div className="w-3.5 h-3.5 rounded-full bg-[#ff5f56]" />
						<div className="w-3.5 h-3.5 rounded-full bg-[#ffbd2e]" />
						<div className="w-3.5 h-3.5 rounded-full bg-[#27c93f]" />
					</div>
					<div className="p-1 sm:p-2 bg-gradient-to-b from-[#12141c] to-[#0b0c10]">
						<img
							src="/static/mockup.png"
							alt="YesPanchi Gateway Dashboard"
							className="w-full h-auto rounded-lg border border-[#1f2833]/20 object-cover"
							onError={(e) => {
								// Fallback: If image fails to load, replace it with a styled grid dashboard skeleton
								e.currentTarget.style.display = "none";
								const skeleton = document.getElementById("mockup-fallback");
								if (skeleton) skeleton.style.display = "block";
							}}
						/>
						{/* Grid skeleton fallback */}
						<div id="mockup-fallback" style={{ display: "none" }} className="w-full aspect-[1.6] bg-[#0b0c10]/95 p-6 space-y-6">
							<div className="grid grid-cols-4 gap-4">
								{[...Array(4)].map((_, i) => (
									<div key={i} className="bg-[#12141c] border border-[#1f2833]/40 p-4 rounded-lg space-y-2">
										<div className="h-3 w-16 bg-[#1f2833] rounded" />
										<div className="h-6 w-24 bg-[#45f3ff]/20 rounded" />
									</div>
								))}
							</div>
							<div className="grid grid-cols-3 gap-4">
								<div className="col-span-2 bg-[#12141c] border border-[#1f2833]/40 h-64 rounded-lg p-4 flex flex-col justify-between">
									<div className="h-4 w-40 bg-[#1f2833] rounded" />
									<div className="h-44 w-full flex items-end gap-2">
										{[...Array(20)].map((_, i) => (
											<div key={i} style={{ height: `${20 + Math.random() * 80}%` }} className="flex-1 bg-[#45f3ff]/40 rounded-t" />
										))}
									</div>
								</div>
								<div className="bg-[#12141c] border border-[#1f2833]/40 h-64 rounded-lg p-4 flex flex-col justify-between">
									<div className="h-4 w-28 bg-[#1f2833] rounded" />
									<div className="w-36 h-36 rounded-full border-[8px] border-[#1f2833] border-t-[#45f3ff] mx-auto flex items-center justify-center">
										<span className="text-[#45f3ff] text-lg font-bold">Postgres</span>
									</div>
									<div className="h-3 w-32 bg-[#1f2833] rounded mx-auto" />
								</div>
							</div>
						</div>
					</div>
				</div>
			</section>

			{/* Features Grid */}
			<section id="features" className="bg-[#12141c]/40 border-y border-[#1f2833]/60 py-20 md:py-28 px-6">
				<div className="max-w-7xl mx-auto">
					<div className="text-center max-w-3xl mx-auto mb-16 md:mb-24">
						<h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-white mb-4">
							Everything You Need in an AI Gateway
						</h2>
						<p className="text-[#8b949e] text-lg">
							UnifAI replaces multiple standalone servers, tracing libraries, and logic hooks with a high-performance, single-binary engine.
						</p>
					</div>

					<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
						{/* Feature 1 */}
						<div className="bg-[#12141c]/50 border border-[#1f2833]/60 rounded-xl p-6 hover:border-[#45f3ff]/40 transition-all hover:-translate-y-1 duration-300">
							<div className="h-10 w-10 rounded-lg bg-[#45f3ff]/10 flex items-center justify-center text-[#45f3ff] mb-5">
								<Code className="h-5 w-5" />
							</div>
							<h3 className="text-xl font-bold text-white mb-2">OpenAI-Compatible API</h3>
							<p className="text-[#8b949e] text-sm leading-relaxed">
								Use your existing OpenAI SDK. Change only the base URL to route your calls to Anthropic, Gemini, Llama, Vertex, Bedrock, and more.
							</p>
						</div>

						{/* Feature 2 */}
						<div className="bg-[#12141c]/50 border border-[#1f2833]/60 rounded-xl p-6 hover:border-[#45f3ff]/40 transition-all hover:-translate-y-1 duration-300">
							<div className="h-10 w-10 rounded-lg bg-[#45f3ff]/10 flex items-center justify-center text-[#45f3ff] mb-5">
								<Terminal className="h-5 w-5" />
							</div>
							<h3 className="text-xl font-bold text-white mb-2">Model Context Protocol (MCP)</h3>
							<p className="text-[#8b949e] text-sm leading-relaxed">
								UnifAI connected MCP servers and tools. Expose filesystem, databases, web search, or APIs directly to your chatbot and editor agents.
							</p>
						</div>

						{/* Feature 3 */}
						<div className="bg-[#12141c]/50 border border-[#1f2833]/60 rounded-xl p-6 hover:border-[#45f3ff]/40 transition-all hover:-translate-y-1 duration-300">
							<div className="h-10 w-10 rounded-lg bg-[#45f3ff]/10 flex items-center justify-center text-[#45f3ff] mb-5">
								<Database className="h-5 w-5" />
							</div>
							<h3 className="text-xl font-bold text-white mb-2">Semantic Caching</h3>
							<p className="text-[#8b949e] text-sm leading-relaxed">
								Drastically cut costs. Enable vector-backed caching to catch identical or semantically similar prompts, serving them instantly at zero cost.
							</p>
						</div>

						{/* Feature 4 */}
						<div className="bg-[#12141c]/50 border border-[#1f2833]/60 rounded-xl p-6 hover:border-[#45f3ff]/40 transition-all hover:-translate-y-1 duration-300">
							<div className="h-10 w-10 rounded-lg bg-[#45f3ff]/10 flex items-center justify-center text-[#45f3ff] mb-5">
								<Lock className="h-5 w-5" />
							</div>
							<h3 className="text-xl font-bold text-white mb-2">Access & Virtual Keys</h3>
							<p className="text-[#8b949e] text-sm leading-relaxed">
								Isolate developers, models, or apps with custom API keys. Set strict token rate limits and configure access controls easily.
							</p>
						</div>

						{/* Feature 5 */}
						<div className="bg-[#12141c]/50 border border-[#1f2833]/60 rounded-xl p-6 hover:border-[#45f3ff]/40 transition-all hover:-translate-y-1 duration-300">
							<div className="h-10 w-10 rounded-lg bg-[#45f3ff]/10 flex items-center justify-center text-[#45f3ff] mb-5">
								<Shield className="h-5 w-5" />
							</div>
							<h3 className="text-xl font-bold text-white mb-2">Smart Fallbacks & Routing</h3>
							<p className="text-[#8b949e] text-sm leading-relaxed">
								Increase uptime. Configure rules to automatically fallback to backup models or alternative providers if the primary endpoint is offline.
							</p>
						</div>

						{/* Feature 6 */}
						<div className="bg-[#12141c]/50 border border-[#1f2833]/60 rounded-xl p-6 hover:border-[#45f3ff]/40 transition-all hover:-translate-y-1 duration-300">
							<div className="h-10 w-10 rounded-lg bg-[#45f3ff]/10 flex items-center justify-center text-[#45f3ff] mb-5">
								<Activity className="h-5 w-5" />
							</div>
							<h3 className="text-xl font-bold text-white mb-2">Audits & Log Tracing</h3>
							<p className="text-[#8b949e] text-sm leading-relaxed">
								Comprehensive audit trail. Trace request and response contents, token counts, response times, and model costs dynamically.
							</p>
						</div>
					</div>
				</div>
			</section>

			{/* Code Demo Section */}
			<section id="code" className="py-20 md:py-28 px-6 max-w-7xl mx-auto">
				<div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
					<div className="space-y-6">
						<h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-white leading-tight">
							One Line Change to Integrate
						</h2>
						<p className="text-[#8b949e] text-lg leading-relaxed">
							UnifAI mirrors standard API interfaces. Replacing your existing LLM provider requires zero refactoring or code rewrites. Just update the connection endpoints.
						</p>

						<div className="space-y-4">
							{[
								"Compatible with standard OpenAI client SDKs",
								"Instantly swap backend models on the fly from the UI",
								"Inject plugins, logging, and safety guardrails automatically"
							].map((item, idx) => (
								<div key={idx} className="flex items-center gap-3">
									<CheckCircle className="h-5 w-5 text-[#45f3ff] flex-shrink-0" />
									<span className="text-sm font-medium text-white">{item}</span>
								</div>
							))}
						</div>
					</div>

					<div className="border border-[#1f2833] rounded-xl bg-[#12141c] overflow-hidden shadow-2xl">
						<div className="flex bg-[#0b0c10] border-b border-[#1f2833] px-4 py-2 justify-between items-center">
							<div className="flex gap-2">
								<button
									onClick={() => setActiveTab("curl")}
									className={`text-xs font-semibold px-3 py-1.5 rounded transition-colors ${activeTab === "curl" ? "bg-[#1f2833] text-white" : "text-gray-500 hover:text-white"}`}
								>
									cURL
								</button>
								<button
									onClick={() => setActiveTab("python")}
									className={`text-xs font-semibold px-3 py-1.5 rounded transition-colors ${activeTab === "python" ? "bg-[#1f2833] text-white" : "text-gray-500 hover:text-white"}`}
								>
									Python
								</button>
								<button
									onClick={() => setActiveTab("node")}
									className={`text-xs font-semibold px-3 py-1.5 rounded transition-colors ${activeTab === "node" ? "bg-[#1f2833] text-white" : "text-gray-500 hover:text-white"}`}
								>
									Node.js
								</button>
							</div>
							<span className="text-[10px] text-gray-500 font-mono">gateway-proxy</span>
						</div>
						<div className="p-5 overflow-x-auto text-[13px] font-mono leading-relaxed bg-[#0b0c10] text-[#a9b1d6] max-h-[300px]">
							<pre className="whitespace-pre">{codeExamples[activeTab]}</pre>
						</div>
					</div>
				</div>
			</section>

			{/* Call To Action Banner */}
			<section className="bg-[#12141c]/20 border-t border-[#1f2833]/60 py-20 px-6 text-center relative overflow-hidden">
				<div className="absolute inset-0 bg-gradient-to-b from-transparent to-[#45f3ff]/5 pointer-events-none" />
				<div className="max-w-4xl mx-auto space-y-6 relative z-10">
					<h2 className="text-3xl sm:text-5xl font-extrabold tracking-tight text-white">
						Ready to Standardize Your AI Stack?
					</h2>
					<p className="text-[#8b949e] text-lg max-w-2xl mx-auto">
						Start running the UnifAI Gateway in production locally or inside a cluster in just 5 minutes.
					</p>
					<div className="pt-4 flex flex-col sm:flex-row items-center gap-4 justify-center">
						{isLoggedIn ? (
							<Button
								onClick={() => navigate({ to: "/workspace" })}
								className="w-full sm:w-auto h-12 px-8 bg-[#45f3ff] text-[#0b0c10] hover:bg-[#45f3ff]/90 font-bold rounded-lg text-base shadow-[0_0_20px_rgba(69,243,255,0.2)]"
							>
								Go to Dashboard
							</Button>
						) : (
							<>
								<Button
									onClick={() => navigate({ to: "/signup" })}
									className="w-full sm:w-auto h-12 px-8 bg-[#45f3ff] text-[#0b0c10] hover:bg-[#45f3ff]/90 font-bold rounded-lg text-base shadow-[0_0_20px_rgba(69,243,255,0.2)]"
								>
									Create Free Account
								</Button>
								<Link
									to="/login"
									className="w-full sm:w-auto h-12 px-8 flex items-center justify-center border border-[#1f2833] bg-[#0b0c10]/40 hover:bg-[#1f2833]/30 font-semibold text-white rounded-lg text-base transition-colors"
								>
									Sign In
								</Link>
							</>
						)}
					</div>
				</div>
			</section>

			{/* Footer */}
			<footer className="border-t border-[#1f2833]/60 bg-[#0b0c10] py-12 px-6">
				<div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-6 text-sm text-[#8b949e]">
					<div className="flex items-center gap-3">
						<img src={companyLogoSrc} alt={companyFullName} className="h-8 w-auto object-contain" />
						<span className="font-bold text-white">{companyFullName}</span>
					</div>
					<span>&copy; 2026 {companyFullName}. All rights reserved.</span>
				</div>
			</footer>
		</div>
	);
}
