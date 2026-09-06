#!/usr/bin/env python3
"""Fix corrupted runTestEvaluate() in ui/app/workspace/browser-ai/page.tsx."""
from __future__ import annotations

import re
import sys
from pathlib import Path

FIXED = '''\tconst runTestEvaluate = async (which: "new" | "edit") => {
\t\tconst policy = which === "new" ? newRuleBotPrompt.trim() : editRuleBotPrompt.trim();
\t\tconst sample = which === "new" ? newRuleTestSample.trim() : editRuleTestSample.trim();
\t\tconst provider = which === "new" ? newRuleBotProvider : editRuleBotProvider;
\t\tconst model = which === "new" ? newRuleBotModel : editRuleBotModel;
\t\tconst action = which === "new" ? newRuleAction : editRuleAction;
\t\tconst setResult = which === "new" ? setNewRuleTestResult : setEditRuleTestResult;
\t\tsetResult("");
\t\tif (!policy) {
\t\t\tsetResult("Enter a security policy first.");
\t\t\treturn;
\t\t}
\t\tif (!sample) {
\t\t\tsetResult("Enter a sample Browser AI prompt to evaluate.");
\t\t\treturn;
\t\t}
\t\ttry {
\t\t\tconst res = await testGuardBot({
\t\t\t\tbot_provider: provider || GUARD_BOT_OLLAMA_PROVIDER,
\t\t\t\tbot_model: model || GUARD_BOT_OLLAMA_MODEL,
\t\t\t\tbot_prompt: policy,
\t\t\t\tsample_prompt: sample,
\t\t\t\taction,
\t\t\t\tname: which === "new" ? newRuleName.trim() || "Test" : editRuleName.trim() || "Test",
\t\t\t}).unwrap();
\t\t\tif (res.eval_error) {
\t\t\t\tsetResult(`EVAL FAILED: ${res.eval_error}`);
\t\t\t\treturn;
\t\t\t}
\t\t\tlet outcome = `OK — ${res.security_message || "no violation"}`;
\t\t\tif (res.would_block) {
\t\t\t\toutcome = `BLOCK — ${res.security_message || "policy violation"}`;
\t\t\t} else if (res.would_warn) {
\t\t\t\toutcome = `REDACT — ${res.security_message || "policy match"}`;
\t\t\t}
\t\t\tif (res.model_raw?.trim()) {
\t\t\t\toutcome = `${outcome}\\n\\nmodel_raw: ${res.model_raw}`;
\t\t\t}
\t\t\tsetResult(outcome);
\t\t} catch (e: any) {
\t\t\tsetResult(
\t\t\t\te?.data?.error?.message ||
\t\t\t\t\te?.data?.message ||
\t\t\t\t\te?.message ||
\t\t\t\t\t"Model evaluate request failed.",
\t\t\t);
\t\t}
\t};
'''

# Match from runTestEvaluate through the next top-level const/function (handleEditRuleSubmit)
PATTERN = re.compile(
    r"\tconst runTestEvaluate = async \(which: \"new\" \| \"edit\"\) => \{.*?\n\t\};\n(?=\tconst handleEditRuleSubmit)",
    re.DOTALL,
)


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    path = root / "ui" / "app" / "workspace" / "browser-ai" / "page.tsx"
    if not path.is_file():
        print(f"FAIL: missing {path}")
        return 1
    text = path.read_text(encoding="utf-8")
    if "if (res.would_block)" in text and "Model evaluate request failed." in text and "let outcome =" in text:
        # Still verify no orphan duplicate setResult spam
        if text.count("setResult(`BLOCK —") <= 1 and "setResult(`BLOCK — ${res.security_message || \"policy violation\"}`);\n\t\t\t\tsetResult(`BLOCK" not in text:
            print(f"OK: already fixed: {path}")
            return 0
    if not PATTERN.search(text):
        print(f"FAIL: could not locate runTestEvaluate block in {path}")
        # show nearby lines for debugging
        idx = text.find("const runTestEvaluate")
        print("idx", idx)
        if idx >= 0:
            print(text[idx : idx + 800])
        return 2
    new_text, n = PATTERN.subn(FIXED + "\n", text, count=1)
    if n != 1:
        print(f"FAIL: replace count={n}")
        return 3
    path.write_text(new_text, encoding="utf-8")
    print(f"FIXED: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
