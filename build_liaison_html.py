"""Liaison Excel → Sankey viewer を生成するラッパ（template + data を順に呼ぶ）。"""

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Liaison Excel → Sankey viewer")
    parser.add_argument("--input", required=True, help="正規化 Liaison Excel")
    parser.add_argument("--outdir", required=True, help="出力 viewer フォルダ")
    parser.add_argument("--precision", type=int, default=None, help="weight_split の丸め桁数")
    parser.add_argument("--debug", action="store_true", help="app.js にデバッグログを埋め込む")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent

    # 1) データ生成
    cmd_data = [
        sys.executable,
        str(script_dir / "build_liaison_data.py"),
        "--input", args.input,
        "--outdir", args.outdir,
    ]
    if args.precision is not None:
        cmd_data.extend(["--precision", str(args.precision)])
    r1 = subprocess.run(cmd_data)
    if r1.returncode != 0:
        sys.exit(r1.returncode)

    # 2) テンプレート生成
    cmd_tpl = [
        sys.executable,
        str(script_dir / "build_liaison_template.py"),
        "--outdir", args.outdir,
    ]
    if args.debug:
        cmd_tpl.append("--debug")
    r2 = subprocess.run(cmd_tpl)
    if r2.returncode != 0:
        sys.exit(r2.returncode)

    print(f"viewer: {args.outdir} (index.html, app.js, data.js, viewer.css, edges_*.csv)")


if __name__ == "__main__":
    main()
