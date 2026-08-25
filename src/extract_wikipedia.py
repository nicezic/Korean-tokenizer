import argparse
import bz2
import html
import json
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path

import mwparserfromhell


def local_name(tag):
    return tag.rsplit("}", 1)[-1]


def direct_child(element, name):
    for child in element:
        if local_name(child.tag) == name:
            return child
    return None


def page_text(page):
    revision = direct_child(page, "revision")
    if revision is None:
        return None
    text = direct_child(revision, "text")
    return None if text is None else text.text


def chunk_paragraph(text, max_chars):
    words = text.split()
    chunk = []
    size = 0
    for word in words:
        if len(word) > max_chars:
            if chunk:
                yield " ".join(chunk)
                chunk = []
                size = 0
            for start in range(0, len(word), max_chars):
                yield word[start : start + max_chars]
            continue
        needed = len(word) + (1 if chunk else 0)
        if chunk and size + needed > max_chars:
            yield " ".join(chunk)
            chunk = [word]
            size = len(word)
        else:
            chunk.append(word)
            size += needed
    if chunk:
        yield " ".join(chunk)


def clean_wikitext(raw, max_chars):
    stripped = mwparserfromhell.parse(raw).strip_code(normalize=True, collapse=True)
    stripped = unicodedata.normalize("NFC", html.unescape(stripped).replace("\xa0", " "))
    for paragraph in stripped.splitlines():
        paragraph = " ".join(paragraph.split())
        if not paragraph:
            continue
        yield from chunk_paragraph(paragraph, max_chars)


def iter_articles(path, max_chars):
    with bz2.open(path, "rb") as source:
        context = ET.iterparse(source, events=("start", "end"))
        _, root = next(context)
        for event, element in context:
            if event != "end" or local_name(element.tag) != "page":
                continue
            namespace = direct_child(element, "ns")
            redirect = direct_child(element, "redirect")
            raw = page_text(element)
            if namespace is not None and namespace.text == "0" and redirect is None and raw:
                paragraphs = list(clean_wikitext(raw, max_chars))
                if paragraphs:
                    yield paragraphs
            root.clear()


def main():
    parser = argparse.ArgumentParser(description="Extract plain article text from Wikimedia XML bz2 shards.")
    parser.add_argument("shards", nargs="+", type=Path)
    parser.add_argument("--output", type=Path, default=Path("data/kowiki.txt"))
    parser.add_argument("--stats", type=Path, default=Path("data/extract_stats.json"))
    parser.add_argument("--max-line-chars", type=int, default=2000)
    args = parser.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    stats = {"articles": 0, "lines": 0, "characters": 0, "shards": []}
    with args.output.open("w", encoding="utf-8", newline="\n") as output:
        for shard in args.shards:
            shard_articles = shard_lines = shard_chars = 0
            for paragraphs in iter_articles(shard, args.max_line_chars):
                for paragraph in paragraphs:
                    output.write(paragraph + "\n")
                    shard_lines += 1
                    shard_chars += len(paragraph)
                output.write("\n")
                shard_articles += 1
            stats["articles"] += shard_articles
            stats["lines"] += shard_lines
            stats["characters"] += shard_chars
            stats["shards"].append(
                {"path": str(shard), "articles": shard_articles, "lines": shard_lines, "characters": shard_chars}
            )

    stats["output_bytes"] = args.output.stat().st_size
    args.stats.write_text(json.dumps(stats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
