import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { getErrorMessage, useLoginMutation } from "@/lib/store/apis";
import { BooksIcon, DiscordLogoIcon, GithubLogoIcon } from "@phosphor-icons/react";
import { Link } from "@tanstack/react-router";
import { Eye, EyeOff, ShieldAlert, Cpu } from "lucide-react";
import { useState } from "react";

const externalLinks = [
	{
		title: "Discord Server",
		url: "https://discord.gg/exN5KAydbU",
		icon: DiscordLogoIcon,
	},
	{
		title: "GitHub Repository",
		url: "",
		icon: GithubLogoIcon,
	},
	{
		title: "Full Documentation",
		url: "",
		icon: BooksIcon,
		strokeWidth: 1,
	},
];

export default function LoginView() {
	const [username, setUsername] = useState("");
	const [password, setPassword] = useState("");
	const [showPassword, setShowPassword] = useState(false);
	const [errorMessage, setErrorMessage] = useState("");
	const [isLoading, setIsLoading] = useState(false);
	const [login, { isLoading: isLoggingIn }] = useLoginMutation();

	const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
		setIsLoading(true);
		e.preventDefault();
		setErrorMessage("");
		try {
			await login({ username, password }).unwrap();
			// Full navigation so RTK cache cannot keep a pre-login /api/config 401
			// (which surfaces as the misleading "Config store setup is missing" banner).
			const params = new URLSearchParams(window.location.search);
			const goto = params.get("goto") || "/workspace";
			window.location.assign(goto.startsWith("/") ? goto : "/workspace");
		} catch (error) {
			const message = getErrorMessage(error);
			setErrorMessage(message);
		} finally {
			setIsLoading(false);
		}
	};

	return (
		<div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-[#0b0c10] p-6 font-sans text-[#c5c6c7]">
			{/* Background decoration */}
			<div className="pointer-events-none absolute -top-40 -left-40 h-[600px] w-[600px] rounded-full bg-[#1f2833]/20 blur-[150px]" />
			<div className="pointer-events-none absolute -right-40 -bottom-40 h-[500px] w-[500px] rounded-full bg-[#45f3ff]/5 blur-[130px]" />

			<div className="relative z-10 grid w-full max-w-4xl grid-cols-1 overflow-hidden rounded-xl border border-[#1f2833]/60 bg-[#12141c]/40 shadow-[0_20px_50px_rgba(0,0,0,0.5)] backdrop-blur-md md:grid-cols-12">
				{/* Info Panel (Left on large screens, matches signup) */}
				<div className="flex flex-col justify-between border-r border-[#1f2833]/60 bg-gradient-to-br from-[#12141c] to-[#0b0c10] p-8 md:col-span-5 md:p-12">
					<div className="space-y-8">
						<div className="flex items-center gap-3">
							<div className="flex h-8 w-8 items-center justify-center rounded bg-[#45f3ff]/10 text-[#45f3ff] shadow-[0_0_10px_rgba(69,243,255,0.1)]">
								<Cpu className="h-4.5 w-4.5" />
							</div>
							<span className="text-lg font-bold tracking-tight text-white">UnifAI.ai</span>
						</div>

						<div className="space-y-4">
							<h2 className="text-2xl leading-tight font-extrabold text-white">Welcome Back</h2>
							<p className="text-sm leading-relaxed text-[#8b949e]">
								Sign in to your UnifAI dashboard to configure provider routing rules, trace logs, or register tools.
							</p>
						</div>
					</div>

					{/* External community Links */}
					<div className="space-y-4 pt-6">
						<div className="text-xs font-semibold tracking-wider text-gray-500 uppercase">Resources</div>
						<div className="flex flex-col gap-2">
							{externalLinks.map((item, index) => (
								<a
									key={index}
									href={item.url}
									target="_blank"
									rel="noopener noreferrer"
									className="flex items-center gap-2.5 text-xs text-[#8b949e] transition-colors hover:text-[#45f3ff]"
								>
									<item.icon className="h-4 w-4" size={16} />
									<span>{item.title}</span>
								</a>
							))}
						</div>
					</div>
				</div>

				{/* Form Panel */}
				<div className="flex flex-col justify-center p-8 md:col-span-7 md:p-12">
					<div className="space-y-6">
						<div className="space-y-2">
							<h1 className="text-2xl font-bold text-white">Sign In</h1>
							<p className="text-sm text-[#8b949e]">Enter your admin credentials to access the gateway.</p>
						</div>

						{errorMessage && (
							<div className="bg-destructive/10 border-destructive/20 text-destructive flex items-center gap-2.5 rounded-lg border p-3 text-sm">
								<ShieldAlert className="h-4 w-4 flex-shrink-0" />
								<span>{errorMessage}</span>
							</div>
						)}

						<form onSubmit={handleSubmit} className="space-y-4">
							<div className="space-y-2">
								<Label htmlFor="username" className="text-xs font-semibold tracking-wider text-white uppercase">
									Username
								</Label>
								<Input
									id="username"
									type="text"
									placeholder="Enter your username"
									value={username}
									onChange={(e) => setUsername(e.target.value)}
									required
									className="border-[#1f2833]/80 bg-[#0b0c10]/80 text-sm text-white focus:border-[#45f3ff]"
									autoComplete="username"
								/>
							</div>

							<div className="space-y-2">
								<div className="flex items-center justify-between">
									<Label htmlFor="password" className="text-xs font-semibold tracking-wider text-white uppercase">
										Password
									</Label>
								</div>
								<div className="relative">
									<Input
										id="password"
										type={showPassword ? "text" : "password"}
										placeholder="Enter your password"
										value={password}
										onChange={(e) => setPassword(e.target.value)}
										required
										className="border-[#1f2833]/80 bg-[#0b0c10]/80 pr-10 text-sm text-white focus:border-[#45f3ff]"
										autoComplete="current-password"
									/>
									<button
										type="button"
										onClick={() => setShowPassword(!showPassword)}
										className="absolute top-1/2 right-3 -translate-y-1/2 text-gray-500 hover:text-white"
									>
										{showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
									</button>
								</div>
							</div>

							<Button
								type="submit"
								className="mt-2 h-10 w-full bg-[#45f3ff] font-bold text-[#0b0c10] shadow-[0_0_15px_rgba(69,243,255,0.15)] hover:bg-[#45f3ff]/90"
								disabled={isLoading || isLoggingIn}
							>
								{isLoading || isLoggingIn ? "Signing in..." : "Sign In"}
							</Button>
						</form>

						<div className="pt-2 text-center">
							<span className="text-xs text-[#8b949e]">
								New deployment?{" "}
								<Link to="/signup" className="font-medium text-[#45f3ff] hover:underline">
									Configure Admin Account
								</Link>
							</span>
						</div>
					</div>
				</div>
			</div>
		</div>
	);
}