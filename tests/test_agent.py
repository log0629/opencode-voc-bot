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
    tool_names = {tool.name for tool in agent._function_toolset.tools.values()}
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
