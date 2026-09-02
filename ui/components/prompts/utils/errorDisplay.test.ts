import { describe, expect, it } from "vitest";

import { formatPromptWarningMessage, isPromptWarningMessage } from "./errorDisplay";

describe("prompt error display", () => {
	it("treats provider API failures as warnings", () => {
		expect(isPromptWarningMessage("provider API error (status 404)")).toBe(true);
		expect(isPromptWarningMessage("provider API error (status 402)")).toBe(true);
	});

	it("formats 404 with actionable guidance", () => {
		expect(formatPromptWarningMessage("provider API error (status 404)")).toContain("Model or endpoint not found");
	});

	it("formats 402 with billing guidance", () => {
		expect(formatPromptWarningMessage("provider API error (status 402)")).toContain("credits");
	});
});
