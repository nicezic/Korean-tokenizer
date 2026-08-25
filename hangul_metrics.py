import unicodedata

SAMPLE = (
    "한글은 조합형 문자다. 초성과 중성, 종성을 조합해 음절을 만든다. "
    "GLM 같은 다국어 모델이 한국어를 처리할 때 토큰 수가 어떻게 달라지는지 확인한다."
)

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
    return {chr(c): b for c, b in zip(code_points, byte_set)}


def summarize_vocab(byte_iter):
    atomic_syllables = set()
    multi_merges = jamo_tokens = fragments = total = 0
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
    return {
        "total": total,
        "atomic": len(atomic_syllables),
        "multi": multi_merges,
        "jamo": jamo_tokens,
        "fragments": fragments,
    }


def nfc_nfd_blowup(token_count_fn, sample=SAMPLE):
    nfc = token_count_fn(unicodedata.normalize("NFC", sample))
    nfd = token_count_fn(unicodedata.normalize("NFD", sample))
    return nfc, nfd, round(nfd / nfc, 2)


def print_report(name, stats, normalizer_label, encode_len_fn):
    nfc, nfd, ratio = nfc_nfd_blowup(encode_len_fn)
    print(f"--- {name} ---")
    print(f"vocab size             : {stats['total']}")
    print(f"normalizer             : {normalizer_label}")
    print(f"atomic syllable tokens : {stats['atomic']} ({stats['atomic'] / 11172:.1%} of 11,172)")
    print(f"multi-syllable merges  : {stats['multi']}")
    print(f"jamo tokens            : {stats['jamo']}")
    print(f"NFC vs NFD sample      : {nfc} vs {nfd} tokens ({ratio}x)")
