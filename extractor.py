#!/usr/bin/env python3
"""
CO2 Emission Extractor
Processes corporate sustainability report snippets and extracts annual
CO2 emissions (in metric tons) using an LLM for robust parsing.

Usage:
    python extractor.py [snippets_file] [output_file]
    python extractor.py                          # uses defaults
    python extractor.py snippets.txt output.json
"""

import re
import json
import sys
import anthropic

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a precise data-extraction engine specialised in
corporate sustainability and ESG reports. Your only job is to return JSON.
Never explain. Never add commentary. Output only valid JSON."""

EXTRACTION_PROMPT = """Extract every annual CO2 emission figure from the text
below and return a JSON array.

Rules (apply in order):
1. Each item must have exactly two fields:
     "value" – the emission amount as a number (int or float) in METRIC TONS
     "year"  – the reporting year as a 4-digit integer
2. Unit conversions (all results must be metric tons):
     kiloton / kt        → multiply by 1 000
     megaton / Mt        → multiply by 1 000 000
     "tonnes métriques"  → already metric tons (no conversion)
     tCO2e               → treat as metric tons (1 tCO2e ≈ 1 tCO2 for extraction purposes)
3. Number-format handling:
     European: "1.234,56" → 1234.56   (period = thousands sep, comma = decimal)
     US/intl:  "12,500"   → 12500     (comma = thousands sep)
4. Scope handling: if individual Scope 1 / 2 / 3 lines AND an explicit total
   are all present, return ONLY the total. If only scopes and no total, return
   each scope as a separate entry.
5. Include ONLY explicitly stated values — do NOT derive or calculate
   (e.g. do not compute "previous year minus 15%").
6. If multiple reporting years appear, include ALL of them as separate entries.
7. If the text contains no CO2 figure, return an empty array: []

Text to analyse:
{text}

Return ONLY the raw JSON array. No markdown fences, no explanation."""


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def parse_snippets(filepath: str) -> dict[str, str]:
    """Read snippets.txt and return {snippet_id: text} preserving order."""
    with open(filepath, encoding="utf-8") as f:
        content = f.read()

    # Match every === snippet_N === block
    pattern = r"=== (snippet_\d+) ===\n(.*?)(?=\n=== snippet_\d+ ===|\Z)"
    matches = re.findall(pattern, content, re.DOTALL)
    if not matches:
        raise ValueError(f"No snippets found in {filepath}")
    return {name: text.strip() for name, text in matches}


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

def extract_entries(client: anthropic.Anthropic, text: str) -> list[dict]:
    """Call the LLM to extract CO2 entries from one snippet."""
    response = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=512,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": EXTRACTION_PROMPT.format(text=text),
            }
        ],
    )
    raw = response.content[0].text.strip()

    # Defensively strip markdown fences in case the model wraps output
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    raw = raw.strip()

    entries = json.loads(raw)
    # Validate shape
    for entry in entries:
        if not isinstance(entry.get("value"), (int, float)):
            raise ValueError(f"Bad value field: {entry}")
        if not isinstance(entry.get("year"), int):
            raise ValueError(f"Bad year field: {entry}")
    return entries


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    snippets_path = sys.argv[1] if len(sys.argv) > 1 else "snippets.txt"
    output_path   = sys.argv[2] if len(sys.argv) > 2 else "output.json"

    print(f"Loading snippets from: {snippets_path}")
    snippets = parse_snippets(snippets_path)
    print(f"Found {len(snippets)} snippet(s)\n")

    client  = anthropic.Anthropic()
    results = {}

    for snippet_id in sorted(snippets):
        text = snippets[snippet_id]
        print(f"Processing {snippet_id} …", end=" ", flush=True)
        try:
            entries = extract_entries(client, text)
            results[snippet_id] = entries
            print(f"→ {entries}")
        except Exception as exc:
            print(f"ERROR: {exc}")
            results[snippet_id] = []

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\n✓ Output written to: {output_path}")


if __name__ == "__main__":
    main()
