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
    output = format_output(response, docs_base_url="http://localhost:4321/docs")
    assert "MCP 서버는 설정 파일에서 구성할 수 있습니다." in output
    assert "### 참고 문서" in output
    assert "[MCP Servers](http://localhost:4321/docs/mcp-servers)" in output
    assert "Confidence: sufficient" in output


def test_format_output_english():
    response = VocResponse(
        answer="You can configure MCP servers in the config file.",
        references=[Reference(title="MCP Servers", url="/docs/mcp-servers")],
        confidence="sufficient",
        escalation_needed=False,
    )
    output = format_output(response, docs_base_url="http://localhost:4321/docs")
    assert "### References" in output
    assert "http://localhost:4321/docs/mcp-servers" in output


def test_format_output_full_url_passthrough():
    """이미 full URL인 경우 그대로 유지."""
    response = VocResponse(
        answer="설정 방법입니다.",
        references=[Reference(title="CLI", url="http://localhost:4321/docs/cli")],
        confidence="sufficient",
        escalation_needed=False,
    )
    output = format_output(response, docs_base_url="http://localhost:4321/docs")
    assert "http://localhost:4321/docs/cli" in output


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
