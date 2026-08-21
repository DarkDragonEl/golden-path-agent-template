# Phase B kickoff, Task 1 — Tool-calling spike + fallback selection

**Branch:** `feature/phase-b-golden-path`. **Script:** `tools/phase_b_tool_calling_spike.py`
(throwaway probe, not agent code — raw JSON in `reports/phase-b-tool-calling-spike-raw.json`
and `reports/phase-b-tool-calling-spike-diagnostic.json`).

## Method

Tool schemas transcribed field-for-field from `srs/SRS-MIT.md` SRS-MIT-IF-02/IF-03 (the
approved contract, not `eval/README.md`'s provisional version). Both `itsm_search_records`
and `itsm_create_request` passed as OpenAI-style `tools=` on every call. Four prompts per
model: `clear_read` (unambiguous lookup), `clear_write` (unambiguous draft-request), `none`
(off-topic — asserts no spurious call), `ambiguous` (VPN-trouble — observed only, no pass/fail
assertion). `temperature=0`. Pass requires: well-formed `tool_calls` (valid JSON args,
required fields present, enum values valid) and the correct tool selected on the two clear
cases; no tool call at all on `none`.

## Shortlist criteria and the three original candidates

Per the kickoff instructions: different model family than Granite (fail-mode decorrelation),
size ≤ primary (~8B — fallback must not silently outperform primary and mask problems through
the wrong route), latency in the same ballpark. Of the 19 models, the three that best fit all
three criteria on paper: `codellama-7b-instruct` (7B, Meta/Code family, GPU-served),
`phi3-mini-cpu` (3.8B, Microsoft, CPU), `qwen25-3b-cpu` (3B, Alibaba, CPU).

## Results — primary + the three shortlisted candidates

| Model | clear_read | clear_write | none | ambiguous (observed) | Latency (clear cases) |
|---|---|---|---|---|---|
| **granite-3-2-8b-instruct** (primary) | pass | pass | pass | called `itsm_search_records` | 1.3s / 1.9s |
| codellama-7b-instruct | **error** | **error** | **error** | — | 5.1–5.6s (all HTTP 400) |
| phi3-mini-cpu | fail (no call) | fail (no call) | pass | no call | 24.5s / 43.1s |
| qwen25-3b-cpu | fail (no call) | fail (no call) | pass | no call | 4.5s / 5.3s |

**codellama-7b-instruct** errors on every call: `"auto" tool choice requires
--enable-auto-tool-choice and --tool-call-parser to be set... Received Model
Group=codellama-7b-instruct` — this specific model group is not configured for tool-calling on
this MaaS deployment at all; it isn't a prompt or schema problem, the backend refuses the
request outright.

**phi3-mini-cpu** and **qwen25-3b-cpu** both accept the request but never emit `tool_calls` on
either clear case — they answer in prose instead. Both correctly decline to call anything on
the `none` case. `phi3-mini-cpu` is also ~15–30× slower than primary (CPU-served), which alone
would have disqualified it on the latency criterion even if it called tools correctly.

**None of the three original candidates passes.** This doesn't match any of the three specified
outcomes (primary+candidate both pass / primary fails+candidate passes / nothing passes
cleanly) — primary passes cleanly, but the failure mode across all three candidates isn't
uniform (one is a hard backend refusal, two are silent no-tool-call behavior), so before
concluding "nothing passes cleanly" for the whole MaaS, four more models were probed as a
diagnostic — cheap to check, and needed to tell "small/CPU models don't do tool-calling here"
apart from "no non-Granite model does."

## Diagnostic probe — four more models (not part of the original shortlist)

| Model | Size (nominal) | clear_read | clear_write | none | Latency (clear cases) |
|---|---|---|---|---|---|
| **llama-scout-17b** | 17B | pass | pass | pass | **0.5s / 0.9s** (faster than primary) |
| **qwen3-14b** | 14B | pass | pass | pass | 8.2s / 6.0s |
| **gpt-oss-120b** | 120B | pass | pass | pass | 5.7s / 4.2s |
| gpt-oss-20b | 20B | error (RemoteDisconnected, ~60s) | error (same) | pass | fast on `none` (5.9s), errors specifically on tool-calling prompts |
| deepseek-r1-distill-qwen-14b | 14B | fail (no call) | fail (no call) | pass | 10.5–18.0s |
| openai/deepseek-r1-distill-qwen-14b | 14B | fail (no call) | fail (no call) | pass | 10.6–18.0s (same behavior as above — likely the same backend under a different route alias) |

**Finding: this is not a small/CPU-model limitation — it's per-model-group backend
configuration and/or architecture.** Three models beyond Granite call tools correctly and
fast: `llama-scout-17b` (fastest of everything tested, even faster than primary),
`qwen3-14b`, and `gpt-oss-120b`. The two DeepSeek-R1-distill routes (same underlying model,
two aliases) consistently fail to emit `tool_calls` at all — likely a reasoning-model
characteristic (verbose chain-of-thought instead of structured output) rather than a config
gap, since `none_of_the_above` behavior looks normal. `codellama-7b-instruct` is a hard
backend-config refusal. `gpt-oss-20b` specifically times out/disconnects on tool-calling
prompts while its `gpt-oss-120b` sibling works fine — looks like an unreliable serving
instance for the 20B variant specifically, not a `gpt-oss` architecture problem.

`llama-scout-17b` had one minor blemish, on the `ambiguous` case only (not a strict-assertion
case): it named a tool `Itsm_create_request` (capitalized) — didn't match the known tool names
and would have been flagged malformed had this happened on a strict case. Worth watching if it
becomes the pick, not disqualifying on its own (this is Granite's chosen role today, and the
ambiguous case has no correct answer to score against).

## The actual decision point — doesn't match the three specified outcomes

Primary passes cleanly. The three candidates that best fit the stated criteria (different
family, size ≤ primary, comparable latency) **all fail** — one hard backend error, two silent
non-calls. But three *other* models fail-mode-decorrelate fine and call tools correctly and
fast — they just violate the size ≤ primary criterion (14B–120B vs. Granite's 8B), which
exists specifically so a routing bug that always uses the fallback wouldn't go undetected by
silently *improving* output. `llama-scout-17b` is the strongest candidate on every other axis
(fastest of anything tested, different family, clean pass) but is the one most likely to
violate the "don't silently outperform primary" intent, being a materially newer/larger
architecture (Llama 4 Scout, 17B active params) than Granite 3.2 8B.

This is flagged back to the owner rather than resolved unilaterally, since it directly
conflicts with an explicit stated design principle rather than just being an implementation
detail.
