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

1. First, call tool_list_doc_pages to see all available documentation pages.
2. Identify which pages are likely relevant to the user's question.
3. Fetch the most relevant pages using tool_fetch_doc_page.
4. After each page, assess: "Do I have enough evidence to answer fully?"
   - If YES: generate the answer.
   - If NO: fetch the next relevant page.
5. If you need to find pages by keyword, use tool_search_docs.
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
