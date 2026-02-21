"""index.html / viewer.css / app.js を生成する CLI（ViewerTemplateBuilder を呼ぶだけ）。"""

import argparse
import sys
from pathlib import Path

# プロジェクトルートを path に追加して util を import
sys.path.insert(0, str(Path(__file__).resolve().parent))
from util.viewer_template_builder import ViewerTemplateBuilder


def main() -> None:
    parser = argparse.ArgumentParser(description="viewer テンプレート（index.html, viewer.css, app.js）を生成")
    parser.add_argument("--outdir", required=True, help="出力フォルダ")
    parser.add_argument("--debug", action="store_true", help="app.js に plotly_click デバッグログを埋め込む")
    args = parser.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    builder = ViewerTemplateBuilder()
    (outdir / "index.html").write_text(builder.render_index_html(), encoding="utf-8")
    (outdir / "viewer.css").write_text(builder.render_viewer_css(), encoding="utf-8")
    (outdir / "app.js").write_text(builder.render_app_js(debug=args.debug), encoding="utf-8")

    print(f"index.html, viewer.css, app.js: {outdir}")


if __name__ == "__main__":
    main()
