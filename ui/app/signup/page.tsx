import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { CheckCircle, ArrowRight, Eye, EyeOff, ShieldAlert, Cpu, Clock } from "lucide-react";
import { Link, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { getApiBaseUrl } from "@/lib/utils/port";

export default function SignupPage() {
	const [username, setUsername] = useState("");
	const [email, setEmail] = useState("");
	const [password, setPassword] = useState("");
	const [confirmPassword, setConfirmPassword] = useState("");
	const [role, setRole] = useState<"user" | "admin">("user");
	const [showPassword, setShowPassword] = useState(false);
	const [errorMessage, setErrorMessage] = useState("");
	const [isSubmitted, setIsSubmitted] = useState(false);
	const [isLoading, setIsLoading] = useState(false);
	const navigate = useNavigate();

	const handleSignup = async (e: React.FormEvent<HTMLFormElement>) => {
		e.preventDefault();
		setErrorMessage("");

		if (password !== confirmPassword) {
			setErrorMessage("Passwords do not match");
			return;
		}

		if (password.length < 8) {
			setErrorMessage("Password must be at least 8 characters long");
			return;
		}

		setIsLoading(true);
		try {
			const res = await fetch(`${getApiBaseUrl()}/session/register`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					username: username.trim(),
					email: email.trim(),
					password,
					role,
				}),
			});
			const data = await res.json().catch(() => ({}));
			if (!res.ok) {
				setErrorMessage(data?.error?.message || data.message || data.error || "Registration failed");
				return;
			}
			setIsSubmitted(true);
		} catch {
			setErrorMessage("Could not reach the server. Please try again.");
		} finally {
			setIsLoading(false);
		}
	};

	return (
		<div className="min-h-screen bg-[#0b0c10] text-[#c5c6c7] flex items-center justify-center p-6 relative overflow-hidden font-sans">
			{/* Background decoration */}
			<div className="absolute -top-40 -left-40 w-[600px] h-[600px] bg-[#1f2833]/20 rounded-full blur-[150px] pointer-events-none" />
			<div className="absolute -bottom-40 -right-40 w-[500px] h-[500px] bg-[#45f3ff]/5 rounded-full blur-[130px] pointer-events-none" />

			<div className="w-full max-w-4xl bg-[#12141c]/40 border border-[#1f2833]/60 rounded-xl overflow-hidden shadow-[0_20px_50px_rgba(0,0,0,0.5)] grid grid-cols-1 md:grid-cols-12 backdrop-blur-md relative z-10">
				{/* Info Panel */}
				<div className="md:col-span-5 bg-gradient-to-br from-[#12141c] to-[#0b0c10] p-8 md:p-12 flex flex-col justify-between border-r border-[#1f2833]/60">
					<div className="space-y-8">
						<div className="flex items-center gap-3">
							<div className="h-8 w-8 bg-[#45f3ff]/10 rounded flex items-center justify-center text-[#45f3ff] shadow-[0_0_10px_rgba(69,243,255,0.1)]">
								<Cpu className="h-4.5 w-4.5" />
							</div>
							<span className="text-lg font-bold tracking-tight text-white">UnifAI.ai</span>
						</div>

						<div className="space-y-6">
							<h2 className="text-2xl font-extrabold text-white leading-tight">Deploy Your Unified AI Gateway</h2>
							<p className="text-sm text-[#8b949e] leading-relaxed">
								Get started with UnifAI to manage keys, fallback routing rules, semantic caching, and Model Context Protocol
								servers in minutes.
							</p>
						</div>

						<div className="space-y-4">
							{[
								"Unified OpenAI-compatible API endpoint",
								"Zero-telemetry local database deployment",
								"Connect Brave Search, Filesystem, or DB to LLMs",
							].map((item, idx) => (
								<div key={idx} className="flex items-start gap-2.5 text-xs text-white">
									<CheckCircle className="h-4 w-4 text-[#45f3ff] flex-shrink-0 mt-0.5" />
									<span>{item}</span>
								</div>
							))}
						</div>
					</div>

					<div className="pt-8 text-xs text-[#8b949e]">
						UnifAI is open source. Deploy on your local machine or Kubernetes cluster.
					</div>
				</div>

				{/* Form Panel */}
				<div className="md:col-span-7 p-8 md:p-12 flex flex-col justify-center">
					{!isSubmitted ? (
						<div className="space-y-6">
							<div className="space-y-2">
								<h1 className="text-2xl font-bold text-white">Create Account</h1>
								<p className="text-sm text-[#8b949e]">
									Request access as a user or admin. An existing admin must approve before you can sign in.
								</p>
							</div>

							{errorMessage && (
								<div className="bg-destructive/10 border border-destructive/20 text-destructive rounded-lg p-3 text-sm flex items-center gap-2.5">
									<ShieldAlert className="h-4 w-4 flex-shrink-0" />
									<span>{errorMessage}</span>
								</div>
							)}

							<form onSubmit={handleSignup} className="space-y-4">
								<div className="space-y-2">
									<Label htmlFor="username" className="text-xs font-semibold text-white uppercase tracking-wider">
										Username
									</Label>
									<Input
										id="username"
										type="text"
										placeholder="e.g. admin"
										value={username}
										onChange={(e) => setUsername(e.target.value)}
										required
										className="bg-[#0b0c10]/80 border-[#1f2833]/80 focus:border-[#45f3ff] text-sm text-white"
									/>
								</div>

								<div className="space-y-2">
									<Label htmlFor="email" className="text-xs font-semibold text-white uppercase tracking-wider">
										Email Address
									</Label>
									<Input
										id="email"
										type="email"
										placeholder="e.g. admin@UnifAI.ai"
										value={email}
										onChange={(e) => setEmail(e.target.value)}
										required
										className="bg-[#0b0c10]/80 border-[#1f2833]/80 focus:border-[#45f3ff] text-sm text-white"
									/>
								</div>

								<div className="space-y-2">
									<Label className="text-xs font-semibold text-white uppercase tracking-wider">Role</Label>
									<div className="grid grid-cols-2 gap-2">
										<button
											type="button"
											onClick={() => setRole("user")}
											className={`h-10 rounded-lg border text-sm font-medium transition-colors ${
												role === "user"
													? "border-[#45f3ff] bg-[#45f3ff]/10 text-[#45f3ff]"
													: "border-[#1f2833]/80 bg-[#0b0c10]/80 text-[#8b949e] hover:border-[#45f3ff]/40"
											}`}
										>
											User
										</button>
										<button
											type="button"
											onClick={() => setRole("admin")}
											className={`h-10 rounded-lg border text-sm font-medium transition-colors ${
												role === "admin"
													? "border-[#45f3ff] bg-[#45f3ff]/10 text-[#45f3ff]"
													: "border-[#1f2833]/80 bg-[#0b0c10]/80 text-[#8b949e] hover:border-[#45f3ff]/40"
											}`}
										>
											Admin
										</button>
									</div>
								</div>

								<div className="space-y-2">
									<Label htmlFor="password" className="text-xs font-semibold text-white uppercase tracking-wider">
										Password
									</Label>
									<div className="relative">
										<Input
											id="password"
											type={showPassword ? "text" : "password"}
											placeholder="At least 8 characters"
											value={password}
											onChange={(e) => setPassword(e.target.value)}
											required
											className="bg-[#0b0c10]/80 border-[#1f2833]/80 focus:border-[#45f3ff] text-sm text-white pr-10"
										/>
										<button
											type="button"
											onClick={() => setShowPassword(!showPassword)}
											className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-white"
										>
											{showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
										</button>
									</div>
								</div>

								<div className="space-y-2">
									<Label htmlFor="confirm-password" className="text-xs font-semibold text-white uppercase tracking-wider">
										Confirm Password
									</Label>
									<Input
										id="confirm-password"
										type="password"
										placeholder="Repeat password"
										value={confirmPassword}
										onChange={(e) => setConfirmPassword(e.target.value)}
										required
										className="bg-[#0b0c10]/80 border-[#1f2833]/80 focus:border-[#45f3ff] text-sm text-white"
									/>
								</div>

								<Button
									type="submit"
									className="w-full bg-[#45f3ff] text-[#0b0c10] hover:bg-[#45f3ff]/90 font-bold h-10 mt-2 shadow-[0_0_15px_rgba(69,243,255,0.15)]"
									disabled={isLoading}
								>
									{isLoading ? "Submitting..." : "Request Access"}
								</Button>
							</form>

							<div className="text-center pt-2">
								<span className="text-xs text-[#8b949e]">
									Already have an account?{" "}
									<Link to="/login" className="text-[#45f3ff] hover:underline font-medium">
										Sign In
									</Link>
								</span>
							</div>
						</div>
					) : (
						<div className="text-center space-y-6 animate-in fade-in duration-300">
							<div className="h-16 w-16 bg-amber-500/10 rounded-full flex items-center justify-center text-amber-300 mx-auto shadow-[0_0_20px_rgba(245,158,11,0.1)]">
								<Clock className="h-8 w-8" />
							</div>

							<div className="space-y-2">
								<h2 className="text-2xl font-bold text-white">Sent to the admin waiting for approval</h2>
								<p className="text-sm text-[#8b949e] max-w-sm mx-auto leading-relaxed">
									Your {role} account request for <span className="text-white font-medium">{username}</span> was submitted.
									An admin must Accept it on the Users page before you can sign in.
								</p>
							</div>

							<Button
								onClick={() => navigate({ to: "/login" })}
								className="bg-[#45f3ff] text-[#0b0c10] hover:bg-[#45f3ff]/90 font-bold h-10 px-6 inline-flex items-center gap-2"
							>
								Back to Sign In
								<ArrowRight className="h-4 w-4" />
							</Button>
						</div>
					)}
				</div>
			</div>
		</div>
	);
}
