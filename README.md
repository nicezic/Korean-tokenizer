# KOREAN-tokenizer

Hangul-awareness benchmarks for production LLM tokenizers.

<p align="center">
  <img src="docs/hangul-hero.svg" alt="Animated: 24 basic jamo assemble into 한글 — tokenizers see only byte soup" width="760">
</p>

> **Thesis.** Hangul composes all 11,172 syllables from 67 reusable Jamo (Korean modular alphabet) symbols.
> Eight production tokenizers — OpenAI, Google, Alibaba, DeepSeek, Z.ai, Meta, LG AI Research, Motif Technologies —
> do not use that 67-jamo inventory as structural primitives.
> Proposal: [huggingface/tokenizers#1975](https://github.com/huggingface/tokenizers/issues/1975) ·
> companion: [google/sentencepiece#1197](https://github.com/google/sentencepiece/issues/1197),
> merged TSV in [#1200](https://github.com/google/sentencepiece/pull/1200)

## Results

Measured 2026-08-25–26 across eight production tokenizers, including Korea-focused K-EXAONE 2.0 and Motif 3.

| Metric | o200k / GPT-5·GPT-4o (200,019) | Gemma 4 / Google (262,144) | Qwen3.8 / Alibaba (248,044) | DeepSeek-V4-Flash (128,000) | GLM-5.2\* (154,820) | Muse Glimmer / Meta (200,000) | K-EXAONE 2.0 / LG AI Research (153,600) | Motif 3 / Motif Technologies (220,160) |
|---|---|---|---|---|---|---|---|---|
| Atomic single-syllable tokens | 700 (**6.3%**) | 1,733 (**15.5%**) | 976 (**8.7%**) | 444 (**4.0%**) | 295 (**2.6%**) | 835 (**7.5%**) | 1,576 (**14.1%**) | 1,420 (**12.7%**) |
| Multi-syllable merges | 1,219 | 2,270 | 5,099 | 416 | 109 | 4,030 | 36,207 | **48,271** |
| Jamo-containing tokens (Korean modular alphabet) | 8 | 117 | 14 | **0** | **0** | 5 | 98 | 62 |
| Unicode normalizer | none | `Replace` (`▁`) | **`NFC`** | `Sequence` | none | none | **`NFC`** | none |

\* Subject of this study; GLM-5.3 shares its base model, so findings apply there too.
Vocab sizes in parentheses.

### What the results mean

1. **Bigger vocabularies do not imply Hangul structure.** Gemma 4 owns the largest
   vocabulary (262K) and still covers only 15.5% of syllables with atomic tokens; GLM-5.2
   manages 2.6%. Large vocabularies mostly spend capacity on learned merges rather than the
   reusable 67-jamo inventory.
2. **More Korean merges do not imply structural primitives.** Motif 3 has the largest measured
   multi-syllable inventory at 48,271 pieces while containing only 62 jamo-bearing pieces.
   Statistical compression and explicit Hangul structure are different design choices.
3. **Blindness outlives model generations.** DeepSeek-V4 reuses the V3 tokenizer design;
   Muse Glimmer inherits Llama 4's unchanged. Each flagship generation keeps shipping
   inherited tokenization decisions for Hangul.

## Three independent axes

**Problem A — Canonical robustness.**
`한` (NFC) and `한` (NFD) are canonically equivalent strings of the same word.
Token cost should not depend on which form arrives.

**Problem B — Structural awareness.**
11,172 opaque syllable blocks vs the actual primitives: **19 initial + 21 medial + 27 final**
jamo that compose them.

**Problem C — Compression / fertility.**
How many tokens ordinary Korean text requires, independent of whether the tokenizer is
canonically robust or structurally aware.

> **Normalization, structural primitives, and compression answer different questions.**

The production table above currently reports vocabulary anatomy and tokenizer configuration.
Cross-tokenizer canonical-robustness and compression measurements use the reference test
sets defined in [`docs/test-sets.md`](docs/test-sets.md). No measured production tokenizer uses
the 67-jamo inventory as structural primitives — that is what the RFC proposal targets.

## How Hangul composes

Every syllable block (U+AC00–D7A3) is arithmetic:

```text
19 initials × 21 vowels × 28 final states   (27 finals, or none)
= 11,172 modern syllable blocks
```

drawn from just **67 modern jamo symbols** — 24 basic letters plus their derived compounds.
Decomposition and recomposition are exact integer transforms; no lookup table needed.
Unicode preserves both views (precomposed blocks and conjoining jamo). Production BPE
tokenizers flatten it again.

## Methodology

1. **Vocabulary anatomy** — decode every vocab entry back to text (through the GPT-2
   byte-level alphabet where tokens are stored that way, as plain UTF-8 otherwise), then
   classify:
   - exactly one Hangul syllable → *atomic*
   - ≥ 2 syllables → *multi-syllable merge*
   - contains any jamo character (U+1100–11FF / U+3130–318F) → *jamo-containing*
   - invalid UTF-8 → *byte fragment*
2. **Reference-corpus evaluation** — canonical robustness and compression are evaluated on
   fixed public or reproducible corpora documented in [`docs/test-sets.md`](docs/test-sets.md).

## Experimental validation — controlled SentencePiece A/B

To isolate the representation change from tokenizer algorithm and vocabulary size, two
SentencePiece 0.2.2 BPE tokenizers were trained on the same Korean Wikipedia train split with
the same 32K vocabulary and training configuration. The primary comparison changes exactly
one normalization path: **identity** vs `data/korean_hangul_jamo.tsv`.

> 🧪 **Primary result.** Jamo decomposition uses **1.47% fewer NFC tokens** on the held-out
> Wikipedia split, reduces the full-corpus NFD blow-up from **6.98× to 1.0013×**, and removes
> byte fallback in the measured rare-Hangul tail. It is **not** the best compression-only
> configuration: an NFKC control compresses the held-out corpus better without becoming
> Jamo-structural.

| Metric | Baseline BPE 32K | Jamo-aware BPE 32K |
|---|---:|---:|
| Held-out NFC tokens | 7,449,254 | **7,339,458** (**−1.47%**) |
| Held-out NFD blow-up | **6.9809×** | **1.0013×** |
| Held-out UTF-8 bytes / token | 4.6320 | **4.7013** |
| Tokens / Hangul syllable | 0.8146 | **0.8026** |
| Jamo-containing vocabulary pieces | 75 | **23,657** |
| NFC-recomposed atomic syllables | **1,960** | 1,122 |
| NFC-recomposed multi-syllable pieces | 18,312 | **21,461** |
| Rare-tail isolated tokens / occurrence¹ | 4.0000 | **2.2281** |
| Rare-tail byte tokens / occurrence¹ | 3.0000 | **0.0000** |

¹ Rare tail = syllables occurring at most five times in training and appearing again in the
test split: 50 syllable types / 57 test occurrences. All 11,172 modern syllables occur at
least once in the Wikipedia train split, so this is a **rare-tail fallback probe**, not an
unseen-syllable or out-of-distribution claim. The Jamo model's full-Wikipedia 1.0013× residual
includes NFD changes outside precomposed Hangul.

### Controls and auxiliary run

The 32K `nmt_nfkc` control reaches **7,107,482** held-out NFC tokens (4.8548 bytes/token) and
a **1.0000×** NFD/NFC ratio (a one-token difference), outperforming both primary models on compression while still using
precomposed-syllable vocabulary structure. This is direct evidence that canonical robustness,
structural awareness, and compression are separate axes.

A pre-registered Jamo 24K auxiliary model uses **7,636,747** held-out NFC tokens — **2.52% more**
than the 32K identity baseline — while retaining 1.0012× NFD parity and the same 2.2281-token,
zero-byte-fallback rare-tail behavior. A 25% vocabulary reduction is therefore **not free** at
this operating point.

### Corpus and configuration

The corpus is the first three `kowiki-latest-pages-articles-multistream` shards:

- `multistream1.xml-p1p82407.bz2`
- `multistream2.xml-p82408p253794.bz2`
- `multistream3.xml-p253795p550363.bz2`

Streaming extraction produced **144,018 articles / 319,968,030 characters**. A deterministic
SHA-256 content-hash split at article boundaries produced **136,757 train documents**
(675,056,542 bytes) and **7,261 test documents** (34,519,812 bytes). The train/test SHA-256
hashes are `17d26d1136085e907d2e5e9506c6527ec1db4989840812a507624a0b088801ba` and
`5bb1ae5d792ecc0444b925162c119a2aa6a0550e617d6e964f007a4dcbde5de`.

Common primary settings are BPE, vocab 32,000, `character_coverage=0.9995`, `byte_fallback=true`,
`input_sentence_size=0`, no input shuffling, and `max_sentencepiece_length=64`. The learned
maximum recomposed span is 12 Hangul syllables in both primary models, so the 64-character cap
is not active in the reported result. `character_coverage=1.0` cannot fit this corpus into a
32K vocabulary because the Wikipedia tail contains far more required Unicode characters;
byte fallback preserves excluded rare characters losslessly.

The held-out Wikipedia split is **in-distribution and not deduplicated across documents**.
Templates, citations, quotations, and repeated phrases can cross document boundaries. These
results measure tokenizer behavior, not downstream language-model quality.

## Unicode note

```text
가  U+AC00   precomposed Hangul syllable

ᄀ  U+1100   conjoining jamo · choseong
ᅡ  U+1161   conjoining jamo · jungseong
ᆨ  U+11A8   conjoining jamo · jongseong

ㄱ  U+3131   compatibility jamo (keyboard legacy)
```

NFD produces **conjoining jamo**, not compatibility jamo. The two ranges are different
codepoints for related-but-distinct purposes; this benchmark's NFD path exercises the
conjoining range only.

## Reproduce

```bash
# Production tokenizer benchmark
uv run python src/analyze_tokenizer_json.py <path/to/tokenizer.json>
uv run python src/analyze_tiktoken_encoding.py o200k_base

# Controlled SentencePiece experiment, after downloading the three local Wikipedia shards
uv run python src/extract_wikipedia.py data/kowiki-shard1.xml.bz2 data/kowiki-shard2.xml.bz2 data/kowiki-shard3.xml.bz2
uv run python src/split_corpus.py
uv run python src/train_sentencepiece.py --with-nfkc-control --aux-jamo-vocab-size 24000
uv run python src/compare_sentencepiece.py
```

Any HF `tokenizer.json` works for the first script — both GPT-2-alphabet vocab storage and
plain-text storage (SentencePiece-derived) are handled. Wikipedia dumps, derived corpora, and
trained SentencePiece model artifacts stay local and are ignored by Git.

## Reproducibility

Results describe these exact revisions; providers may update tokenizers at any time.

| Tokenizer | Source · revision | Measured |
|---|---|---|
| o200k_base | `tiktoken` 0.14.0 built-in encoding | 2026-08-25 |
| GLM-5.2 | [`zai-org/GLM-5.2`](https://huggingface.co/zai-org/GLM-5.2) @ `b4734de` | 2026-08-25 |
| Gemma 4 | [`google/gemma-4-E4B-it`](https://huggingface.co/google/gemma-4-E4B-it) @ `ee0ef60` | 2026-08-25 |
| Qwen3.8 | [`Qwen/Qwen3.8-27B`](https://huggingface.co/Qwen/Qwen3.8-27B) @ `1d4bf0f` | 2026-08-25 |
| DeepSeek-V4-Flash | [`deepseek-ai/DeepSeek-V4-Flash-0731`](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-0731) @ `7872f01` | 2026-08-25 |
| Muse Glimmer | [`meta-models/Muse-Glimmer-30B`](https://huggingface.co/meta-models/Muse-Glimmer-30B) @ `a4e59da` | 2026-08-25 |
| K-EXAONE 2.0 | [`LGAI-EXAONE/K-EXAONE-2.0-750B-A37B`](https://huggingface.co/LGAI-EXAONE/K-EXAONE-2.0-750B-A37B) @ `fec0c8d` | 2026-08-25 |
| Motif 3 | [`Motif-Technologies/Motif-3`](https://huggingface.co/Motif-Technologies/Motif-3) @ `883d5c4` | 2026-08-26 |

## What this benchmark does not claim

- NFC/NFD token-count parity is **not** the same as jamo-aware modeling — see
  *Three independent axes* above.
- Jamo counts in a vocabulary are a proxy for structural awareness, not a measurement of
  what models do internally with those structures.
- Token efficiency alone does not demonstrate downstream quality; a model layer can
  compensate for a structure-blind tokenizer at some cost. This benchmark prices that cost,
  it does not claim models fail.

## References

### Canonical robustness

- [Unicode Standard Annex #15: Unicode Normalization Forms](https://www.unicode.org/reports/tr15/)
  - Normative definition of NFC/NFD canonical equivalence used by the stress test in this benchmark.
- [Unicode Korean FAQ](https://www.unicode.org/faq/korean.html)
  - Background on precomposed Hangul syllables and conjoining jamo.

### Hangul structural awareness

- [*A Sub-Character Architecture for Korean Language Processing* — EMNLP 2017](https://aclanthology.org/D17-1075/)
  - Early evidence that jamo-level representations shrink the observation space while exposing reusable Hangul structure.
- [*Jamo Pair Encoding* — LREC 2020](https://aclanthology.org/2020.lrec-1.429/)
  - Applies BPE directly over Hangul jamo to reduce Korean vocabulary cost.
- [*KR-BERT: A Small-Scale Korean-Specific Language Model* — 2020](https://arxiv.org/abs/2008.03979)
  - Demonstrates a competitive Korean-specific model built with a compact sub-character vocabulary; useful evidence without isolating tokenizer causality.
- [*Jamo-Level Subword Tokenization in Low-Resource Korean Machine Translation* — ACL 2025](https://aclanthology.org/2025.loresmt-1.8/)
  - Reports jamo-level BPE gains in low-resource settings, while noting syllable-level tokenization can still win with more data.
- [*KOMBO: Korean Character Representations Based on the Combination Rules of Subcharacters* — Findings of ACL 2024](https://aclanthology.org/2024.findings-acl.302/)
  - Model-level evidence that explicitly encoding Hangul combination rules can improve Korean NLU; this is not a tokenizer-efficiency result.
- [*SCRIPT* — Findings of ACL 2026](https://aclanthology.org/2026.findings-acl.104/)
  - Model-level evidence that Hangul compositional information can be injected into existing subword representations.

### Compression and fertility

- [*Length-aware Byte Pair Encoding for Mitigating Over-segmentation in Korean Machine Translation* — Findings of ACL 2024](https://aclanthology.org/2024.findings-acl.135/)
  - LeVoC shows that Korean over-segmentation is itself a useful optimization target, separate from structural awareness.
- [*Thunder-Tok: Minimizing Tokens per Word in Tokenizing Korean Texts for Generative Language Models* — 2025](https://arxiv.org/abs/2506.15138)
  - Korean tokenizer design focused on fertility; its ablations also show that structural seed filtering matters for downstream quality.
- [*MUTANT: A Recipe for Multilingual Tokenizer Design* — 2026; formerly IndicSuperTokenizer](https://arxiv.org/abs/2511.03237)
  - Provides a recent multilingual methodology precedent for comparing normalization choices and tokenizer fertility.
- [*Parity-Aware BPE* — ACL 2026](https://aclanthology.org/2026.acl-long.342/)
  - Treats cross-language compression disparity as an explicit BPE optimization objective, including Korean evaluation.
- [*SuperBPE: Space Travel for Language Models* — 2025](https://arxiv.org/abs/2503.13423)
  - Two-stage BPE whose second stage lets pre-tokens span multiple whitespace-delimited words; the exact mechanism
    Motif 3 adopts for its Korean compression, explaining this benchmark's table-leading multi-syllable merge count.
- [*Motif 3 Technical Report* — 2026](https://arxiv.org/abs/2608.09119)
  - Uses SuperBPE to optimize multilingual compression; its released tokenizer is a useful counterexample showing that strong Korean compression can coexist with poor NFC/NFD parity.

### Generalization and design caveats

- [*BPE Stays on SCRIPT: Structured Encoding for Robust Multilingual Pretokenization* — 2025](https://arxiv.org/abs/2505.24689)
  - Separates Unicode-script structure from statistical merging and enforces character integrity, eliminating partial UTF-8 token fragments.
- [*Separate Before You Compress: The WWHO Tokenization Architecture* — 2026](https://arxiv.org/abs/2603.25309)
  - Generalizes the same structure-before-compression principle to complex scripts through SGPE and a zero-breakage guarantee.
- [*Improving Korean NLP Tasks with Linguistically Informed Subword Tokenization and Sub-character Decomposition* — 2023](https://arxiv.org/abs/2311.03928)
  - A useful design caveat: selective, linguistically informed decomposition can outperform indiscriminate decomposition.
- [*Getting the Most Out of Your Tokenizer for Pre-training and Domain Adaptation* — ICML 2024](https://proceedings.mlr.press/v235/dagan24a.html)
  - Shows that tokenizer size, pre-tokenization, and training data materially affect speed, context efficiency, and downstream performance.
- [*Don’t Touch My Diacritics* — NAACL 2025](https://aclanthology.org/2025.naacl-short.25/)
  - Documents the risks of inconsistent Unicode preprocessing, useful context when arguing for normalization choices that preserve distinctions.

## Files

| File | Purpose |
|---|---|
| [`docs/test-sets.md`](docs/test-sets.md) | Canonical benchmark-set definitions, roles, and external references |
| [`src/hangul_metrics.py`](src/hangul_metrics.py) | Shared Hangul vocabulary-anatomy classification |
| [`src/analyze_tokenizer_json.py`](src/analyze_tokenizer_json.py) | Analyze any HF `tokenizer.json` |
| [`src/analyze_tiktoken_encoding.py`](src/analyze_tiktoken_encoding.py) | Analyze any `tiktoken` encoding |
| [`src/extract_wikipedia.py`](src/extract_wikipedia.py) | Stream and clean Wikimedia XML bz2 shards while preserving article boundaries |
| [`src/split_corpus.py`](src/split_corpus.py) | Deterministic document-level train/test split |
| [`src/train_sentencepiece.py`](src/train_sentencepiece.py) | Train/audit identity, Jamo, NFKC-control, and auxiliary SentencePiece BPE models |
| [`src/compare_sentencepiece.py`](src/compare_sentencepiece.py) | Held-out compression, normalization, vocabulary, and rare-tail comparison |
| [`tests/test_pipeline.py`](tests/test_pipeline.py) | Pipeline invariants for extraction, splitting, normalization, fairness, and rare-tail metrics |
| [`svg/hangul-hero.svg`](svg/hangul-hero.svg) | Editable source for the animated Hangul hero banner |
| [`docs/hangul-hero.svg`](docs/hangul-hero.svg) | README-rendered copy of the hero banner |
