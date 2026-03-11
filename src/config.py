from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_prefix": "", "env_file": ".env", "extra": "ignore"}

    # Docs
    docs_base_url: str = "http://localhost:4321/docs"

    # LLM
    llm_base_url: str = "http://localhost:9013/v1"
    llm_api_key: str = ""
    llm_model: str = "qwen3.5:cloud"

    # Agent
    agent_max_iterations: int = 15
    agent_timeout: int = 120
