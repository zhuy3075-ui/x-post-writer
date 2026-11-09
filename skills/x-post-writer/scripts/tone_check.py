"""Read-only Chinese prose candidate scanner; not an AI or X policy classifier."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import statistics
import sys


RULES = (
    ("paired_reversal", r"(?:不是|并非)[^。！？!?\n]{1,60}?(?:而是|而在于)", "确认对立是否必要，避免假设读者误解"),
    ("assumed_reversal", r"(?:你以为|看似)[^。！？!?\n]{1,60}?(?:其实|实则)", "核对前半句是否有素材依据"),
    ("announcement", r"(?:核心是|关键在于|真相是|本质是|一句话总结)[：:]", "检查是否多了一层结论宣告"),
    ("stock_bridge", r"综上所述|值得注意的是|不可否认的是|在当今时代", "确认这处过渡是否带来实际信息"),
    ("absolute_promise", r"全网唯一|保证(?:涨粉|赚钱|成功)|稳赚|人人都能|零风险", "检查范围与依据，不能只调整语气"),
    ("engagement_request", r"(?:点赞|转发|关注|收藏|评论|回复)[^。！？!?\n]{0,8}?(?:领取|解锁|公布|扣[1１]|领资料)|互赞|互关|赞够", "检查是否诱导或交换互动"),
    ("withheld_answer", r"答案下次(?:再说|公布)|下期揭晓|先卖个关子", "独立短推应兑现本条的关键承诺"),
    ("punctuation_cluster", r"[！!？?]{3,}|[，,]{2,}", "确认情绪表达或停顿是否需要重复符号"),
)


def mask_code(text):
    """Keep source offsets and line breaks while ignoring fenced code."""
    result = []
    fence_char = None
    fence_size = 0
    for line in text.splitlines(keepends=True):
        marker = re.match(r"^\s{0,3}(`{3,}|~{3,})", line)
        if fence_char is None and marker:
            fence_char = marker.group(1)[0]
            fence_size = len(marker.group(1))
            result.append(re.sub(r"[^\r\n]", " ", line))
        elif fence_char is not None:
            result.append(re.sub(r"[^\r\n]", " ", line))
            if marker and marker.group(1)[0] == fence_char and len(marker.group(1)) >= fence_size:
                if not line[marker.end():].strip():
                    fence_char = None
        else:
            result.append(line)
    return "".join(result)


def location(text, offset):
    start = text.rfind("\n", 0, offset) + 1
    end = text.find("\n", offset)
    line = text[start:end if end >= 0 else len(text)]
    stripped = line.lstrip()
    context = "block_quote" if stripped.startswith(">") else "heading" if re.match(r"#{1,6}\s", stripped) else "body"
    return {
        "line": text.count("\n", 0, offset) + 1,
        "column": offset - start + 1,
        "context": context,
        "line_text": line,
    }


def scan(text):
    active = mask_code(text)
    candidates = []
    for rule, expression, question in RULES:
        for match in re.finditer(expression, active):
            candidates.append({
                "rule": rule,
                "offset": match.start(),
                "match": text[match.start():match.end()],
                "review_question": question,
                **location(text, match.start()),
            })

    starts = {}
    for match in re.finditer(r"(?m)^[ \t]*([^\n]+)", active):
        content = match.group(1).strip()
        if content.startswith(("#", ">")):
            continue
        prefix = re.match(r"[\u3400-\u9fff]{6}", content)
        if prefix:
            offset = match.start(1) + len(match.group(1)) - len(match.group(1).lstrip())
            starts.setdefault(prefix.group(), []).append(offset)
    for prefix, offsets in starts.items():
        if len(offsets) >= 3:
            for offset in offsets:
                candidates.append({"rule": "repeated_line_start", "offset": offset, "match": prefix,
                                   "review_question": "相同起句是否重复同一个意思；正常列表可以保留",
                                   **location(text, offset)})
    candidates.sort(key=lambda item: (item["offset"], item["rule"]))
    for index, candidate in enumerate(candidates, 1):
        candidate["id"] = f"C{index:03d}"

    paragraphs = [re.sub(r"\s", "", part) for part in re.split(r"\n\s*\n", active) if part.strip()]
    units = [len(re.sub(r"\s", "", part)) for part in re.findall(r"[^。！？!?\n]+[。！？!?]*", active) if part.strip()]
    punctuation = Counter(char for char in active if char in "，。！？：；、‘’“”（）《》—…,.!?;:()\"'")
    return {
        "schema_version": 1,
        "scope": "中文表达候选扫描；不是AI来源鉴定或平台违规判定",
        "limitations": [
            "所有命中需逐条语义复核；未命中不代表表达、事实或资格合格",
            "短推不作人机统计推断；长度和标点没有人类目标值",
            "字符计数为Unicode码点，不是X平台加权字符数",
            "句段以中文句末标点及换行切分，不以英文句号分句",
            "计数含标题与引语、排除围栏代码；我字样不证明叙述者或亲历",
        ],
        "metrics": {
            "raw_codepoints": len(text),
            "nonspace_codepoints_excluding_fenced_code": len(re.sub(r"\s", "", active)),
            "paragraphs": len(paragraphs),
            "paragraph_lengths": [len(part) for part in paragraphs],
            "paragraphs_at_most_20_codepoints": sum(len(part) <= 20 for part in paragraphs),
            "sentence_units": len(units),
            "sentence_unit_lengths": units,
            "sentence_unit_mean": round(statistics.mean(units), 2) if units else 0,
            "sentence_unit_population_sd": round(statistics.pstdev(units), 2) if units else 0,
            "punctuation_counts": dict(sorted(punctuation.items())),
            "first_person_token_occurrences": len(re.findall(r"我(?:们)?", active)),
            "candidate_counts": dict(sorted(Counter(item["rule"] for item in candidates).items())),
        },
        "candidates": candidates,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path, help="UTF-8 text file, read only")
    args = parser.parse_args()
    try:
        raw = args.file.read_bytes()
        text = raw.decode("utf-8-sig")
    except (OSError, UnicodeError) as error:
        parser.exit(2, f"Cannot read UTF-8 input {args.file}: {error}\n")
    if "\x00" in text:
        parser.exit(2, f"Input contains NUL and may be binary: {args.file}\n")
    report = scan(text)
    report["input"] = str(args.file)
    report["source_sha256"] = hashlib.sha256(raw).hexdigest()
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
