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
