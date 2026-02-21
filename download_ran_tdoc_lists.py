#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
download_ran_tdoc_lists.py
- 3GPP RAN Plenary (TSG_RAN/TSG_RAN/TSGR_xxx*/Docs) から
  TDoc_List_Meeting_RAN#xxx(.xlsx) / #xxx-e(.xlsx) を範囲指定で自動ダウンロードする。

例:
  python download_ran_tdoc_lists.py --range 90-110 --outdir out_tdoc_lists
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Tuple
from urllib.parse import unquote, urljoin

import requests

# optional: BeautifulSoup (recommended)
try:
    from bs4 import BeautifulSoup  # type: ignore
except Exception:
    BeautifulSoup = None  # fallback to regex parsing


BASE = "https://www.3gpp.org/ftp/tsg_ran/TSG_RAN/"
TDOC_RE = re.compile(
    r"TDoc_List_Meeting_RAN#(?P<num>\d+)(?P<suffix>-e)?\.xlsx$", re.IGNORECASE
)


def parse_range(expr: str) -> list[int]:
    m = re.fullmatch(r"\s*(\d+)\s*-\s*(\d+)\s*", expr)
    if not m:
        raise ValueError(f"--range は 90-110 形式で指定してください: {expr!r}")
    a = int(m.group(1))
    b = int(m.group(2))
    if a > b:
        a, b = b, a
    return list(range(a, b + 1))


def iter_candidate_docs_urls(n: int) -> Iterable[str]:
    """通常フォルダ → e会合フォルダの順で候補URLを返す。"""
    yield urljoin(BASE, f"TSGR_{n}/Docs/")
    yield urljoin(BASE, f"TSGR_{n}e/Docs/")


def fetch_text(
    url: str, *, timeout: int
) -> Tuple[Optional[str], Optional[int], Optional[str]]:
    """Docs一覧HTMLを取得。戻り値: (text, status_code, error_msg)。"""
    try:
        r = requests.get(
            url,
            timeout=timeout,
            headers={"User-Agent": "Mozilla/5.0 (tdoc-downloader)"},
        )
        if r.status_code != 200:
            return None, r.status_code, f"HTTP_{r.status_code}"
        r.encoding = r.apparent_encoding or "utf-8"
        return r.text, r.status_code, None
    except requests.RequestException as e:
        return None, None, f"REQ_ERROR:{e.__class__.__name__}"


def find_tdoc_href_from_listing(html: str, n: int) -> Optional[str]:
    """HTMLのディレクトリ一覧から会合番号 n の TDoc List xlsx の href を1つ返す。"""
    if BeautifulSoup is not None:
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.find_all("a"):
            text = (a.get_text() or "").strip()
            m = TDOC_RE.match(text)
            if not m:
                continue
            if int(m.group("num")) != n:
                continue
            href = a.get("href")
            if href:
                return href
        return None

    for m in re.finditer(
        r'href="([^"]+)".*?>\s*(TDoc_List_Meeting_RAN#[^<]+\.xlsx)\s*<',
        html,
        re.IGNORECASE | re.DOTALL,
    ):
        fname = m.group(2).strip()
        mm = TDOC_RE.match(fname)
        if mm and int(mm.group("num")) == n:
            return m.group(1)
    return None


def download_file(
    url: str, out_path: Path, *, timeout: int, overwrite: bool
) -> Tuple[bool, Optional[int], str, int]:
    """
    ファイルをダウンロード。
    戻り値: (成功, http_status, status, bytes)
    status: OK / SKIPPED_EXISTS / DOWNLOAD_ERROR(HTTP_xxx or REQ_ERROR)
    """
    if out_path.exists() and not overwrite:
        return False, None, "SKIPPED_EXISTS", out_path.stat().st_size

    out_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with requests.get(
            url,
            stream=True,
            timeout=timeout,
            headers={"User-Agent": "Mozilla/5.0 (tdoc-downloader)"},
        ) as r:
            if r.status_code != 200:
                return False, r.status_code, "DOWNLOAD_ERROR", 0
            tmp = out_path.with_suffix(out_path.suffix + ".part")
            size = 0
            with open(tmp, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 1024):
                    if not chunk:
                        continue
                    f.write(chunk)
                    size += len(chunk)
            os.replace(tmp, out_path)
            return True, r.status_code, "OK", size
    except requests.RequestException:
        return False, None, "DOWNLOAD_ERROR", 0


@dataclass
class ManifestRow:
    meeting: int
    chosen_folder: str
    url: str
    status: str
    http_status: str
    saved_path: str
    bytes: int


def main() -> None:
    ap = argparse.ArgumentParser(
        description="3GPP RAN Plenary の TDoc List xlsx を範囲指定で一括ダウンロード"
    )
    ap.add_argument("--range", required=True, help="例: 90-110")
    ap.add_argument("--outdir", required=True, help="出力フォルダ")
    ap.add_argument(
        "--sleep",
        type=float,
        default=0.2,
        help="リクエスト間スリープ秒（デフォルト 0.2）",
    )
    ap.add_argument(
        "--overwrite",
        action="store_true",
        help="既存ファイルを上書きする",
    )
    ap.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="HTTPタイムアウト秒（デフォルト 30）",
    )
    ap.add_argument(
        "--manifest",
        default="",
        help="取得結果CSVのパス（デフォルト: <outdir>/manifest.csv）",
    )
    args = ap.parse_args()

    meetings = parse_range(args.range)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    manifest_path = (
        Path(args.manifest) if args.manifest else (outdir / "manifest.csv")
    )
    rows: list[ManifestRow] = []

    for n in meetings:
        chosen_folder = ""
        file_url = ""
        status = ""
        http_status = ""
        saved_path = ""
        size = 0

        # 1) どの Docs フォルダに TDoc List があるか探す
        found = False
        for docs_url in iter_candidate_docs_urls(n):
            html, code, err = fetch_text(docs_url, timeout=args.timeout)
            time.sleep(args.sleep)

            if html is None:
                # フォルダなし or 取得失敗
                if not chosen_folder:
                    chosen_folder = docs_url
                    status = "NOT_FOUND"
                    http_status = str(code) if code is not None else ""
                continue

            href = find_tdoc_href_from_listing(html, n)
            if not href:
                # Docs は取れたが TDoc List が見つからない
                if not found:
                    chosen_folder = docs_url
                    status = "NO_TDOC_LIST"
                    http_status = str(code) if code is not None else ""
                continue

            chosen_folder = docs_url
            file_url = urljoin(docs_url, href)
            found = True
            break

        if not found:
            if status == "":
                status = "NOT_FOUND"
            rows.append(
                ManifestRow(
                    n, chosen_folder, file_url, status, http_status, saved_path, size
                )
            )
            print(f"[{n}] {status}")
            continue

        # 2) ダウンロード（ファイル名の %23 等をデコード）
        filename = unquote(file_url.split("/")[-1])
        out_path = outdir / filename
        ok, code, dstatus, size = download_file(
            file_url, out_path, timeout=args.timeout, overwrite=args.overwrite
        )
        time.sleep(args.sleep)

        status = dstatus
        http_status = str(code) if code is not None else ""
        saved_path = str(out_path) if (ok or out_path.exists()) else ""

        rows.append(
            ManifestRow(
                n, chosen_folder, file_url, status, http_status, saved_path, size
            )
        )
        print(f"[{n}] {status} {http_status} -> {saved_path or '-'}")

    # manifest 書き出し
    with open(manifest_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "meeting",
                "chosen_folder",
                "url",
                "status",
                "http_status",
                "saved_path",
                "bytes",
            ]
        )
        for r in rows:
            w.writerow(
                [
                    r.meeting,
                    r.chosen_folder,
                    r.url,
                    r.status,
                    r.http_status,
                    r.saved_path,
                    r.bytes,
                ]
            )

    print(f"manifest: {manifest_path}")


if __name__ == "__main__":
    main()
