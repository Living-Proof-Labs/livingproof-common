# SPDX-License-Identifier: Apache-2.0
"""Check local HTML targets and fragments without network access."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


class Page(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.ids = set()
        self.links = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.add(attrs["id"])
        for attribute in ("href", "src"):
            if attribute in attrs:
                self.links.append(attrs[attribute])


def check_links(root, base_path="/livingproof-common/"):
    root = Path(root).resolve()
    pages = {path.resolve(): Page(path.read_text()) for path in root.rglob("*.html")}
    for path, page in pages.items():
        for link in page.links:
            url = urlsplit(link)
            if url.scheme or url.netloc:
                continue  # External availability is a separate online link check.
            if url.path.startswith('/'):
                if not url.path.startswith(base_path):
                    raise ValueError(f"Link escapes project base path in {path.name}: {link}")
                target = (root / unquote(url.path.removeprefix(base_path))).resolve()
            else:
                target = (path.parent / unquote(url.path)).resolve() if url.path else path
            if target.is_dir():
                target /= "index.html"
            if not target.is_relative_to(root) or not target.exists():
                raise ValueError(f"Broken local link in {path.name}: {link}")
            if url.fragment and target in pages and unquote(url.fragment) not in pages[target].ids:
                raise ValueError(f"Broken local fragment in {path.name}: {link}")
