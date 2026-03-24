#!/usr/bin/env python3
"""Scrape Electrobun docs from blackboard.sh into a local docs/ folder as markdown."""

import os
import re
import time
import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md

BASE_URL = "https://blackboard.sh"

DOC_PATHS = [
    # Getting Started
    "/electrobun/docs/guides/quick-start",
    "/electrobun/docs/guides/what-is-electrobun",
    "/electrobun/docs/guides/hello-world",
    "/electrobun/docs/guides/creating-ui",
    "/electrobun/docs/guides/bundling-and-distribution",
    # Advanced Guides
    "/electrobun/docs/guides/cross-platform-development",
    "/electrobun/docs/guides/compatability",
    "/electrobun/docs/guides/code-signing",
    "/electrobun/docs/guides/architecture/overview",
    "/electrobun/docs/guides/architecture/webview-tag",
    "/electrobun/docs/guides/updates",
    # Bun APIs
    "/electrobun/docs/apis/bun",
    "/electrobun/docs/apis/browser-window",
    "/electrobun/docs/apis/browser-view",
    "/electrobun/docs/apis/webgpu",
    "/electrobun/docs/apis/utils",
    "/electrobun/docs/apis/context-menu",
    "/electrobun/docs/apis/application-menu",
    "/electrobun/docs/apis/paths",
    "/electrobun/docs/apis/tray",
    "/electrobun/docs/apis/updater",
    "/electrobun/docs/apis/events",
    # Browser APIs
    "/electrobun/docs/apis/browser/electroview-class",
    "/electrobun/docs/apis/browser/electrobun-webview-tag",
    "/electrobun/docs/apis/browser/draggable-regions",
    "/electrobun/docs/apis/browser/global-properties",
    "/electrobun/docs/apis/browser/wgpu-tag",
    # CLI & Configuration
    "/electrobun/docs/apis/cli/build-configuration",
    "/electrobun/docs/apis/cli/cli-args",
    "/electrobun/docs/apis/bundled-assets",
    "/electrobun/docs/apis/bundling-cef",
    "/electrobun/docs/apis/application-icons",
]


def slugify_path(path: str) -> str:
    """Convert a URL path to a local file path under docs/."""
    # Strip the /electrobun/docs/ prefix
    rel = path.removeprefix("/electrobun/docs/")
    return rel + ".md"


def extract_doc_content(soup: BeautifulSoup) -> str:
    """Extract the main documentation content from the page."""
    # Try common content containers - adjust selectors as needed
    for selector in ["article", "main", '[class*="content"]', '[class*="doc"]', '[role="main"]']:
        content = soup.select_one(selector)
        if content:
            return content

    # Fallback: use body
    return soup.body if soup.body else soup


def scrape_page(path: str) -> str | None:
    """Fetch a doc page and return its content as markdown."""
    url = BASE_URL + path
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"  ERROR fetching {url}: {e}")
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    # Remove nav, sidebar, footer, scripts, styles
    for tag in soup.select("nav, footer, script, style, [class*='sidebar'], [class*='nav'], [class*='footer']"):
        tag.decompose()

    content = extract_doc_content(soup)
    markdown = md(str(content), heading_style="ATX", code_language_callback=lambda el: el.get("class", [""])[0].removeprefix("language-") if el.get("class") else "")

    # Clean up excessive blank lines
    markdown = re.sub(r"\n{3,}", "\n\n", markdown).strip()
    return markdown


def main():
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs")
    os.makedirs(out_dir, exist_ok=True)

    total = len(DOC_PATHS)
    for i, path in enumerate(DOC_PATHS, 1):
        local_file = os.path.join(out_dir, slugify_path(path))
        os.makedirs(os.path.dirname(local_file), exist_ok=True)

        print(f"[{i}/{total}] {path}")
        content = scrape_page(path)
        if content:
            with open(local_file, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"  -> {local_file}")
        else:
            print(f"  SKIPPED")

        # Be polite to the server
        if i < total:
            time.sleep(0.5)

    print(f"\nDone! {total} pages scraped into {out_dir}/")


if __name__ == "__main__":
    main()
