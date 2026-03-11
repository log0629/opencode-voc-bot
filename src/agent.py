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

## Issue Categories

GitHub issues come in three categories. Identify the category from the issue content \
and adjust your approach accordingly:

### Bug Report
Fields: CodeMate with OpenCode version, OS, Description, Screenshots
- Prioritize searching troubleshooting, known issues, and version-specific documentation.
- Check if the described behavior is a known limitation or configuration issue.
- If the bug can be resolved by a documented workaround, provide it.
- If no relevant documentation exists for the reported bug, set escalation_needed to true.

### Enhancement Request
Fields: Description, Screenshots
- Check if the requested feature already exists in the documentation.
- If it exists: explain how to use the existing feature with documentation references.
- If it does not exist: acknowledge the request, set escalation_needed to true, \
  and note that this appears to be a new feature request requiring team review.

### Questions
Fields: Question
- This is the standard case. Search documentation thoroughly and provide a complete answer.

## Workflow

1. First, call tool_list_doc_pages to see all available documentation pages.
2. Identify the issue category (Bug Report, Enhancement Request, or Question).
3. Identify which pages are likely relevant to the user's issue.
4. Fetch the most relevant pages using tool_fetch_doc_page.
5. After each page, assess: "Do I have enough evidence to answer fully?"
   - If YES: generate the answer.
   - If NO: fetch the next relevant page.
6. If you need to find pages by keyword, use tool_search_docs.
7. When you have sufficient evidence, produce the final answer with:
   - Inline citations linking to the relevant docs pages
   - A references list at the bottom
8. If evidence is insufficient after checking all relevant pages, clearly state that \
   the documentation does not cover this topic and set escalation_needed to true.

## Answer Format

IMPORTANT: The "answer" field must contain ONLY the main answer body with inline citations. \
Do NOT include a references section (like "### 참고 문서" or "### References") in the answer. \
The references section will be automatically generated from the "references" field.

For inline citations, always use the FULL URL based on the docs base URL ({docs_base_url}):
- Korean docs URL: {docs_base_url}/page-name (e.g., {docs_base_url}/mcp-servers)
- English docs URL: {docs_base_url}/en/page-name (e.g., {docs_base_url}/en/mcp-servers)

Choose the URL language based on the user's question language:
- Korean question → use Korean docs URL ({docs_base_url}/page-name)
- English question → use English docs URL ({docs_base_url}/en/page-name)

Examples:
- Korean: "~할 수 있습니다 ([MCP 서버]({docs_base_url}/mcp-servers) 참고)."
- English: "You can configure this ([MCP Servers]({docs_base_url}/en/mcp-servers))."

For the "references" field, also use the appropriate FULL URLs matching the question language.

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

    prompt = SYSTEM_PROMPT.format(docs_base_url=settings.docs_base_url.rstrip("/"))

    agent = Agent(
        model,
        deps_type=AgentDeps,
        output_type=VocResponse,
        instructions=prompt,
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
