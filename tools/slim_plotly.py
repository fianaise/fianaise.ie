"""Move the plotly.js bundle that write_html() inlines into one shared file.

A figure saved with the default include_plotlyjs=True carries all of plotly.js
(about 4.8 MB). This writes the bundle once to figures/lib/ and points each
figure at it, so the browser downloads it once for the whole site.

Usage: python3 -I tools/slim_plotly.py figures/*.html
"""
import os
import re
import sys

BUNDLE = re.compile(r"<script>(/\*\*\s*\*\s*plotly\.js v([0-9.]+).*?)</script>", re.S)

for path in sys.argv[1:]:
    html = open(path, encoding="utf-8").read()
    m = BUNDLE.search(html)
    if not m:
        continue
    lib_dir = os.path.join(os.path.dirname(path), "lib")
    lib_name = f"plotly-{m.group(2)}.min.js"
    os.makedirs(lib_dir, exist_ok=True)
    lib_path = os.path.join(lib_dir, lib_name)
    if not os.path.exists(lib_path):
        open(lib_path, "w", encoding="utf-8").write(m.group(1))
    html = html[: m.start()] + f'<script src="lib/{lib_name}"></script>' + html[m.end():]
    open(path, "w", encoding="utf-8").write(html)
    print(f"{path}: now loads lib/{lib_name}")
