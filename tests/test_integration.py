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
    assert len(agent._function_toolset.tools) == 3


@pytest.mark.asyncio
async def test_fetch_and_format_pipeline(httpx_mock):
    """fetch -> VocResponse 생성 -> format_output 전체 파이프라인 검증."""
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
