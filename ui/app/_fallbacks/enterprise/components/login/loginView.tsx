import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { getErrorMessage, useLoginMutation } from "@/lib/store/apis";
import { resolvePostLoginPath } from "@/lib/utils/workspaceAccess";
import { Activity, Cpu, Eye, EyeOff, Globe, Lock, Shield, ShieldAlert, Upload } from "lucide-react";
import { useState } from "react";

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
			const result = await login({ username, password }).unwrap();
			const params = new URLSearchParams(window.location.search);
			const goto = params.get("goto");
			const target = resolvePostLoginPath({ role: result.role }, goto);
			window.location.assign(target);
		} catch (error) {
			setErrorMessage(getErrorMessage(error));
		} finally {
			setIsLoading(false);
		}
	};

	return (
		<div className="relative flex min-h-screen flex-col overflow-hidden bg-[#07080c] font-sans text-[#c5c6c7]">
			<div className="ug-login-grid pointer-events-none absolute inset-0" />
			<div className="pointer-events-none absolute -top-32 left-[-8%] h-[520px] w-[520px] rounded-full bg-[#45f3ff]/12 blur-[140px]" />
			<div className="pointer-events-none absolute right-[-10%] bottom-[-18%] h-[480px] w-[480px] rounded-full bg-[#3b82f6]/16 blur-[150px]" />

			<div className="relative z-10 mx-auto flex w-full max-w-[1440px] flex-1 flex-col px-5 py-6 lg:px-10 lg:py-8">
				<header className="flex items-center justify-between">
					<div className="flex items-center gap-3.5">
						<div className="flex h-12 w-12 items-center justify-center rounded-xl border border-[#45f3ff]/25 bg-[#45f3ff]/10 text-[#45f3ff]">
							<Cpu className="h-6 w-6" />
						</div>
						<div>
							<p className="text-xl font-bold tracking-tight text-white">UnifAI Guard</p>
							<p className="text-[11px] tracking-[0.16em] text-[#7d8896] uppercase">YesPanchi Group of Companies</p>
						</div>
					</div>
					<div className="hidden items-center gap-2 rounded-full border border-[#1f2833] bg-[#12141c]/70 px-3 py-1.5 text-xs text-[#8b949e] sm:flex">
						<span className="h-1.5 w-1.5 rounded-full bg-[#45f3ff] shadow-[0_0_8px_#45f3ff]" />
						Live policy sync
					</div>
				</header>

				<main className="grid flex-1 items-center gap-10 pt-8 lg:grid-cols-12 lg:gap-8 lg:pt-4">
					<section className="lg:col-span-7">
						<div className="mb-8 max-w-xl space-y-4">
							<div className="inline-flex items-center rounded-full border border-[#45f3ff]/20 bg-[#45f3ff]/10 px-3 py-1 text-[11px] font-semibold tracking-[0.16em] text-[#89f7ff] uppercase">
								Browser AI security
							</div>
							<h1 className="text-4xl leading-[1.08] font-extrabold text-white sm:text-5xl lg:text-[56px]">
								See every risk.
								<br />
								<span className="bg-gradient-to-r from-[#45f3ff] to-[#7dd3fc] bg-clip-text text-transparent">
									Block it in real time.
								</span>
							</h1>
							<p className="max-w-lg text-sm leading-7 text-[#8b949e] sm:text-base">
								One dashboard for employee AI chats, website locks, upload policy, and Guard agents — no restart, no extra
								tools.
							</p>
						</div>

						<div className="ug-login-stage relative mx-auto h-[360px] w-full max-w-[640px] sm:h-[420px] lg:mx-0">
							<div className="ug-login-glow pointer-events-none absolute inset-x-10 bottom-6 h-24 rounded-full bg-[#45f3ff]/20 blur-3xl" />

							<div className="ug-login-plane relative h-full w-full">
								<div className="ug-login-glass absolute inset-x-6 top-10 overflow-hidden rounded-3xl sm:inset-x-10">
									<div className="flex items-center gap-2 border-b border-white/5 px-4 py-3">
										<span className="h-2.5 w-2.5 rounded-full bg-[#ff5f57]" />
										<span className="h-2.5 w-2.5 rounded-full bg-[#febc2e]" />
										<span className="h-2.5 w-2.5 rounded-full bg-[#28c840]" />
										<span className="ml-3 text-xs font-medium text-white/80">Browser AI Control</span>
									</div>
									<div className="grid grid-cols-3 gap-3 p-4">
										<div className="rounded-2xl border border-white/10 bg-white/5 p-3">
											<p className="text-[10px] tracking-wider text-[#8b949e] uppercase">Targets</p>
											<p className="mt-1 text-xl font-bold text-white">Any domain</p>
										</div>
										<div className="rounded-2xl border border-rose-500/20 bg-rose-500/10 p-3">
											<p className="text-[10px] tracking-wider text-rose-300 uppercase">Locks</p>
											<p className="mt-1 text-xl font-bold text-white">Full site</p>
										</div>
										<div className="rounded-2xl border border-[#45f3ff]/20 bg-[#45f3ff]/10 p-3">
											<p className="text-[10px] tracking-wider text-[#89f7ff] uppercase">Uploads</p>
											<p className="mt-1 text-xl font-bold text-white">Policy on</p>
										</div>
									</div>
									<div className="space-y-2 px-4 pb-5">
										<div className="flex items-center justify-between rounded-xl border border-white/10 bg-[#0b0c10]/70 px-3 py-2.5">
											<div className="flex items-center gap-2 text-sm text-white">
												<Globe className="h-3.5 w-3.5 text-[#45f3ff]" />
												chatgpt.com
											</div>
											<span className="text-[10px] font-semibold tracking-wider text-emerald-400 uppercase">Monitored</span>
										</div>
										<div className="flex items-center justify-between rounded-xl border border-rose-500/20 bg-rose-950/40 px-3 py-2.5">
											<div className="flex items-center gap-2 text-sm text-white">
												<Lock className="h-3.5 w-3.5 text-rose-400" />
												facebook.com
											</div>
											<span className="text-[10px] font-semibold tracking-wider text-rose-300 uppercase">Blocked</span>
										</div>
										<div className="flex items-center justify-between rounded-xl border border-amber-500/20 bg-amber-950/30 px-3 py-2.5">
											<div className="flex items-center gap-2 text-sm text-white">
												<Upload className="h-3.5 w-3.5 text-amber-300" />
												file.pdf
											</div>
											<span className="text-[10px] font-semibold tracking-wider text-amber-200 uppercase">Upload block</span>
										</div>
									</div>
								</div>

								<div className="ug-login-chip absolute top-4 left-0 rounded-2xl border border-[#45f3ff]/25 bg-[#0b0c10]/80 px-3 py-2 shadow-[0_12px_40px_rgba(0,0,0,0.45)] backdrop-blur-md">
									<div className="flex items-center gap-2">
										<Shield className="h-3.5 w-3.5 text-[#45f3ff]" />
										<div>
											<p className="text-[11px] font-semibold text-white">Prompt Guard</p>
											<p className="text-[10px] text-[#8b949e]">Secrets blocked live</p>
										</div>
									</div>
								</div>

								<div className="ug-login-chip ug-login-chip-delay absolute top-16 right-0 rounded-2xl border border-white/10 bg-[#0b0c10]/80 px-3 py-2 shadow-[0_12px_40px_rgba(0,0,0,0.45)] backdrop-blur-md">
									<div className="flex items-center gap-2">
										<Activity className="h-3.5 w-3.5 text-[#45f3ff]" />
										<div>
											<p className="text-[11px] font-semibold text-white">12 agents online</p>
											<p className="text-[10px] text-[#8b949e]">No restart required</p>
										</div>
									</div>
								</div>
							</div>
						</div>
					</section>

					<section className="flex items-center justify-center lg:col-span-5">
						<div className="w-full max-w-md rounded-[28px] border border-white/10 bg-[#10131c]/80 p-8 shadow-[0_30px_80px_rgba(0,0,0,0.55)] backdrop-blur-2xl">
							<div className="mb-6 space-y-2">
								<h2 className="text-3xl font-bold text-white">Sign In</h2>
								<p className="text-sm leading-6 text-[#8b949e]">Access the Guard control plane for your organization.</p>
							</div>

							{errorMessage && (
								<div className="bg-destructive/10 border-destructive/20 text-destructive mb-4 flex items-center gap-2.5 rounded-lg border p-3 text-sm">
									<ShieldAlert className="h-4 w-4 shrink-0" />
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
										className="h-11 border-[#1f2833]/80 bg-[#07080c]/80 text-sm text-white focus:border-[#45f3ff]"
										autoComplete="username"
									/>
								</div>

								<div className="space-y-2">
									<Label htmlFor="password" className="text-xs font-semibold tracking-wider text-white uppercase">
										Password
									</Label>
									<div className="relative">
										<Input
											id="password"
											type={showPassword ? "text" : "password"}
											placeholder="Enter your password"
											value={password}
											onChange={(e) => setPassword(e.target.value)}
											required
											className="h-11 border-[#1f2833]/80 bg-[#07080c]/80 pr-10 text-sm text-white focus:border-[#45f3ff]"
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
									className="mt-2 h-11 w-full bg-[#45f3ff] font-bold text-[#0b0c10] shadow-[0_0_24px_rgba(69,243,255,0.28)] hover:bg-[#45f3ff]/90"
									disabled={isLoading || isLoggingIn}
								>
									{isLoading || isLoggingIn ? "Signing in..." : "Sign In"}
								</Button>
							</form>
						</div>
					</section>
				</main>
			</div>

			<footer className="relative z-10 mt-auto border-t border-[#1f2833]/80 bg-[#07080c]/85 backdrop-blur-md">
				<p className="px-5 py-3.5 text-center text-[11px] font-medium tracking-[0.18em] text-[#7d8896] uppercase">
					YesPanchi Group of Companies
				</p>
			</footer>
		</div>
	);
}
