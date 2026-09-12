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

## Prior work

- **Jamo-level BPE beats syllable/byte-level** — Lee, Cognetta, Moon & Okazaki,
  [*Jamo-Level Subword Tokenization in Low-Resource Korean Machine Translation*](https://aclanthology.org/2025.loresmt-1.8/)
  (LoResMT 2025). Jamo-based subword models consistently outperform syllable- and
  byte-level models in low-resource and restricted-vocabulary settings, with
  shorter tokenized sequences and fewer vocabulary parameters.
- **Tokenization-strategy sweep for Korean** — Park, Lee, Jang & Jung,
  [*An Empirical Study of Tokenization Strategies for Various Korean NLP Tasks*](https://aclanthology.org/2020.aacl-main.17/)
  (AACL 2020, [kortok](https://github.com/kakaobrain/kortok)). Compares jamo (CV),
  syllable, morpheme and BPE strategies; morphological segmentation followed by
  BPE wins overall.
- **Sub-character decomposition in PLMs** — Jeon, Yang, Kim & Lim,
  [*Improving Korean NLP Tasks with Linguistically Informed Subword Tokenization and Sub-character Decomposition*](https://arxiv.org/abs/2311.03928)
  (arXiv 2023). Morpheme-aware subwords plus sub-character decomposition improve
  Korean PLM tasks, notably NIKL-CoLA.
- **Encoder-side precedent in `tokenizers`** — the library's normalizer already
  performs arithmetic Hangul syllable decomposition on the NFD path
  ([c4ec9ef](https://github.com/huggingface/tokenizers/commit/c4ec9ef2fa72f0e693804c300af0b7f5f4c7c4ef));
  the compositional machinery exists, it is just not exposed as a modeling
  primitive.
- **Historical parallel** — legacy Korean encodings faced the same choice this
  repo measures: EUC-KR (완성형/Wansung) covered only the 2,350 most common
  precomposed syllables, while Johab (조합형) covered all 11,172 via jamo
  composition. Vocab-allocated atomic-syllable coverage is a re-run of the
  Wansung trade-off — and history already showed compositional wins.
