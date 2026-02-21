"""TDoc List Excel → 正規化 Liaison Excel を作成する."""

import argparse
import re
import sys
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook


def extract_meeting_id(filepath: str) -> str:
    """ファイル名から会合番号 (#xxx) を抽出する."""
    m = re.search(r"#\d+", Path(filepath).name)
    if not m:
        raise ValueError(f"会合番号が見つかりません: {filepath}")
    return m.group()


def load_liaison_rows(filepath: str, meeting_id: str) -> pd.DataFrame:
    """1ファイル分の LS in / LS out 行を抽出・正規化して返す."""
    df = pd.read_excel(filepath, sheet_name="TDoc_List", engine="openpyxl")

    for col in ("Source", "Type", "To"):
        if col not in df.columns:
            raise ValueError(f"必須列 '{col}' が見つかりません: {filepath}")

    ls = df[df["Type"].isin(["LS in", "LS out"])].copy()

    n_in = (ls["Type"] == "LS in").sum()
    n_out = (ls["Type"] == "LS out").sum()
    print(f"  {meeting_id}: LS in={n_in}, LS out={n_out}, 合計={n_in + n_out}")

    rows = []
    for _, r in ls.iterrows():
        src = str(r["Source"]) if pd.notna(r["Source"]) else ""
        to_ = str(r["To"]) if pd.notna(r["To"]) else ""
        typ = r["Type"]

        if typ == "LS in":
            rows.append({"RAN": meeting_id, "Source": src, "Type": typ, "To": "RAN"})
        else:
            rows.append({"RAN": meeting_id, "Source": "RAN", "Type": typ, "To": to_})

    return pd.DataFrame(rows, columns=["RAN", "Source", "Type", "To"])


def style_workbook(path: str) -> None:
    """ヘッダ固定・オートフィルタ・列幅を整える."""
    wb = load_workbook(path)
    ws = wb["liaison"]
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    for letter, width in {"A": 10, "B": 30, "C": 10, "D": 50}.items():
        ws.column_dimensions[letter].width = width
    wb.save(path)


def main() -> None:
    parser = argparse.ArgumentParser(description="TDoc List → Liaison Excel")
    parser.add_argument("--list", required=True, help="入力ファイルリスト (1行1パス)")
    parser.add_argument("--out", required=True, help="出力Excelパス")
    args = parser.parse_args()

    list_path = Path(args.list)
    if not list_path.exists():
        print(f"ERROR: ファイルリストが見つかりません: {list_path}", file=sys.stderr)
        sys.exit(1)

    files = [
        line.strip()
        for line in list_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    all_frames: list[pd.DataFrame] = []
    for fp in files:
        p = Path(fp)
        if not p.is_absolute():
            p = list_path.parent / p
        if not p.exists():
            print(f"ERROR: 入力ファイルが見つかりません: {p}", file=sys.stderr)
            sys.exit(1)

        meeting_id = extract_meeting_id(str(p))
        print(f"処理中: {p.name}")
        frame = load_liaison_rows(str(p), meeting_id)
        all_frames.append(frame)

    result = pd.concat(all_frames, ignore_index=True)
    print(f"\n出力行数(ヘッダ除く): {len(result)}")

    out_path = Path(args.out)
    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        result.to_excel(writer, sheet_name="liaison", index=False)

    style_workbook(str(out_path))
    print(f"出力完了: {out_path}")


if __name__ == "__main__":
    main()
