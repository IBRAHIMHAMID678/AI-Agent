"""Site crawler: sitemap.xml first, homepage link-following as fallback.

Same-domain only, caps at ~50 pages. Returns list of {url, title, text}.
"""
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "AIAgentBot/1.0 (+site-operator demo crawler)"}
MAX_PAGES = 50
SKIP_EXT = (".pdf", ".jpg", ".jpeg", ".png", ".gif", ".svg", ".zip",
            ".mp4", ".css", ".js", ".ico", ".woff", ".woff2")


def _same_domain(url, domain):
    try:
        return urlparse(url).netloc.lower() == domain
    except Exception:
        return False


def _clean_text(html, base_url):
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer", "aside",
                     "form", "noscript"]):
        tag.decompose()
    title = soup.title.string.strip() if soup.title and soup.title.string else ""
    text = soup.get_text(separator="\n")
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    return title, "\n".join(lines)


def _sitemap_urls(client, base_url):
    urls = []
    for name in ("sitemap.xml", "sitemap_index.xml"):
        try:
            r = client.get(urljoin(base_url, name), timeout=15)
            if r.status_code != 200:
                continue
            soup = BeautifulSoup(r.text, "xml")
            locs = [l.text.strip() for l in soup.find_all("loc")]
            # sitemap index -> recurse one level
            if soup.find("sitemapindex"):
                for loc in locs[:5]:
                    try:
                        r2 = client.get(loc, timeout=15)
                        s2 = BeautifulSoup(r2.text, "xml")
                        urls += [l.text.strip() for l in s2.find_all("loc")]
                    except Exception:
                        continue
            else:
                urls += locs
        except Exception:
            continue
    return urls


def _homepage_links(client, base_url, domain):
    try:
        r = client.get(base_url, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        links = []
        for a in soup.find_all("a", href=True):
            u = urljoin(base_url, a["href"]).split("#")[0].split("?")[0]
            if _same_domain(u, domain) and not u.lower().endswith(SKIP_EXT):
                links.append(u)
        return links
    except Exception:
        return []


def crawl_site(start_url, max_pages=MAX_PAGES):
    """Crawl a site. Returns [{url, title, text}]."""
    parsed = urlparse(start_url if "://" in start_url else "https://" + start_url)
    domain = parsed.netloc.lower()
    base = f"{parsed.scheme or 'https'}://{domain}"
    pages, seen = [], set()

    with httpx.Client(headers=HEADERS, follow_redirects=True) as client:
        candidates = _sitemap_urls(client, base) or _homepage_links(client, base, domain)
        # always include the homepage itself
        candidates = [base + "/"] + candidates
        for url in candidates:
            if len(pages) >= max_pages or url in seen:
                continue
            seen.add(url)
            if not _same_domain(url, domain) or url.lower().endswith(SKIP_EXT):
                continue
            try:
                r = client.get(url, timeout=15)
                if r.status_code != 200 or "text/html" not in r.headers.get("content-type", ""):
                    continue
                title, text = _clean_text(r.text, url)
                if len(text) < 200:
                    continue
                pages.append({"url": url, "title": title or url, "text": text})
            except Exception:
                continue
    return pages
