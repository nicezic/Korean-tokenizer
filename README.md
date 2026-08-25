# KOREAN-tokenizer

Hangul-awareness benchmarks for production LLM tokenizers.

Korean (Hangul) is a **compositional script**: every syllable block (U+AC00–D7A3) is pure
arithmetic over just **68 jamo** (19 initials + 21 vowels + 28 finals). Yet mainstream
tokenizers treat all 11,172 syllable blocks as opaque byte sequences with zero structural
awareness.

This repo measures how deep that blindness goes, across three production tokenizers.
Motivation and proposal: [huggingface/tokenizers#1975](https://github.com/huggingface/tokenizers/issues/1975)
(companion: [google/sentencepiece#1197](https://github.com/google/sentencepiece/issues/1197),
merged TSV in [google/sentencepiece#1200](https://github.com/google/sentencepiece/pull/1200)).

## Methodology

1. **Vocab anatomy** — decode every vocab entry back through the GPT-2 byte-level alphabet,
   then classify:
   - *atomic single-syllable* tokens (entire token is one U+AC00–D7A3 char)
   - *multi-syllable* merges
   - *jamo-containing* tokens (U+1100–11FF / U+3130–318F)
2. **NFC vs NFD stress test** — encode an identical 85-char Korean paragraph in composed
   (NFC) vs decomposed (NFD) form; NFD is what you get from macOS text pipelines and
   jamo search queries.

## Results (measured 2026-08-25)

| Metric | GLM-5.2 (vocab 154,820)* | cl100k_base / GPT-4 (100,277) | o200k_base / GPT-4o (200,019) |
|---|---|---|---|
| Unique syllables with an atomic token | 295 / 11,172 (**2.6%**) | 164 (**1.5%**) | 700 (**6.3%**) |
| Multi-syllable merge tokens | 109 | 62 | 1,219 |
| Jamo-containing tokens | **0** | **0** | **8** |
| Unicode normalizer | none (`normalizer: null`) | none | none |
| Korean sample — NFC / NFD | 64 / 445 tokens | 75 / 452 tokens | 51 / 472 tokens |
| **NFD blow-up factor** | **6.95×** | **6.03×** | **9.25×** |

\* GLM-5.3 shares its base model with GLM-5.2, so these findings apply to it as well.

### Observations

- **No tokenizer knows Hangul is compositional.** Across 100K–200K vocabularies,
  jamo tokens number 0–8 — statistical noise. The full Hangul system needs only 68 symbols;
  instead, models spend thousands of vocab slots on accidental syllable fragments.
- **Decomposed Hangul collapses catastrophically.** Any NFD input explodes 6–9.3× into raw
  UTF-8 byte fragments. More vocabulary does not fix missing structure — the largest-vocab
  model suffers the worst relative blow-up.
- **Even common syllables are mostly unrepresented.** Only 1.5–6.3% of syllable blocks ever
  earned an atomic token; the other ~94–98% are encoded as accidental merges or mid-character
  byte fragments.
- A ~10-line jamo-decomposition pre-tokenizer step would make the 68-jamo inventory the
  structural foundation, instead of hoping statistics rediscover it per-syllable at enormous
  vocab cost. See the RFC for the proposal.

## Usage

```bash
uv run --with tokenizers python analyze_tokenizer_json.py <path/to/tokenizer.json>
uv run --with tiktoken python analyze_tiktoken_encoding.py cl100k_base o200k_base
```

Any HF `tokenizer.json` works for the first script, so Qwen, Llama, Gemma, Mistral etc.
can be benchmarked identically.

## Files

| File | Purpose |
|---|---|
| `hangul_metrics.py` | Shared classification + NFC/NFD blow-up logic |
| `analyze_tokenizer_json.py` | Analyze any HF `tokenizer.json` |
| `analyze_tiktoken_encoding.py` | Analyze any `tiktoken` encoding |
