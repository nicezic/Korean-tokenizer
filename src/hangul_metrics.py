import unicodedata

SYLLABLE_MIN, SYLLABLE_MAX = 0xAC00, 0xD7A3
JAMO_RANGES = ((0x1100, 0x11FF), (0x3130, 0x318F))


def is_syllable(char):
    return SYLLABLE_MIN <= ord(char) <= SYLLABLE_MAX


def is_jamo(char):
    return any(lo <= ord(char) <= hi for lo, hi in JAMO_RANGES)


def byte_to_unicode_table():
    byte_set = list(range(33, 127)) + list(range(161, 173)) + list(range(174, 256))
    code_points = byte_set[:]
    offset = 0
    for b in range(256):
        if b not in byte_set:
            byte_set.append(b)
            code_points.append(256 + offset)
            offset += 1
    return {chr(c): b for c, b in zip(code_points, byte_set, strict=True)}


def summarize_vocab(byte_iter):
    atomic_syllables = set()
    recomposed_atomic_syllables = set()
    multi_merges = recomposed_multi_merges = jamo_tokens = fragments = total = 0
    max_recomposed_syllables = 0

    for data in byte_iter:
        total += 1
        if data is None:
            fragments += 1
            continue
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            fragments += 1
            continue

        body = text.lstrip(" ")
        syllables = sum(1 for c in body if is_syllable(c))
        if syllables == 1 and len(body) == 1:
            atomic_syllables.add(body)
        elif syllables >= 2:
            multi_merges += 1
        if any(is_jamo(c) for c in body):
            jamo_tokens += 1

        recomposed = unicodedata.normalize("NFC", body)
        recomposed_syllables = sum(1 for c in recomposed if is_syllable(c))
        max_recomposed_syllables = max(max_recomposed_syllables, recomposed_syllables)
        if recomposed_syllables == 1 and len(recomposed) == 1:
            recomposed_atomic_syllables.add(recomposed)
        elif recomposed_syllables >= 2:
            recomposed_multi_merges += 1

    return {
        "total": total,
        "atomic": len(atomic_syllables),
        "multi": multi_merges,
        "jamo": jamo_tokens,
        "fragments": fragments,
        "recomposed_atomic": len(recomposed_atomic_syllables),
        "recomposed_multi": recomposed_multi_merges,
        "max_recomposed_syllables": max_recomposed_syllables,
    }


def print_report(name, stats, normalizer_label):
    print(f"--- {name} ---")
    print(f"vocab size             : {stats['total']}")
    print(f"normalizer             : {normalizer_label}")
    print(f"atomic syllable tokens : {stats['atomic']} ({stats['atomic'] / 11172:.1%} of 11,172)")
    print(f"multi-syllable merges  : {stats['multi']}")
    print(f"jamo tokens            : {stats['jamo']}")
    print(f"recomposed atomic      : {stats['recomposed_atomic']}")
    print(f"recomposed multi       : {stats['recomposed_multi']}")
    print(f"max recomposed span    : {stats['max_recomposed_syllables']}")
