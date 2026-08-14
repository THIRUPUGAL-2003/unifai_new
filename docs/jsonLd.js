const jsonLd = {
	"@context": "https://schema.org",
	"@type": "WebPage",
	url: "https://www.getmaxim.ai/unifai/docs",
	name: "UnifAI Documentation",
	description:
		"Comprehensive documentation for Maxim's end-to-end platform for AI simulation, evaluation, and observability. Learn how to build, evaluate, and monitor GenAI workflows at scale.",
	publisher: {
		"@type": "Organization",
		name: "UnifAI",
		url: "https://www.getmaxim.ai/unifai",
		logo: {
			"@type": "ImageObject",
			url: "https://unifai.getmaxim.ai/logo-full.svg",
			width: 300,
			height: 60,
		},
		sameAs: ["https://twitter.com/getmaximai", "https://www.linkedin.com/company/maxim-ai", "https://www.youtube.com/@getmaximai"],
	},
	mainEntity: {
		"@type": "TechArticle",
		name: "UnifAI Documentation",
		url: "https://www.getmaxim.ai/unifai",
		headline: "UnifAI Docs",
		description:
			"UnifAI is the fastest LLM gateway in the market, 90x faster than LiteLLM (P99 latency).",
		inLanguage: "en",
	},
};

function injectJsonLd() {
	const script = document.createElement("script");
	script.type = "application/ld+json";
	script.text = JSON.stringify(jsonLd);

	if (document.readyState === "loading") {
		document.addEventListener("DOMContentLoaded", () => {
			document.head.appendChild(script);
		});
	} else {
		document.head.appendChild(script);
	}

	return () => {
		if (script.parentNode) {
			script.parentNode.removeChild(script);
		}
	};
}

// Call the function to inject JSON-LD
const cleanup = injectJsonLd();

// Cleanup when needed
// cleanup()