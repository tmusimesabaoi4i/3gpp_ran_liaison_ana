#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
manifest.csv の saved_path から files.txt を生成する。
build_liaison_excel.py の --list に渡す入力リストを、手作業ではなく manifest から自動生成するためのスクリプト。

使い方:
  python manifest_to_files_txt.py out/raw_90_110/manifest.csv
  → out/raw_90_110/files.txt が生成される（manifest と同じディレクトリ）。
"""

import argparse
import csv
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser(description="manifest.csv から files.txt を生成")
    ap.add_argument("manifest", help="manifest.csv のパス")
    ap.add_argument(
        "-o", "--output",
        default=None,
        help="出力 files.txt のパス（省略時は manifest と同じディレクトリの files.txt）",
    )
    args = ap.parse_args()

    m = Path(args.manifest)
    if not m.exists():
        raise SystemExit(f"ERROR: ファイルが見つかりません: {m}")

    out = Path(args.output) if args.output else (m.parent / "files.txt")

    rows: list[str] = []
    with m.open("r", encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            if r.get("status") in ("OK", "SKIPPED_EXISTS") and r.get("saved_path"):
                path = Path(r["saved_path"])
                # manifest と同じディレクトリに xlsx がある想定ならファイル名のみでよい
                if path.parent == m.parent:
                    rows.append(path.name)
                else:
                    rows.append(r["saved_path"])

    rows = sorted(set(rows))
    out.write_text("\n".join(rows) + "\n", encoding="utf-8")
    print(f"wrote {out}  n={len(rows)}")


if __name__ == "__main__":
    main()
