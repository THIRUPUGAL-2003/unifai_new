import { describe, expect, it } from "vitest";

import { RequestTypeColors, RequestTypeLabels, RequestTypes, shortenRateLimitMessage } from "./logs";

describe("logs constants", () => {
	it("registers realtime turn as a known request type", () => {
		expect(RequestTypes).toContain("realtime.turn");
		expect(RequestTypeLabels["realtime.turn"]).toBe("Realtime Turn");
		expect(RequestTypeColors["realtime.turn"]).toBeTruthy();
	});

	it("shortens verbose model-level token limit reasons", () => {
		expect(
			shortenRateLimitMessage(
				"Model-level rate limit check failed: rate limit violated for Model:AllModels:Provider:openrouter: [token limit exceeded (71/50, resets every 1h)]",
			),
		).toBe("Token limit exceeded (71/50, resets every 1h)");
	});
});