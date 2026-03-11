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
