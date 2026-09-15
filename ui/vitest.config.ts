import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import fs from "node:fs";
import path from "node:path";

const isEnterpriseBuild = fs.existsSync(path.join(__dirname, "app", "enterprise"));

export default defineConfig({
	plugins: [react()],
	resolve: {
		alias: {
			"@": path.resolve(__dirname, "."),
			"@enterprise": isEnterpriseBuild
				? path.resolve(__dirname, "app", "enterprise")
				: path.resolve(__dirname, "app", "_fallbacks", "enterprise"),
			"@schemas": isEnterpriseBuild
				? path.resolve(__dirname, "app", "enterprise", "lib", "schemas")
				: path.resolve(__dirname, "app", "_fallbacks", "enterprise", "lib", "schemas"),
		},
	},
	test: {
		globals: true,
	},
});