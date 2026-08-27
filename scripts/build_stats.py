#!/usr/bin/env python3
"""Generate stats-dark.svg / stats-light.svg from the GitHub API.

Self-contained replacement for github-readme-stats, which is frequently
rate-limited. Run locally, or via .github/workflows/stats.yml on a schedule.
Set GITHUB_TOKEN to raise the API rate limit.
"""

import json
import os
import urllib.error
import urllib.request

USER = "longtimeno-c"
API = "https://api.github.com"

HEADERS = {"User-Agent": "stats-builder", "Accept": "application/vnd.github+json"}
if os.environ.get("GITHUB_TOKEN"):
    HEADERS["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]

# Reported as "other"; not worth a slice of their own.
LANG_SKIP = {"Makefile", "Batchfile", "Dockerfile", "Shell", "CSS", "SCSS"}

LANG_COLORS = {
    "TypeScript": "#3178c6",
    "JavaScript": "#f1e05a",
    "Python": "#3572a5",
    "Swift": "#f05138",
    "C++": "#f34b7d",
    "C": "#555555",
    "Java": "#b07219",
    "Kotlin": "#a97bff",
    "Ruby": "#701516",
    "HTML": "#e34c26",
    "EJS": "#a91e50",
    "Assembly": "#6e4c13",
    "Vue": "#41b883",
    "Go": "#00add8",
    "Rust": "#dea584",
}
FALLBACK_COLORS = ["#58a6ff", "#a371f7", "#3fb950", "#f0883e", "#db61a2", "#e3b341"]


def get(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def paged(url):
    out, page = [], 1
    while True:
        batch = get(f"{url}{'&' if '?' in url else '?'}per_page=100&page={page}")
        out.extend(batch)
        if len(batch) < 100:
            return out
        page += 1


def collect():
    repos = paged(f"{API}/users/{USER}/repos")
    own = [r for r in repos if not r["fork"]]

    langs = {}
    for repo in own:
        try:
            for name, count in get(repo["languages_url"]).items():
                if name not in LANG_SKIP:
                    langs[name] = langs.get(name, 0) + count
        except urllib.error.HTTPError:
            continue

    commits = get(f"{API}/search/commits?q=author:{USER}&per_page=1")
    prs = get(f"{API}/search/issues?q=author:{USER}+type:pr&per_page=1")
    merged = get(f"{API}/search/issues?q=author:{USER}+type:pr+is:merged&per_page=1")

    return {
        "repos": len(own),
        "stars": sum(r["stargazers_count"] for r in own),
        "commits": commits["total_count"],
        "prs": prs["total_count"],
        "merged": merged["total_count"],
        "contributed": len({r["full_name"].split("/")[0] for r in repos if r["fork"]}),
        "followers": get(f"{API}/users/{USER}")["followers"],
        "langs": sorted(langs.items(), key=lambda kv: -kv[1])[:6],
    }


def esc(text):
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render(data, theme):
    if theme == "dark":
        bg, panel, border = "#0d1117", "#161b22", "#30363d"
        fg, muted, accent = "#e6edf3", "#8b949e", "#58a6ff"
        track = "#21262d"
    else:
        bg, panel, border = "#ffffff", "#f6f8fa", "#d0d7de"
        fg, muted, accent = "#1f2328", "#57606a", "#0969da"
        track = "#eaeef2"

    mono = "ui-monospace,SFMono-Regular,Consolas,monospace"
    tiles = [
        ("repos", data["repos"], "public repos"),
        ("commits", f"{data['commits']:,}", "commits authored"),
        ("merged", data["merged"], "PRs merged"),
        ("prs", data["prs"], "PRs opened"),
    ]

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="900" height="260" '
        f'viewBox="0 0 900 260" role="img" aria-label="GitHub statistics for {USER}">',
        f'<rect width="900" height="260" rx="14" fill="{bg}" stroke="{border}"/>',
        f'<text x="28" y="40" font-family="{mono}" font-size="15" fill="{accent}" '
        f'font-weight="700">{USER} · by the numbers</text>',
    ]

    # Stat tiles across the top.
    for i, (_, value, label) in enumerate(tiles):
        x = 28 + i * 212
        parts.append(
            f'<rect x="{x}" y="58" width="196" height="76" rx="10" '
            f'fill="{panel}" stroke="{border}"/>'
            f'<text x="{x + 16}" y="98" font-family="{mono}" font-size="28" '
            f'font-weight="700" fill="{fg}">{value}</text>'
            f'<text x="{x + 16}" y="120" font-family="{mono}" font-size="12" '
            f'fill="{muted}">{label}</text>'
        )

    parts.append(
        f'<text x="28" y="170" font-family="{mono}" font-size="13" '
        f'fill="{muted}">most used languages</text>'
    )

    # Stacked language bar.
    total = sum(count for _, count in data["langs"]) or 1
    x, bar_w = 28.0, 844.0
    parts.append(
        f'<rect x="28" y="182" width="844" height="14" rx="7" fill="{track}"/>'
    )
    for i, (name, count) in enumerate(data["langs"]):
        w = bar_w * count / total
        color = LANG_COLORS.get(name, FALLBACK_COLORS[i % len(FALLBACK_COLORS)])
        parts.append(f'<rect x="{x:.1f}" y="182" width="{w:.1f}" height="14" fill="{color}"/>')
        x += w
    parts.append(
        f'<rect x="28" y="182" width="844" height="14" rx="7" fill="none" stroke="{bg}" stroke-width="2"/>'
    )

    # Legend, two rows of three.
    for i, (name, count) in enumerate(data["langs"]):
        col, row = i % 3, i // 3
        lx, ly = 28 + col * 282, 222 + row * 24
        color = LANG_COLORS.get(name, FALLBACK_COLORS[i % len(FALLBACK_COLORS)])
        pct = 100 * count / total
        parts.append(
            f'<circle cx="{lx + 5}" cy="{ly - 4}" r="5" fill="{color}"/>'
            f'<text x="{lx + 18}" y="{ly}" font-family="{mono}" font-size="12" '
            f'fill="{fg}">{esc(name)}</text>'
            f'<text x="{lx + 18 + 7.3 * len(name) + 12}" y="{ly}" font-family="{mono}" '
            f'font-size="12" fill="{muted}">{pct:.1f}%</text>'
        )

    parts.append("</svg>")
    return "\n".join(parts)


def main():
    data = collect()
    for theme in ("dark", "light"):
        with open(f"stats-{theme}.svg", "w", encoding="utf-8", newline="\n") as f:
            f.write(render(data, theme))
    print(json.dumps({k: v for k, v in data.items() if k != "langs"}, indent=2))
    print("languages:", ", ".join(name for name, _ in data["langs"]))


if __name__ == "__main__":
    main()
