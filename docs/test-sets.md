# Test sets

## Purpose

Tokenizer evaluation in this repository uses fixed corpora with explicit roles and reproducible identities.

```text
cross-tokenizer comparison
        |
        +-- FLORES+ Korean devtest
        |     -> public, fixed, externally referenceable
        |     -> compression / fertility / NFC-NFD robustness
        |
        +-- Korean Wikipedia held-out
              -> optional domain-scale / precursor validation
              -> document statistics / rare-tail behavior
```

The two sets answer different questions and should be reported separately rather than collapsed into one score.

## 1. FLORES+ Korean devtest — primary reference benchmark

Use the Korean `devtest` split from FLORES+ as the standard cross-tokenizer comparison set.

- **Size:** 1,012 sentences per language in `devtest`.
- **Language:** Korean written in Hangul. The original FLORES-200 identifier is `kor_Hang`.
- **Role:** fixed public reference set for comparing production and experimental tokenizers on the same Korean sentences.
- **Do not train on it.** FLORES+ is an evaluation dataset.

Measure at least:

- total NFC tokens;
- UTF-8 bytes per token;
- characters per token;
- tokens per Hangul syllable;
- NFD token count;
- NFD/NFC token ratio;
- unknown / byte-fallback counts where the tokenizer exposes them.

For canonical robustness, construct the NFD condition deterministically from the exact Korean NFC text used for the NFC condition. Do not substitute different sentences.

### Why this set

FLORES is a professionally translated, aligned multilingual benchmark. FLORES-200 contains 3,001 sentences drawn from 842 source articles; the public splits include `dev` and `devtest`. The actively maintained successor, FLORES+, keeps 997 `dev` and 1,012 `devtest` sentences per language.

It also has direct tokenizer-evaluation precedent: *Teaching Old Tokenizers New Words* (Findings of EACL 2026) reports tokenizer compression as **bytes per token on FLORES**, including Korean.

### References

- [FLORES+ dataset — Open Language Data Initiative](https://huggingface.co/datasets/openlanguagedata/flores_plus)
- [FLORES+ dataset card / current version and split definitions](https://huggingface.co/datasets/openlanguagedata/flores_plus/blob/main/README.md)
- [Original FLORES-200 documentation](https://github.com/facebookresearch/flores/blob/main/flores200/README.md) — includes `Korean | kor_Hang` and the 3,001-sentence composition.
- [*No Language Left Behind: Scaling Human-Centered Machine Translation*](https://arxiv.org/abs/2207.04672) — FLORES-200/NLLB reference.
- [*The Flores-101 Evaluation Benchmark for Low-Resource and Multilingual Machine Translation*](https://aclanthology.org/2022.tacl-1.30/) — benchmark methodology background.
- [*Teaching Old Tokenizers New Words: Efficient Tokenizer Adaptation for Pretrained Models*](https://aclanthology.org/2026.findings-eacl.341/) — tokenizer-compression precedent using FLORES bytes/token.

### Reproducibility rule

Before publishing numbers, pin the exact FLORES+ dataset version or Hugging Face revision used. Do not silently mix FLORES-200 and a later FLORES+ revision in one result table.

## 2. Korean Wikipedia held-out — optional domain / precursor validation

Use the existing deterministic held-out split only as a secondary domain-scale check and to connect new results with the completed SentencePiece precursor.

```text
first three kowiki article shards
        |
        v
streaming extraction
        |
        v
SHA-256 content-hash document split
        |
        +-- precursor train: 136,757 documents
        |
        +-- held-out:          7,261 documents
                               34,519,812 bytes
```

Current held-out metadata:

- **Documents:** 7,261
- **Derived file bytes:** 34,519,812
- **Evaluation text characters:** 15,742,551
- **Held-out SHA-256:** `5bb1ae5d792ecc0444b925162c119a2aa6a0550e617d6e9646f007a4dcbde5de`
- **Paired precursor-train SHA-256:** `17d26d1136085e907d2e5e9506c6527ec1db4989840812a507624a0b088801ba`

The paired train hash identifies the completed Wikipedia/SentencePiece precursor only. **CC-100 Korean is the training corpus for the new 2×2 experiment.**

Source shards:

1. `kowiki-latest-pages-articles-multistream1.xml-p1p82407.bz2`
2. `kowiki-latest-pages-articles-multistream2.xml-p82408p253794.bz2`
3. `kowiki-latest-pages-articles-multistream3.xml-p253795p550363.bz2`

When this set is used, measure the same aggregate compression and NFC/NFD metrics as FLORES+, plus metrics that benefit from a larger document corpus:

- mean and median tokens per document;
- vocabulary anatomy for experimental tokenizers;
- rare-Hangul tail behavior when the frequency definition is tied to the relevant training corpus;
- byte-fallback behavior.

### Interpretation boundary

This split is **in-distribution for the completed Wikipedia precursor and not deduplicated across documents**. Article-level splitting prevents the same extracted article from appearing in both precursor train and held-out files, but Wikipedia templates, citations, quotations, boilerplate, and duplicated phrases may cross document boundaries.

When a tokenizer is trained on CC-100 rather than the paired Wikipedia train split, this set is simply a separate-domain validation corpus. Do not describe it as OOD without a stronger overlap analysis.

### References

- [Korean Wikipedia dump index](https://dumps.wikimedia.org/kowiki/latest/)
- [Wikimedia database backup documentation](https://meta.wikimedia.org/wiki/Data_dumps)
- Local extraction implementation: `src/extract_wikipedia.py`
- Local deterministic split implementation: `src/split_corpus.py`
- Local tokenizer comparison implementation: `src/compare_sentencepiece.py`

## Reporting policy

Use the sets with these roles:

```text
FLORES+ Korean devtest
    -> headline public cross-tokenizer comparison

Wikipedia held-out
    -> optional domain-scale / precursor comparison
       and rare-tail analysis when its definition is appropriate
```

Every result table must name the exact test set and report corpus-level metrics from that set. Do not require Wikipedia validation for a claim that is explicitly scoped to FLORES+.
