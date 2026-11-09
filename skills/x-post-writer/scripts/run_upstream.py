"""Run pinned, unchanged lieflat scripts locally; never rewrite the input."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys


SKILL = Path(__file__).resolve().parent.parent
VENDOR = SKILL / "vendor/lieflat-less-ai-tone"
REVISION = "53160078a04926d98de57a233549612d1b89bdc9"
FILES = {"scripts/detect.py", "scripts/report.py", "references/semantic-criteria.md", "LICENSE"}
LABELS = {
    "rename": {"0组", "1组", "2组", "3组及以上", "无法判断"},
    "cohesion": {"表面有连接词实际关系不清", "明确承接", "有关但转换突然", "主题跳转缺少说明", "无法判断"},
    "colon": {"引语或人物发言", "标题时间比例元数据或版式用途", "定义或解释", "空转提示", "结论提示", "其他正文冒号", "无法判断"},
    "iso3": {"高度同构", "部分同构", "只有词语重复句法不同", "只有语义并列句法不同", "无同构关系", "无法判断"},
}


def verified_upstream():
    manifest = json.loads((VENDOR / "UPSTREAM.json").read_text(encoding="utf-8"))
    if manifest["commit"] != REVISION or set(manifest["files"]) != FILES:
        raise ValueError("上游版本或文件清单不匹配；请核对安装，不自动下载")
    for name, expected in manifest["files"].items():
        actual = hashlib.sha256((VENDOR / name).read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(f"上游文件校验失败：{name}")
    return manifest


def read_prose(path):
    raw = path.read_bytes()
    text = raw.decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
    if not text.strip() or "\x00" in text:
        raise ValueError(f"输入为空或含NUL，不是可用文稿：{path}")
    return raw, text


def run(script, *arguments):
    command = [sys.executable, "-B", "-X", "utf8", str(script), *map(str, arguments)]
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", timeout=120)
    if result.returncode:
        raise ValueError(f"原脚本执行失败 {script.name}：{result.stderr.strip() or result.stdout.strip()}")
    return result.stdout


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")


def scan(args, upstream):
    raw, text = read_prose(args.input)
    hanzi = len(re.findall(r"[一-鿿]", text))
    args.out_dir.mkdir(parents=True, exist_ok=False)
    snapshot = args.out_dir / "输入稿.md"
    snapshot.write_text(text, encoding="utf-8", newline="\n")
    detector = VENDOR / "scripts/detect.py"
    candidates = json.loads(run(detector, snapshot, "--candidates"))
    write_json(args.out_dir / "原仓库候选.json", candidates)
    if hanzi >= 500:
        metrics = json.loads(run(detector, snapshot, "--json"))
        write_json(args.out_dir / "原仓库检测.json", metrics)
        (args.out_dir / "原仓库检测.txt").write_text(run(detector, snapshot), encoding="utf-8", newline="\n")
    supplement = json.loads(run(SKILL / "scripts/tone_check.py", snapshot))
    write_json(args.out_dir / "补充表达扫描.json", supplement)
    record = {
        "upstream_commit": upstream["commit"], "upstream_files": upstream["files"],
        "source": str(args.input.resolve()), "source_sha256": hashlib.sha256(raw).hexdigest(),
        "snapshot_sha256": hashlib.sha256(snapshot.read_bytes()).hexdigest(),
        "normalization": "仅快照移除UTF-8 BOM并统一LF；原文件不改",
        "hanzi": hanzi, "measurement_executed": hanzi >= 500,
        "measurement_note": "已运行原版常规CLI" if hanzi >= 500 else "不足500汉字，跳过常规统计；已运行原版候选提取，需逐句复核",
        "semantic_candidates": candidates["meta"], "semantic_labels_created_by_script": False,
        "supplement_note": "补充表达扫描由本技能旧版工具提供，与原版输出分开保存",
    }
    if args.input.read_bytes() != raw:
        raise ValueError(f"源文件在运行期间被更改：{args.input}；请使用新输出目录重新检测")
    write_json(args.out_dir / "运行记录.json", record)
    return {"output": str(args.out_dir), **record}


def check_semantic(path, before):
    labeled = json.loads(path.read_text(encoding="utf-8-sig"))
    original = json.loads((before / "原仓库候选.json").read_text(encoding="utf-8"))
    if labeled.get("meta") != original["meta"]:
        raise ValueError("语义判读不能改写原始候选计数")
    for group, allowed in LABELS.items():
        rows = labeled.get(group, [])
        if len(rows) != len(original[group]):
            raise ValueError(f"语义候选数量不一致：{group}")
        for item, raw in zip(rows, original[group]):
            if any(item.get(key) != value for key, value in raw.items()):
                raise ValueError(f"原始候选被改写：{group}，行{raw.get('line')}")
            if item.get("label") not in allowed or item.get("confidence") not in {"高", "中", "低"}:
                raise ValueError(f"缺少有效的语义标签/置信度：{group}，行{raw.get('line')}")
            if not isinstance(item.get("reason"), str) or not item["reason"].strip():
                raise ValueError(f"缺少逐条理由：{group}，行{raw.get('line')}")


def compare(args, upstream):
    if args.out.exists():
        raise ValueError(f"报告路径已存在，拒绝覆盖：{args.out}")
    for directory in (args.before, args.after):
        record = json.loads((directory / "运行记录.json").read_text(encoding="utf-8"))
        if record["upstream_commit"] != upstream["commit"] or not record["measurement_executed"]:
            raise ValueError(f"无法生成常规统计对比：{directory}；短稿请逐句对照，不凑字或伪造检测JSON")
        read_prose(directory / "输入稿.md")
        if hashlib.sha256((directory / "输入稿.md").read_bytes()).hexdigest() != record["snapshot_sha256"]:
            raise ValueError(f"检测后的快照已改变：{directory}")
        measured = json.loads(run(VENDOR / "scripts/detect.py", directory / "输入稿.md", "--json"))
        saved = json.loads((directory / "原仓库检测.json").read_text(encoding="utf-8"))
        if measured != saved:
            raise ValueError(f"保存的检测JSON与原版重新计算不一致：{directory}")
    command = [args.before / "输入稿.md", args.after / "输入稿.md",
               args.before / "原仓库检测.json", args.after / "原仓库检测.json"]
    if args.semantic:
        check_semantic(args.semantic, args.before)
        command.extend(["--semantic", args.semantic])
    command.extend(["--format", args.format, "--out", args.out])
    run(VENDOR / "scripts/report.py", *command)
    return {"report": str(args.out), "upstream_commit": upstream["commit"],
            "semantic_included": bool(args.semantic), "format": args.format}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="mode", required=True)
    scan_parser = commands.add_parser("scan")
    scan_parser.add_argument("input", type=Path)
    scan_parser.add_argument("--out-dir", type=Path, required=True, help="新建目录，不能已存在")
    compare_parser = commands.add_parser("compare")
    compare_parser.add_argument("before", type=Path)
    compare_parser.add_argument("after", type=Path)
    compare_parser.add_argument("--semantic", type=Path, help="完整逐条标注的改前候选JSON")
    compare_parser.add_argument("--format", choices=["md", "html"], default="md")
    compare_parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        upstream = verified_upstream()
        result = scan(args, upstream) if args.mode == "scan" else compare(args, upstream)
    except (OSError, ValueError, KeyError, subprocess.TimeoutExpired) as error:
        parser.exit(2, f"{error}\n")
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
