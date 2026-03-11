import pytest
import httpx

from src.tools import list_doc_pages, fetch_doc_page, search_docs


FAKE_DOCS_INDEX_HTML = """
<html><body>
<nav>
  <ul>
    <li><a href="/docs/cli">CLI</a></li>
    <li><a href="/docs/config">Configuration</a></li>
    <li><a href="/docs/mcp-servers">MCP Servers</a></li>
    <li><a href="/docs/troubleshooting">Troubleshooting</a></li>
  </ul>
</nav>
</body></html>
"""

FAKE_DOC_PAGE_HTML = """
<html><body>
<main>
  <h1>MCP Servers</h1>
  <p>MCP servers can be configured in your config file.</p>
  <p>Use the mcp_servers section to define server endpoints.</p>
  <pre><code>{ "mcp_servers": { "url": "http://localhost:3000" } }</code></pre>
</main>
</body></html>
"""


@pytest.mark.asyncio
async def test_list_doc_pages(httpx_mock):
    httpx_mock.add_response(
        url="http://localhost:4321/docs",
        html=FAKE_DOCS_INDEX_HTML,
    )
    pages = await list_doc_pages("http://localhost:4321/docs")
    assert len(pages) == 4
    assert {"title": "CLI", "path": "/docs/cli"} in pages
    assert {"title": "MCP Servers", "path": "/docs/mcp-servers"} in pages


@pytest.mark.asyncio
async def test_fetch_doc_page(httpx_mock):
    httpx_mock.add_response(
        url="http://localhost:4321/docs/mcp-servers",
        html=FAKE_DOC_PAGE_HTML,
    )
    content = await fetch_doc_page("http://localhost:4321/docs", "/docs/mcp-servers")
    assert "MCP Servers" in content
    assert "mcp_servers" in content
    assert "<html>" not in content  # HTML 태그가 제거되어야 함


@pytest.mark.asyncio
async def test_fetch_doc_page_not_found(httpx_mock):
    httpx_mock.add_response(
        url="http://localhost:4321/docs/nonexistent",
        status_code=404,
    )
    content = await fetch_doc_page("http://localhost:4321/docs", "/docs/nonexistent")
    assert content == ""


@pytest.mark.asyncio
async def test_search_docs_title_match(httpx_mock):
    """제목에 키워드가 포함되면 fetch 없이 바로 결과에 포함."""
    pages = [
        {"title": "CLI", "path": "/docs/cli"},
        {"title": "MCP Servers", "path": "/docs/mcp-servers"},
    ]
    # "MCP Servers" 제목에 "mcp"가 포함되므로 fetch 없이 매칭
    # CLI는 제목에 "mcp" 없으므로 본문 검색 필요
    httpx_mock.add_response(
        url="http://localhost:4321/docs/cli",
        html="<main><p>CLI usage guide</p></main>",
    )
    results = await search_docs("http://localhost:4321/docs", pages, "mcp")
    assert len(results) == 1
    assert results[0]["path"] == "/docs/mcp-servers"


@pytest.mark.asyncio
async def test_search_docs_content_match(httpx_mock):
    """제목에 없지만 본문에 키워드가 포함된 경우."""
    pages = [
        {"title": "Configuration", "path": "/docs/config"},
        {"title": "Troubleshooting", "path": "/docs/troubleshooting"},
    ]
    httpx_mock.add_response(
        url="http://localhost:4321/docs/config",
        html="<main><p>Configure your mcp_servers here.</p></main>",
    )
    httpx_mock.add_response(
        url="http://localhost:4321/docs/troubleshooting",
        html="<main><p>Common issues and fixes</p></main>",
    )
    results = await search_docs("http://localhost:4321/docs", pages, "mcp")
    assert len(results) == 1
    assert results[0]["path"] == "/docs/config"
