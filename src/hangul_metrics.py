import unicodedata

SAMPLE = (
    "한글은 세종대왕이 직접 만든 백성을 위한 글자다. "
    "글을 모르던 일반 백성이 억울한 일을 겪지 않도록 지어 내어 훈민정음이라 이름 지었고, "
    "지혜로운 사람은 아침에 배워 저녁에 쓸 수 있다고 했다. "
    "자음은 소리를 내는 발음 기관의 모양을 본떠 그렸고, 모음은 하늘과 땅과 사람의 형상에서 빌어 왔다. "
    "입 모양이 미음, 이 모양이 시옷, 목구멍이 이응처럼 글자 자체가 소리의 생김새를 담고 있으니 "
    "배우기 쉽고 쓰기에도 편리하다. "
    "기본 자모 스물넷만으로 음절이 만여 개나 태어나고, 받침을 더하면 만 천백칠십이 개까지 조합할 수 있다. "
    "명사와 조사가 만나고 동사와 어미가 붙으며 문장이 되는데, "
    "글자들이 결합했다가 흩어지는 이 조합의 성질 덕분에 새로운 말과 외래어까지 놀랍게 잘 담아 낸다. "
    "완성된 음절을 통째로 외운 글자가 아니라 부품을 맞춰 조립하는 글자라서 "
    "몇백 년이 지난 오늘날 컴퓨터 시대에도 그 과학적 설계는 여전히 유효하다."
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
    return {chr(c): b for c, b in zip(code_points, byte_set, strict=True)}


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
