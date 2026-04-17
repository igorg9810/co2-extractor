# CO2 Emission Extractor

Extracts annual CO2 emissions (in metric tons) from corporate sustainability
report snippets using the Anthropic Claude API.

## Project Structure

```
co2-extractor/
├── extractor.py    ← main program
├── snippets.txt    ← input data (7 snippets)
├── output.json     ← extracted results (generated)
├── writeup.md      ← approach, assumptions, edge cases
└── README.md       ← this file
```

## Requirements

- Python 3.11+
- `anthropic` Python SDK

```bash
pip install anthropic
```

## Setup

Set your Anthropic API key:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

## Usage

```bash
# Default: reads snippets.txt, writes output.json
python extractor.py

# Custom paths
python extractor.py path/to/snippets.txt path/to/output.json
```

## Output Format

```json
{
  "snippet_1": [{ "value": 12500, "year": 2024 }],
  "snippet_2": [],
  ...
}
```

Each entry contains:
- `value` – CO2 emissions in **metric tons** (float or int)
- `year`  – 4-digit reporting year (int)

Snippets with no extractable CO2 figure return an empty array `[]`.
