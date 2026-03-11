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
