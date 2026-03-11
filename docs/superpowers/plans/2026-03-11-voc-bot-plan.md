# VOC Bot Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** GitHub issue에 올라오는 사용자 질문에 대해 docs를 근거로 정확하게 1차 응답하는 PydanticAI 기반 agent를 구축한다.

**Architecture:** Multi-step Agent with Tools 방식. PydanticAI agent가 docs 사이트를 실시간 HTTP fetch로 탐색하며, 적응형 탐색(Adaptive Retrieval)으로 충분한 근거를 확보한 후 structured output으로 답변을 생성한다.

**Tech Stack:** Python 3.11+, PydanticAI, httpx, BeautifulSoup4, pydantic

**Spec:** `docs/superpowers/specs/2026-03-11-voc-bot-design.md`

---

## File Structure

```
opencode-voc-bot/
├── src/
│   ├── __init__.py            # 패키지 초기화
│   ├── config.py              # 설정 (API URL, docs base URL, 환경변수)
│   ├── models.py              # Pydantic 입출력 모델
│   ├── tools.py               # docs 탐색 도구 (list, fetch, search)
│   ├── agent.py               # PydanticAI agent 정의
│   └── main.py                # CLI 진입점
├── tests/
│   ├── __init__.py
│   ├── test_config.py
│   ├── test_models.py
│   ├── test_tools.py
│   ├── test_agent.py
│   └── conftest.py            # 공통 fixtures
├── mock-api-server/           # GitHub에서 가져온 mock server
│   ├── __init__.py
│   ├── main.py
│   ├── auth_bearer.py
│   ├── auth_handler.py
│   ├── config/
│   │   └── cli_model_list.json
│   └── requirements.txt
├── requirements.txt
├── .env.example
└── pytest.ini
```

---

## Chunk 1: 프로젝트 기반 및 설정

### Task 1: 프로젝트 초기화 및 의존성 설정

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `pytest.ini`
- Create: `src/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: requirements.txt 생성**

```
pydantic-ai[openai]>=0.0.49
pydantic-settings>=2.0.0
httpx>=0.27.0
beautifulsoup4>=4.12.0
pydantic>=2.0.0
python-dotenv>=1.0.0
pytest>=8.0.0
pytest-asyncio>=0.23.0
pytest-httpx>=0.30.0
```

- [ ] **Step 2: .env.example 생성**

```
# LLM API 설정
LLM_BASE_URL=http://localhost:9013/v1
LLM_API_KEY=your-api-key-here
LLM_MODEL=qwen3.5:397b-cloud

# Docs 사이트 설정
DOCS_BASE_URL=http://localhost:4321/docs

# Mock API 인증 (mock server 사용 시)
UMS_TOKEN=test-ums-token-12345
```

- [ ] **Step 3: pytest.ini 생성**

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
```

- [ ] **Step 4: 패키지 초기화 파일 및 conftest.py 생성**

`src/__init__.py` — 빈 파일

`tests/__init__.py` — 빈 파일

`tests/conftest.py`:
```python
import pytest


@pytest.fixture
def docs_base_url():
    return "http://localhost:4321/docs"


@pytest.fixture
def sample_issue():
    return {
        "title": "MCP 서버 설정 방법이 궁금합니다",
        "body": "MCP 서버를 설정하려고 하는데 어떻게 해야 하나요? 설정 파일 위치와 옵션을 알고 싶습니다.",
    }


@pytest.fixture
def sample_issue_en():
    return {
        "title": "How to configure custom tools?",
        "body": "I want to add custom tools to my setup. Where do I configure them and what options are available?",
    }
```

- [ ] **Step 5: 가상환경 생성 및 의존성 설치**

Run: `cd /home/soob/task/opencode-voc-bot && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`

- [ ] **Step 6: .gitignore 생성**

```
.venv/
__pycache__/
*.pyc
.env
*.egg-info/
dist/
build/
.pytest_cache/
```

- [ ] **Step 7: 커밋**

```bash
git add requirements.txt .env.example pytest.ini src/__init__.py tests/__init__.py tests/conftest.py .gitignore
git commit -m "chore: initialize project with dependencies and test config"
```

---

### Task 2: 설정 모듈 (`config.py`)

**Files:**
- Create: `src/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_config.py`:
```python
from src.config import Settings


def test_settings_defaults():
    settings = Settings()
    assert settings.docs_base_url == "http://localhost:4321/docs"
    assert settings.llm_model == "qwen3.5:397b-cloud"
    assert settings.agent_max_iterations == 15
    assert settings.agent_timeout == 120


def test_settings_custom():
    settings = Settings(
        docs_base_url="http://example.com/docs",
        llm_base_url="http://localhost:8000/v1",
        llm_api_key="test-key",
        llm_model="test-model",
    )
    assert settings.docs_base_url == "http://example.com/docs"
    assert settings.llm_base_url == "http://localhost:8000/v1"
    assert settings.llm_api_key == "test-key"
    assert settings.llm_model == "test-model"
```

- [ ] **Step 2: 테스트 실행하여 실패 확인**

Run: `cd /home/soob/task/opencode-voc-bot && source .venv/bin/activate && python -m pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.config'`

- [ ] **Step 3: 최소 구현 작성**

`src/config.py`:
```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_prefix": "", "env_file": ".env", "extra": "ignore"}

    # Docs
    docs_base_url: str = "http://localhost:4321/docs"

    # LLM
    llm_base_url: str = "http://localhost:9013/v1"
    llm_api_key: str = ""
    llm_model: str = "qwen3.5:397b-cloud"

    # Agent
    agent_max_iterations: int = 15
    agent_timeout: int = 120
```

- [ ] **Step 4: 테스트 실행하여 통과 확인**

Run: `cd /home/soob/task/opencode-voc-bot && source .venv/bin/activate && python -m pytest tests/test_config.py -v`
Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add src/config.py tests/test_config.py
git commit -m "feat: add settings module with env-based configuration"
```


---

### Task 3: 입출력 모델 (`models.py`)

**Files:**
- Create: `src/models.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_models.py`:
```python
from src.models import IssueInput, Reference, VocResponse


def test_issue_input():
    issue = IssueInput(
        title="MCP 서버 설정 방법",
        body="MCP 서버를 어떻게 설정하나요?",
    )
    assert issue.title == "MCP 서버 설정 방법"
    assert issue.body == "MCP 서버를 어떻게 설정하나요?"


def test_reference():
    ref = Reference(title="MCP Servers", url="/docs/mcp-servers")
    assert ref.title == "MCP Servers"
    assert ref.url == "/docs/mcp-servers"


def test_voc_response_sufficient():
    response = VocResponse(
        answer="MCP 서버는 config.json에서 설정할 수 있습니다.",
        references=[Reference(title="MCP Servers", url="/docs/mcp-servers")],
        confidence="sufficient",
        escalation_needed=False,
    )
    assert response.confidence == "sufficient"
    assert response.escalation_needed is False
    assert len(response.references) == 1


def test_voc_response_insufficient():
    response = VocResponse(
        answer="문서만으로는 정확한 답변을 확인할 수 없습니다.",
        references=[],
        confidence="insufficient",
        escalation_needed=True,
    )
    assert response.confidence == "insufficient"
    assert response.escalation_needed is True
```

- [ ] **Step 2: 테스트 실행하여 실패 확인**

Run: `cd /home/soob/task/opencode-voc-bot && source .venv/bin/activate && python -m pytest tests/test_models.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 최소 구현 작성**

`src/models.py`:
```python
from typing import Literal

from pydantic import BaseModel, Field


class IssueInput(BaseModel):
    title: str = Field(description="GitHub issue 제목")
    body: str = Field(description="GitHub issue 본문")


class Reference(BaseModel):
    title: str = Field(description="참고 문서 제목")
    url: str = Field(description="참고 문서 URL")


class VocResponse(BaseModel):
    answer: str = Field(
        description="인라인 인용을 포함한 답변. 사용자 질문의 언어와 동일한 언어로 작성."
    )
    references: list[Reference] = Field(
        description="답변에서 참고한 문서 목록"
    )
    confidence: Literal["sufficient", "insufficient"] = Field(
        description="문서 근거의 충분성"
    )
    escalation_needed: bool = Field(
        description="담당자 에스컬레이션 필요 여부"
    )
```

- [ ] **Step 4: 테스트 실행하여 통과 확인**

Run: `cd /home/soob/task/opencode-voc-bot && source .venv/bin/activate && python -m pytest tests/test_models.py -v`
Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add src/models.py tests/test_models.py
git commit -m "feat: add input/output data models"
```

---

## Chunk 2: Docs 탐색 도구

### Task 4: Docs 탐색 도구 (`tools.py`)

**Files:**
- Create: `src/tools.py`
- Create: `tests/test_tools.py`

- [ ] **Step 1: 실패하는 테스트 작성 — list_doc_pages**

`tests/test_tools.py`:
```python
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
async def test_search_docs(httpx_mock):
    httpx_mock.add_response(
        url="http://localhost:4321/docs/cli",
        html="<main><p>CLI usage guide for terminal</p></main>",
    )
    httpx_mock.add_response(
        url="http://localhost:4321/docs/config",
        html="<main><p>Configuration options for settings</p></main>",
    )
    httpx_mock.add_response(
        url="http://localhost:4321/docs/mcp-servers",
        html=FAKE_DOC_PAGE_HTML,
    )
    httpx_mock.add_response(
        url="http://localhost:4321/docs/troubleshooting",
        html="<main><p>Common issues and fixes</p></main>",
    )

    pages = [
        {"title": "CLI", "path": "/docs/cli"},
        {"title": "Configuration", "path": "/docs/config"},
        {"title": "MCP Servers", "path": "/docs/mcp-servers"},
        {"title": "Troubleshooting", "path": "/docs/troubleshooting"},
    ]
    results = await search_docs("http://localhost:4321/docs", pages, "mcp")
    assert len(results) >= 1
    assert any(r["path"] == "/docs/mcp-servers" for r in results)
```

- [ ] **Step 2: 테스트 실행하여 실패 확인**

Run: `cd /home/soob/task/opencode-voc-bot && source .venv/bin/activate && python -m pytest tests/test_tools.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 최소 구현 작성**

`src/tools.py`:
```python
import httpx
from bs4 import BeautifulSoup


async def list_doc_pages(docs_base_url: str) -> list[dict[str, str]]:
    """docs 사이트의 전체 페이지 목록을 반환한다."""
    async with httpx.AsyncClient() as client:
        response = await client.get(docs_base_url, follow_redirects=True)
        response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    pages = []
    seen = set()

    for link in soup.find_all("a", href=True):
        href = link["href"]
        if href.startswith("/docs/") and href != "/docs/" and href not in seen:
            # 앵커(#) 제거
            path = href.split("#")[0]
            if path not in seen:
                seen.add(path)
                title = link.get_text(strip=True)
                if title:
                    pages.append({"title": title, "path": path})

    return pages


async def fetch_doc_page(docs_base_url: str, page_path: str) -> str:
    """특정 docs 페이지의 본문 텍스트를 반환한다. HTML 태그는 제거."""
    from urllib.parse import urlparse, urlunparse

    parsed = urlparse(docs_base_url)
    origin = urlunparse((parsed.scheme, parsed.netloc, "", "", "", ""))

    if page_path.startswith("/"):
        url = origin + page_path
    else:
        url = docs_base_url.rstrip("/") + "/" + page_path

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, follow_redirects=True)
            if response.status_code != 200:
                return ""
        except httpx.HTTPError:
            return ""

    soup = BeautifulSoup(response.text, "html.parser")

    # <main> 태그 우선, 없으면 <body>
    main = soup.find("main") or soup.find("body")
    if main is None:
        return ""

    # 스크립트, 스타일 태그 제거
    for tag in main.find_all(["script", "style", "nav"]):
        tag.decompose()

    return main.get_text(separator="\n", strip=True)


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

    return results
```

- [ ] **Step 4: 테스트 실행하여 통과 확인**

Run: `cd /home/soob/task/opencode-voc-bot && source .venv/bin/activate && python -m pytest tests/test_tools.py -v`
Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add src/tools.py tests/test_tools.py
git commit -m "feat: add docs crawling tools (list, fetch, search)"
```

---

## Chunk 3: PydanticAI Agent

### Task 5: Agent 정의 (`agent.py`)

**Files:**
- Create: `src/agent.py`
- Create: `tests/test_agent.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_agent.py`:
```python
import pytest

from src.agent import create_agent, AgentDeps, SYSTEM_PROMPT
from src.config import Settings
from src.models import VocResponse


def test_agent_creates_successfully():
    settings = Settings(llm_api_key="test-key")
    agent = create_agent(settings)
    assert agent is not None


def test_agent_has_expected_tools():
    settings = Settings(llm_api_key="test-key")
    agent = create_agent(settings)
    tool_names = {tool.name for tool in agent._function_tools.values()}
    assert "tool_list_doc_pages" in tool_names
    assert "tool_fetch_doc_page" in tool_names
    assert "tool_search_docs" in tool_names


def test_agent_system_prompt_contains_key_rules():
    assert "STRICTLY" in SYSTEM_PROMPT
    assert "SAME LANGUAGE" in SYSTEM_PROMPT
    assert "escalation_needed" in SYSTEM_PROMPT
    assert "inline" in SYSTEM_PROMPT.lower()


def test_agent_deps_defaults():
    settings = Settings(llm_api_key="test-key")
    deps = AgentDeps(settings=settings)
    assert deps.settings.docs_base_url == "http://localhost:4321/docs"
    assert len(deps.fetched_pages) == 0


def test_agent_deps_tracks_fetched_pages():
    settings = Settings(llm_api_key="test-key")
    deps = AgentDeps(settings=settings)
    deps.fetched_pages.add("/docs/cli")
    deps.fetched_pages.add("/docs/config")
    assert "/docs/cli" in deps.fetched_pages
    assert len(deps.fetched_pages) == 2


def test_agent_output_type_is_voc_response():
    settings = Settings(llm_api_key="test-key")
    agent = create_agent(settings)
    # PydanticAI agent의 output_type 확인
    assert agent._output_type == VocResponse
```

- [ ] **Step 2: 테스트 실행하여 실패 확인**

Run: `cd /home/soob/task/opencode-voc-bot && source .venv/bin/activate && python -m pytest tests/test_agent.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 최소 구현 작성**

`src/agent.py`:
```python
from dataclasses import dataclass, field

from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from src.config import Settings
from src.models import VocResponse
from src.tools import list_doc_pages, fetch_doc_page, search_docs


SYSTEM_PROMPT = """\
You are a VOC (Voice of Customer) support agent. Your role is to answer user questions \
from GitHub issues based STRICTLY on the official documentation.

## Rules

1. You MUST ONLY use information retrieved from documentation pages via the provided tools.
2. NEVER guess, speculate, or use knowledge outside of the retrieved documents.
3. If the documentation does not contain sufficient information to answer the question, \
   set confidence to "insufficient" and escalation_needed to true.
4. Always cite your sources with inline references and include a reference list.
5. Respond in the SAME LANGUAGE as the user's question. \
   If the question is in Korean, respond in Korean. If in English, respond in English.
6. Use a formal, polite tone. \
   In Korean: use "~하시기 바랍니다", "~을 참고해 주세요" style. \
   In English: use "Please refer to...", "We recommend..." style.

## Workflow

1. First, call list_doc_pages to see all available documentation pages.
2. Identify which pages are likely relevant to the user's question.
3. Fetch the most relevant pages using fetch_doc_page.
4. After each page, assess: "Do I have enough evidence to answer fully?"
   - If YES: generate the answer.
   - If NO: fetch the next relevant page.
5. If you need to find pages by keyword, use search_docs.
6. When you have sufficient evidence, produce the final answer with:
   - Inline citations linking to the relevant docs pages
   - A references list at the bottom
7. If evidence is insufficient after checking all relevant pages, clearly state that \
   the documentation does not cover this topic and set escalation_needed to true.

## Answer Format

For Korean:
- 답변 본문에 인라인 인용: "~할 수 있습니다 ([문서 제목](URL) 참고)."
- 하단에 "### 참고 문서" 섹션

For English:
- Inline citations: "You can configure this ([Doc Title](URL))."
- Bottom section: "### References"

## Escalation Format

When escalation is needed:
- Korean: "문서만으로는 정확한 답변을 확인할 수 없습니다. 담당자의 확인이 필요합니다."
- English: "The documentation does not provide sufficient information. Human review is required."
"""


@dataclass
class AgentDeps:
    settings: Settings
    fetched_pages: set[str] = field(default_factory=set)


def create_agent(settings: Settings) -> Agent[AgentDeps, VocResponse]:
    model = OpenAIChatModel(
        settings.llm_model,
        provider=OpenAIProvider(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
        ),
    )

    agent = Agent(
        model,
        deps_type=AgentDeps,
        output_type=VocResponse,
        instructions=SYSTEM_PROMPT,
        retries=2,
    )

    @agent.tool
    async def tool_list_doc_pages(ctx: RunContext[AgentDeps]) -> str:
        """Get the list of all available documentation pages. Call this first to see what docs exist."""
        pages = await list_doc_pages(ctx.deps.settings.docs_base_url)
        lines = [f"- {p['title']}: {p['path']}" for p in pages]
        return "Available documentation pages:\n" + "\n".join(lines)

    @agent.tool
    async def tool_fetch_doc_page(ctx: RunContext[AgentDeps], page_path: str) -> str:
        """Fetch the full content of a specific documentation page. Provide the page path like '/docs/cli'."""
        if page_path in ctx.deps.fetched_pages:
            return f"[Already fetched: {page_path}. Use the content from the previous fetch.]"

        content = await fetch_doc_page(ctx.deps.settings.docs_base_url, page_path)
        if not content:
            return f"[Page not found or empty: {page_path}]"

        ctx.deps.fetched_pages.add(page_path)
        return f"Content of {page_path}:\n\n{content}"

    @agent.tool
    async def tool_search_docs(ctx: RunContext[AgentDeps], keyword: str) -> str:
        """Search documentation pages by keyword. Returns pages whose title or content contains the keyword."""
        pages = await list_doc_pages(ctx.deps.settings.docs_base_url)
        results = await search_docs(ctx.deps.settings.docs_base_url, pages, keyword)

        if not results:
            return f"No pages found matching keyword: '{keyword}'"

        lines = [f"- {r['title']}: {r['path']}" for r in results]
        return f"Pages matching '{keyword}':\n" + "\n".join(lines)

    return agent


async def run_agent(settings: Settings, title: str, body: str) -> VocResponse:
    """issue 제목과 본문으로 agent를 실행하여 답변을 생성한다."""
    agent = create_agent(settings)
    deps = AgentDeps(settings=settings)

    user_message = f"GitHub Issue Title: {title}\n\nGitHub Issue Body:\n{body}"

    result = await agent.run(user_message, deps=deps)
    return result.output
```

- [ ] **Step 4: 테스트 실행하여 통과 확인**

Run: `cd /home/soob/task/opencode-voc-bot && source .venv/bin/activate && python -m pytest tests/test_agent.py -v`
Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add src/agent.py tests/test_agent.py
git commit -m "feat: add PydanticAI agent with docs tools and system prompt"
```

---

## Chunk 4: CLI 진입점 및 Mock Server

### Task 6: CLI 진입점 (`main.py`)

**Files:**
- Create: `src/main.py`
- Create: `tests/test_main.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_main.py`:
```python
from src.main import format_output, _is_korean
from src.models import VocResponse, Reference


def test_is_korean_true():
    assert _is_korean("MCP 서버 설정 방법") is True


def test_is_korean_false():
    assert _is_korean("How to configure MCP servers") is False


def test_is_korean_empty():
    assert _is_korean("") is False


def test_format_output_korean():
    response = VocResponse(
        answer="MCP 서버는 설정 파일에서 구성할 수 있습니다.",
        references=[Reference(title="MCP Servers", url="/docs/mcp-servers")],
        confidence="sufficient",
        escalation_needed=False,
    )
    output = format_output(response)
    assert "MCP 서버는 설정 파일에서 구성할 수 있습니다." in output
    assert "### 참고 문서" in output
    assert "[MCP Servers](/docs/mcp-servers)" in output
    assert "Confidence: sufficient" in output


def test_format_output_english():
    response = VocResponse(
        answer="You can configure MCP servers in the config file.",
        references=[Reference(title="MCP Servers", url="/docs/mcp-servers")],
        confidence="sufficient",
        escalation_needed=False,
    )
    output = format_output(response)
    assert "### References" in output


def test_format_output_escalation():
    response = VocResponse(
        answer="문서만으로는 확인할 수 없습니다.",
        references=[],
        confidence="insufficient",
        escalation_needed=True,
    )
    output = format_output(response)
    assert "담당자의 확인이 필요합니다" in output
    assert "Confidence: insufficient" in output
```

- [ ] **Step 2: 테스트 실행하여 실패 확인**

Run: `cd /home/soob/task/opencode-voc-bot && source .venv/bin/activate && python -m pytest tests/test_main.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 구현 작성**

`src/main.py`:
```python
import argparse
import asyncio
import sys

from src.config import Settings
from src.agent import run_agent


def format_output(response) -> str:
    """VocResponse를 사람이 읽기 좋은 형태로 포맷한다."""
    output_parts = []

    # 답변 본문
    output_parts.append(response.answer)

    # 참고 문서
    if response.references:
        output_parts.append("")
        output_parts.append("### 참고 문서" if _is_korean(response.answer) else "### References")
        for ref in response.references:
            output_parts.append(f"- [{ref.title}]({ref.url})")

    # 에스컬레이션
    if response.escalation_needed:
        output_parts.append("")
        if _is_korean(response.answer):
            output_parts.append("> ⚠️ 담당자의 확인이 필요합니다.")
        else:
            output_parts.append("> ⚠️ Human review is required.")

    # 메타 정보
    output_parts.append("")
    output_parts.append(f"---")
    output_parts.append(f"Confidence: {response.confidence}")

    return "\n".join(output_parts)


def _is_korean(text: str) -> bool:
    """텍스트에 한글이 포함되어 있는지 간단히 판단한다."""
    return any("\uac00" <= ch <= "\ud7a3" for ch in text)


async def async_main(title: str, body: str) -> None:
    settings = Settings()
    print(f"=== VOC Bot Agent ===")
    print(f"Issue Title: {title}")
    print(f"Issue Body: {body[:100]}{'...' if len(body) > 100 else ''}")
    print(f"Docs URL: {settings.docs_base_url}")
    print(f"LLM: {settings.llm_model} @ {settings.llm_base_url}")
    print(f"=====================\n")

    print("Analyzing issue and searching documentation...\n")

    try:
        response = await run_agent(settings, title, body)
        print(format_output(response))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="VOC Bot - GitHub Issue Auto-responder")
    parser.add_argument("--title", "-t", required=True, help="GitHub issue title")
    parser.add_argument("--body", "-b", required=True, help="GitHub issue body")
    args = parser.parse_args()

    asyncio.run(async_main(args.title, args.body))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 테스트 실행하여 통과 확인**

Run: `cd /home/soob/task/opencode-voc-bot && source .venv/bin/activate && python -m pytest tests/test_main.py -v`
Expected: PASS

- [ ] **Step 5: CLI 도움말 확인**

Run: `cd /home/soob/task/opencode-voc-bot && source .venv/bin/activate && python -m src.main --help`
Expected: usage 메시지 출력

- [ ] **Step 6: 커밋**

```bash
git add src/main.py tests/test_main.py
git commit -m "feat: add CLI entry point for VOC bot"
```

---

### Task 7: Mock API Server 가져오기

**Files:**
- Create: `mock-api-server/` (GitHub repo에서 파일 복사)

- [ ] **Step 1: mock-api-server 디렉토리 생성 및 파일 다운로드**

```bash
cd /home/soob/task/opencode-voc-bot
mkdir -p mock-api-server/config
# GitHub API로 각 파일 다운로드
gh api repos/log0629/opencode/contents/mock-api-server/main.py?ref=develop -q '.content' | base64 -d > mock-api-server/main.py
gh api repos/log0629/opencode/contents/mock-api-server/auth_bearer.py?ref=develop -q '.content' | base64 -d > mock-api-server/auth_bearer.py
gh api repos/log0629/opencode/contents/mock-api-server/auth_handler.py?ref=develop -q '.content' | base64 -d > mock-api-server/auth_handler.py
gh api repos/log0629/opencode/contents/mock-api-server/__init__.py?ref=develop -q '.content' | base64 -d > mock-api-server/__init__.py
gh api repos/log0629/opencode/contents/mock-api-server/requirements.txt?ref=develop -q '.content' | base64 -d > mock-api-server/requirements.txt
gh api repos/log0629/opencode/contents/mock-api-server/config/cli_model_list.json?ref=develop -q '.content' | base64 -d > mock-api-server/config/cli_model_list.json
```

- [ ] **Step 2: mock server 의존성 설치 확인**

Run: `cd /home/soob/task/opencode-voc-bot && source .venv/bin/activate && pip install -r mock-api-server/requirements.txt`

- [ ] **Step 3: 커밋**

```bash
git add mock-api-server/
git commit -m "chore: add mock API server from opencode repo"
```

---

## Chunk 5: 통합 테스트 및 마무리

### Task 8: 통합 테스트

**Files:**
- Create: `tests/test_integration.py`

- [ ] **Step 1: 통합 테스트 작성**

`tests/test_integration.py`:
```python
"""
통합 테스트 — tools + agent 구성을 함께 검증.
실제 LLM 호출 없이 구조적 정합성을 확인.
"""
import pytest

from src.agent import create_agent, AgentDeps
from src.config import Settings
from src.models import VocResponse, Reference
from src.main import format_output
from src.tools import list_doc_pages, fetch_doc_page


@pytest.mark.asyncio
async def test_tools_and_agent_wiring(httpx_mock):
    """Agent의 tool이 실제 tools 모듈 함수를 올바르게 호출하는지 검증."""
    httpx_mock.add_response(
        url="http://localhost:4321/docs",
        html="""<html><body><nav>
            <a href="/docs/cli">CLI</a>
            <a href="/docs/config">Config</a>
        </nav></body></html>""",
    )

    # tools 모듈 직접 호출로 agent가 사용할 함수가 정상 동작하는지 확인
    pages = await list_doc_pages("http://localhost:4321/docs")
    assert len(pages) == 2

    # agent 생성 후 tool 개수 확인
    settings = Settings(llm_api_key="test-key")
    agent = create_agent(settings)
    assert len(agent._function_tools) == 3


@pytest.mark.asyncio
async def test_fetch_and_format_pipeline(httpx_mock):
    """fetch → VocResponse 생성 → format_output 전체 파이프라인 검증."""
    httpx_mock.add_response(
        url="http://localhost:4321/docs/cli",
        html="<main><h1>CLI Guide</h1><p>Use the CLI to run commands.</p></main>",
    )

    content = await fetch_doc_page("http://localhost:4321/docs", "/docs/cli")
    assert "CLI Guide" in content

    # 이 content를 기반으로 응답을 구성한다고 가정
    response = VocResponse(
        answer=f"CLI를 사용하여 명령을 실행할 수 있습니다 ([CLI Guide](/docs/cli) 참고).",
        references=[Reference(title="CLI Guide", url="/docs/cli")],
        confidence="sufficient",
        escalation_needed=False,
    )

    output = format_output(response)
    assert "CLI Guide" in output
    assert "### 참고 문서" in output
    assert "Confidence: sufficient" in output


def test_escalation_format_pipeline():
    """에스컬레이션 응답의 전체 포맷 파이프라인 검증."""
    response = VocResponse(
        answer="문서만으로는 정확한 답변을 확인할 수 없습니다. 담당자의 확인이 필요합니다.",
        references=[],
        confidence="insufficient",
        escalation_needed=True,
    )
    output = format_output(response)
    assert "담당자의 확인이 필요합니다" in output
    assert "Confidence: insufficient" in output
```

- [ ] **Step 2: 전체 테스트 스위트 실행**

Run: `cd /home/soob/task/opencode-voc-bot && source .venv/bin/activate && python -m pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 3: 커밋**

```bash
git add tests/test_integration.py
git commit -m "test: add integration tests for full pipeline"
```

---

### Task 9: 수동 E2E 테스트 가이드

이 태스크는 코드 작성이 아닌 수동 테스트 절차입니다.

- [ ] **Step 1: mock-api-server 시작**

```bash
cd /home/soob/task/opencode-voc-bot
source .venv/bin/activate
export OLLAMA_API_KEY="your-ollama-api-key"
cd mock-api-server && uvicorn main:app --host 0.0.0.0 --port 9013 --reload &
cd ..
```

- [ ] **Step 2: docs 사이트가 실행 중인지 확인**

```bash
curl -s http://localhost:4321/docs/ | head -20
```

Expected: HTML 응답

- [ ] **Step 3: 한글 질문 테스트**

```bash
python -m src.main \
  --title "MCP 서버 설정 방법이 궁금합니다" \
  --body "MCP 서버를 설정하려고 하는데 어떻게 해야 하나요? 설정 파일 위치와 옵션을 알고 싶습니다."
```

Expected: 한글로 된 정중한 답변 + 인라인 인용 + 참고 문서 링크

- [ ] **Step 4: 영문 질문 테스트**

```bash
python -m src.main \
  --title "How to configure custom tools?" \
  --body "I want to add custom tools to my setup. Where do I configure them and what options are available?"
```

Expected: 영문으로 된 정중한 답변 + 인라인 인용 + References 섹션

- [ ] **Step 5: 답변 불가 케이스 테스트**

```bash
python -m src.main \
  --title "Does it support Azure DevOps integration?" \
  --body "Can I use this with Azure DevOps pipelines? Is there a plugin for that?"
```

Expected: 문서에서 확인할 수 없다는 답변 + escalation_needed: true

- [ ] **Step 6: 결과 확인 체크리스트**

- [ ] 한글 질문 → 한글 답변
- [ ] 영문 질문 → 영문 답변
- [ ] 인라인 인용이 답변 본문에 포함
- [ ] 하단에 참고 문서 링크 목록
- [ ] 답변 불가 시 에스컬레이션 메시지
- [ ] confidence 값이 적절하게 설정
- [ ] hallucination 없이 문서 근거 기반 답변

---

## Future Scope (현재 계획에 포함하지 않음)

- GitHub Actions 트리거 연동 (issue 이벤트 → workflow → bot 실행)
- 에스컬레이션 시 `needs-human-review` 라벨 자동 추가
- 담당자 멘션/assign 자동화
- `search_docs` 병렬 fetch로 성능 개선
