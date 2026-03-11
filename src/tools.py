import sys
from urllib.parse import urlparse, urlunparse

import httpx
from bs4 import BeautifulSoup

SSL_CA_BUNDLE = "/etc/ssl/certs/ca-certificates.crt"


def _log(msg: str) -> None:
    print(f"[tools] {msg}", file=sys.stderr)


async def list_doc_pages(docs_base_url: str) -> list[dict[str, str]]:
    """docs 사이트의 전체 페이지 목록을 반환한다."""
    parsed = urlparse(docs_base_url)
    base_path = parsed.path.rstrip("/")

    _log(f"Fetching doc index from: {docs_base_url}")
    _log(f"Base path for link matching: {base_path}")

    async with httpx.AsyncClient(verify=False) as client:
        response = await client.get(docs_base_url, follow_redirects=True)
        response.raise_for_status()

    _log(f"Index response status: {response.status_code}, length: {len(response.text)}")

    soup = BeautifulSoup(response.text, "html.parser")
    pages = []
    seen = set()

    for link in soup.find_all("a", href=True):
        href = link["href"]
        # base_path 기반으로 동적 필터링
        if href.startswith(base_path + "/") and href != base_path + "/" and href not in seen:
            # 앵커(#) 제거
            path = href.split("#")[0]
            if path not in seen:
                seen.add(path)
                title = link.get_text(strip=True)
                if title:
                    pages.append({"title": title, "path": path})

    _log(f"Found {len(pages)} doc pages")
    if pages:
        _log(f"Sample pages: {[p['path'] for p in pages[:5]]}")
    else:
        # 디버깅용: 페이지에 있는 모든 링크 출력
        all_hrefs = [a["href"] for a in soup.find_all("a", href=True)][:20]
        _log(f"No pages matched. Sample hrefs on page: {all_hrefs}")

    return pages


async def fetch_doc_page(docs_base_url: str, page_path: str) -> str:
    """특정 docs 페이지의 본문 텍스트를 반환한다. HTML 태그는 제거."""
    parsed = urlparse(docs_base_url)
    origin = urlunparse((parsed.scheme, parsed.netloc, "", "", "", ""))

    if page_path.startswith("/"):
        url = origin + page_path
    else:
        url = docs_base_url.rstrip("/") + "/" + page_path

    _log(f"Fetching page: {url}")

    async with httpx.AsyncClient(verify=False) as client:
        try:
            response = await client.get(url, follow_redirects=True)
            if response.status_code != 200:
                _log(f"Page returned status {response.status_code}: {url}")
                return ""
        except httpx.HTTPError as e:
            _log(f"HTTP error fetching {url}: {e}")
            return ""

    soup = BeautifulSoup(response.text, "html.parser")

    # <main> 태그 우선, 없으면 <body>
    main = soup.find("main") or soup.find("body")
    if main is None:
        _log(f"No <main> or <body> tag found: {url}")
        return ""

    # 스크립트, 스타일 태그 제거
    for tag in main.find_all(["script", "style", "nav"]):
        tag.decompose()

    content = main.get_text(separator="\n", strip=True)
    _log(f"Fetched {len(content)} chars from {page_path}")
    return content


async def search_docs(
    docs_base_url: str,
    pages: list[dict[str, str]],
    keyword: str,
) -> list[dict[str, str]]:
    """키워드로 페이지 제목 및 본문을 검색하여 매칭되는 페이지 목록을 반환한다."""
    keyword_lower = keyword.lower()
    results = []

    for page in pages:
        # 제목에 키워드가 포함되면 바로 추가
        if keyword_lower in page["title"].lower():
            results.append(page)
            continue

        # 본문에서 키워드 검색
        content = await fetch_doc_page(docs_base_url, page["path"])
        if keyword_lower in content.lower():
            results.append(page)

    _log(f"Search '{keyword}': {len(results)} results from {len(pages)} pages")
    return results
