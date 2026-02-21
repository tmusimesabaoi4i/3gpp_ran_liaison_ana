"""Liaison Excel → data.js / edges_by_meeting.csv / edges_total.csv（edge_key 付き）を生成する。"""

import argparse
import json
import sys
from pathlib import Path

import pandas as pd


def _src_label(src: str) -> str:
    return "RAN" if (src == "RAN" or pd.isna(src) or str(src).strip() == "") else f"{str(src).strip()} (src)"


def _dst_label(t: str) -> str:
    return "RAN" if (t == "RAN" or pd.isna(t) or str(t).strip() == "") else f"{str(t).strip()} (dst)"


def _edge_key(dir_: str, from_: str, to_: str) -> str:
    return f"{dir_}|||{from_}|||{to_}"


def build_edges(df: pd.DataFrame, precision: int | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    liaison 行から edges_by_meeting と edges_total を構築。
    edge_key = dir + "|||" + from + "|||" + to を付与。
    """
    rows: list[dict] = []

    for _, r in df.iterrows():
        meeting = r["RAN"]
        typ = r["Type"]
        if typ == "LS in":
            src = str(r["Source"]).strip() if pd.notna(r["Source"]) else ""
            from_ = _src_label(src)
            to_ = "RAN"
            rows.append({
                "meeting": meeting, "dir": "in",
                "from": from_, "to": to_,
                "raw_count": 1, "weight_raw": 1.0, "weight_split": 1.0,
            })
        else:
            tos = [t.strip() for t in str(r["To"]).split(",") if t.strip()]
            if not tos:
                continue
            k = len(tos)
            for t in tos:
                to_ = _dst_label(t)
                rows.append({
                    "meeting": meeting, "dir": "out",
                    "from": "RAN", "to": to_,
                    "raw_count": 1, "weight_raw": 1.0, "weight_split": 1.0 / k,
                })

    edge_df = pd.DataFrame(rows)
    agg = edge_df.groupby(["meeting", "dir", "from", "to"], as_index=False).agg(
        raw_count=("raw_count", "sum"),
        weight_raw=("weight_raw", "sum"),
        weight_split=("weight_split", "sum"),
    )

    def add_edge_key(a: pd.DataFrame) -> pd.DataFrame:
        a = a.copy()
        a["edge_key"] = a.apply(
            lambda r: _edge_key(str(r["dir"]), str(r["from"]), str(r["to"])),
            axis=1
        )
        if precision is not None:
            a["weight_split"] = a["weight_split"].round(precision)
        return a

    edges_by_meeting = add_edge_key(agg)
    edges_total = add_edge_key(
        agg.groupby(["dir", "from", "to"], as_index=False).agg(
            raw_count=("raw_count", "sum"),
            weight_raw=("weight_raw", "sum"),
            weight_split=("weight_split", "sum"),
        )
    )
    return edges_by_meeting, edges_total


def validate_edges(df: pd.DataFrame, edges_by_meeting: pd.DataFrame) -> None:
    """検算: meeting ごと・all で weight 合計が LS in/out 行数（および out explode 数）と一致するか."""
    for meeting in sorted(df["RAN"].unique()):
        sub = df[df["RAN"] == meeting]
        n_in = (sub["Type"] == "LS in").sum()
        n_out = (sub["Type"] == "LS out").sum()
        out_explode = sum(len([t for t in str(r["To"]).split(",") if t.strip()])
                        for _, r in sub[sub["Type"] == "LS out"].iterrows())
        e = edges_by_meeting[edges_by_meeting["meeting"] == meeting]
        sum_in = e[e["dir"] == "in"]["weight_raw"].sum()
        sum_out_raw = e[e["dir"] == "out"]["weight_raw"].sum()
        sum_out_split = e[e["dir"] == "out"]["weight_split"].sum()
        ok_in = abs(sum_in - n_in) < 1e-6
        ok_raw = abs(sum_out_raw - out_explode) < 1e-6
        ok_split = abs(sum_out_split - n_out) < 1e-6
        print(f"  検算 {meeting}: LS in={n_in} sum_in={sum_in:.0f} ok={ok_in} | "
              f"LS out行={n_out} explode={out_explode} sum_raw={sum_out_raw:.0f} ok={ok_raw} | "
              f"sum_split={sum_out_split:.2f} ok={ok_split}")
        if not (ok_in and ok_raw and ok_split):
            print("    WARN: 数量不整合", file=sys.stderr)

    n_in_all = (df["Type"] == "LS in").sum()
    n_out_all = (df["Type"] == "LS out").sum()
    out_explode_all = sum(len([t for t in str(r["To"]).split(",") if t.strip()])
                         for _, r in df[df["Type"] == "LS out"].iterrows())
    sum_in_all = edges_by_meeting[edges_by_meeting["dir"] == "in"]["weight_raw"].sum()
    sum_raw_all = edges_by_meeting[edges_by_meeting["dir"] == "out"]["weight_raw"].sum()
    sum_split_all = edges_by_meeting[edges_by_meeting["dir"] == "out"]["weight_split"].sum()
    print(f"  検算 all: LS in={n_in_all} sum_in={sum_in_all:.0f} | "
          f"explode={out_explode_all} sum_raw={sum_raw_all:.0f} | "
          f"LS out行={n_out_all} sum_split={sum_split_all:.2f}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Liaison Excel → data.js, edges CSV")
    parser.add_argument("--input", required=True, help="正規化 Liaison Excel")
    parser.add_argument("--outdir", required=True, help="出力フォルダ")
    parser.add_argument("--precision", type=int, default=None,
                        help="weight_split の丸め桁数（例: 6）")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"ERROR: 入力ファイルが見つかりません: {input_path}", file=sys.stderr)
        sys.exit(1)

    df = pd.read_excel(input_path, sheet_name="liaison", engine="openpyxl")
    print(f"読み込み行数: {len(df)}")

    for meeting in sorted(df["RAN"].unique()):
        sub = df[df["RAN"] == meeting]
        n_in = (sub["Type"] == "LS in").sum()
        n_out = (sub["Type"] == "LS out").sum()
        print(f"  {meeting}: LS in={n_in}, LS out={n_out}")

    edges_by_meeting, edges_total = build_edges(df, precision=args.precision)

    print("検算（meeting ごと・all）:")
    validate_edges(df, edges_by_meeting)

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    edges_by_meeting.to_csv(outdir / "edges_by_meeting.csv", index=False, encoding="utf-8-sig")
    edges_total.to_csv(outdir / "edges_total.csv", index=False, encoding="utf-8-sig")
    print(f"edges_by_meeting.csv, edges_total.csv: {outdir}")

    meetings = sorted(df["RAN"].unique().tolist())
    data_js = {
        "meetings": meetings,
        "edgesByMeeting": edges_by_meeting.fillna("").to_dict(orient="records"),
        "edgesTotal": edges_total.fillna("").to_dict(orient="records"),
    }
    content = "window.LIAISON_DATA = " + json.dumps(data_js, ensure_ascii=False) + ";\n"
    (outdir / "data.js").write_text(content, encoding="utf-8")
    print(f"data.js: {outdir / 'data.js'}")


if __name__ == "__main__":
    main()
