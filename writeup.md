# CO2 Extractor — Write-up

## Approach

I used an LLM (Claude via the Anthropic API) as the extraction engine, wrapping it in a thin Python harness that handles file I/O, prompt construction, and JSON validation. Each snippet is sent to the model in a separate API call with a tightly-scoped prompt that spells out every conversion rule explicitly.

The alternative was a purely regex/rule-based approach. For well-structured, homogeneous input that might work fine, but the 7 snippets alone surface four problems that break rules immediately: multilingual text (French), non-standard units (kilotons), European number formatting, and a markdown table. An LLM handles all of these in a single pass without a separate parser per case. The trade-off is non-determinism and latency, both of which I address in the prompt (strict JSON schema, rule ordering) and in post-call validation.

## Assumptions

- "Annual CO2 emissions" means total GHG output for a full calendar or fiscal year, expressed in metric tons CO2-equivalent. Scope-specific figures without a stated total are still valid emissions data.
- A value must be **explicitly stated** in the text. Derived values (e.g. "reduced by 15% vs prior year") are excluded.
- European number formatting (`1.234,56`) is correctly identified by context (language, currency clues) rather than heuristic digit-counting.
- "tCO2e" and "metric tons" are treated as numerically equivalent for extraction purposes (the task asks for metric tons; GWP-weighting is irrelevant here).

These assumptions break if: a document mixes EU and US number formats without clear context, uses non-standard scope definitions, or buries the annual figure in a graph caption rather than body text.

## Edge Cases

| Snippet | Issue | Decision |
|---------|-------|----------|
| `snippet_2` | No numeric value — only a 2035 net-zero pledge | Return `[]`; aspirational language ≠ reported figure |
| `snippet_3` | Unit is **kilotons** (4.8 kt = 4,800 t) | Converted in prompt; rule is explicit |
| `snippet_4` | French text, European number format (`1.234,56`) | LLM handles both simultaneously; rule stated explicitly |
| `snippet_5` | 2024 figure is **derivable** (8,000 × 0.85 = 6,800) but not stated | Excluded — extraction scope is stated values only |
| `snippet_6` | Scope breakdown + total + note redefining "annual emissions" as Scope 1 | Returned the stated **total** (57,000 tCO2e); the note describes their commitment metric, not the total footprint |
| `snippet_7` | Markdown table with 3 years and 4 metrics | LLM reads tables natively; all three CO2 rows extracted; non-CO2 rows (`Water`, `Renewable energy`, `Waste`) ignored |

`snippet_6` is the hardest call: the note says their public commitment figure is Scope 1 only (2,000 t), which could mislead a downstream consumer. In production I would surface a `flags` field alongside `value` to flag ambiguity rather than silently picking one interpretation.

## Scaling

At 100,000 documents the following break first:

1. **Latency** — sequential API calls at ~1 s each = ~28 hours. Fix: async batching with `asyncio` + `httpx`, targeting ~500 concurrent requests (stay within API rate limits).
2. **Cost** — one call per snippet is fine for 7; at 100k, batch multiple snippets per request (up to context-window limits) to reduce per-token overhead.
3. **Reliability** — the LLM occasionally misformats JSON. Fix: retry with exponential back-off; fall back to a structured-output schema (`response_format=json_schema`) to enforce the output shape.
4. **Observability** — at scale you need per-document confidence scores, disagreement flagging (when the same document yields conflicting values across re-runs), and a human-review queue for low-confidence outputs.

A hybrid pipeline would help at scale: a fast regex pre-filter identifies documents that almost certainly have no CO2 value (like `snippet_2`), reducing LLM calls by potentially 30–50%.

## Time Spent

Approximately **45 minutes**: 10 min reading and the task and snippets, 10 mins creating the prompt for LLM and waiting for response, 25 mins reviewing and testing the results.

With another hour I would: add an async batch mode, write pytest unit tests for the parser and number-conversion rules, and experiment with structured output (`json_schema` response format) to eliminate the JSON-fence stripping workaround.
