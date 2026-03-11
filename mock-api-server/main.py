"""
Mock API Server for Token Authentication Testing

Endpoints:
- POST /v1/token/refresh - Token refresh API (returns JWT)
- GET /api.json - Models list API (requires JWT auth, matches OPENCODE_MODELS_URL/api.json)
- POST /v1/chat/completions - Chat completions API (proxies to Ollama Cloud)

Usage:
    cd mock-api-server
    pip install -r requirements.txt
    uvicorn main:app --host 0.0.0.0 --port 9013 --reload

Then run opencode with:
    export OPENCODE_TOKEN_REFRESH_URL="http://localhost:9013/v1/token/refresh"
    export OPENCODE_MODELS_URL="http://localhost:9013"
    export OLLAMA_API_KEY="your-ollama-api-key"
    cd packages/opencode && bun run ./src/index.ts
"""

import json
import logging
import os
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import uvicorn
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from ollama import Client as OllamaClient
from pydantic import BaseModel, ConfigDict

from auth_bearer import JWTBearer
from auth_handler import create_jwt

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Mock API Server for CodeMate Token Auth")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Constants
VALID_UMS_TOKEN = "test-ums-token-12345"
CONFIG_PATH = Path(__file__).parent / "config"
CLI_MODEL_LIST_FILE = CONFIG_PATH / "cli_model_list.json"
MODEL_MAPPING = {
    "DSllmOCoder": "qwen3.5:397b-cloud",
    "DSllmOCoderStable": "minimax-m2.5:cloud",
}
THINKING_MODELS = {"qwen3.5:397b-cloud", "qwen3-next:80b", "minimax-m2.5:cloud", "minimax-m2.1:cloud"}


def _get_models_with_cli() -> dict:
    """Load cli_model_list.json and return model configs"""
    if CLI_MODEL_LIST_FILE.exists():
        with open(CLI_MODEL_LIST_FILE, "r") as f:
            return json.load(f)
    logger.warning("cli_model_list.json not found, returning empty dict")
    return {}


class TokenRefreshRequest(BaseModel):
    ums_token: str


class TokenRefreshResponse(BaseModel):
    access_token: str


# Chat Completions Models (OpenAI-compatible)
class ToolCall(BaseModel):
    id: str
    type: str = "function"
    function: Dict[str, Any]


class ChatMessage(BaseModel):
    role: str
    content: Optional[Union[str, List[Any]]] = None
    tool_calls: Optional[List[ToolCall]] = None
    tool_call_id: Optional[str] = None


class Tool(BaseModel):
    type: str = "function"
    function: Dict[str, Any]


class ChatCompletionRequest(BaseModel):
    model_config = ConfigDict(extra="allow")
    model: str
    messages: List[ChatMessage]
    stream: Optional[bool] = False
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    tools: Optional[List[Tool]] = None
    tool_choice: Optional[Any] = None


# Ollama Cloud client (lazy initialization)
_ollama_client: Optional[OllamaClient] = None


def get_ollama_client() -> OllamaClient:
    """Get or create Ollama Cloud client"""
    global _ollama_client
    if _ollama_client is None:
        api_key = os.environ.get("OLLAMA_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="OLLAMA_API_KEY not set")
        _ollama_client = OllamaClient(
            host="https://ollama.com",
            headers={"Authorization": f"Bearer {api_key}"}
        )
    return _ollama_client


# Model mapping: codemate model -> ollama model
# If model not in mapping, use as-is (most models use same name)
MODEL_MAPPING = {
    "DSllmOCoder": "qwen3.5:397b-cloud",
    "DSllmOCoderStable": "minimax-m2.5:cloud",
}

# Models that support thinking/reasoning via Ollama's think parameter
THINKING_MODELS = {"qwen3.5:397b-cloud", "qwen3-next:80b", "minimax-m2.5:cloud", "minimax-m2.1:cloud"}


@app.on_event("startup")
async def startup_event():
    logger.info("=" * 50)
    logger.info("Mock API Server for CodeMate Token Auth Testing")
    logger.info("=" * 50)
    logger.info(f"Valid UMS Token: {VALID_UMS_TOKEN}")
    logger.info(f"CLI Model List File: {CLI_MODEL_LIST_FILE}")
    logger.info(f"CLI Model List File Exists: {CLI_MODEL_LIST_FILE.exists()}")
    logger.info("")
    logger.info("Endpoints:")
    logger.info("  POST /v1/token/refresh - Returns JWT access_token")
    logger.info("  GET  /api.json - Models API (matches OPENCODE_MODELS_URL/api.json)")
    logger.info("  POST /v1/chat/completions - Chat API (proxies to Ollama Cloud)")
    logger.info("")
    logger.info("Usage:")
    logger.info('  export OPENCODE_TOKEN_REFRESH_URL="http://localhost:9013/v1/token/refresh"')
    logger.info('  export OPENCODE_MODELS_URL="http://localhost:9013"')
    logger.info("=" * 50)


@app.post("/v1/token/refresh", response_model=TokenRefreshResponse)
async def token_refresh(request: TokenRefreshRequest):
    """
    Token refresh endpoint.
    Accepts UMS token and returns JWT access token.
    """
    logger.info("POST /v1/token/refresh")
    token_display = request.ums_token[:20] + "..." if len(request.ums_token) > 20 else request.ums_token
    logger.info(f"  -> UMS Token: {token_display}")

    if request.ums_token != VALID_UMS_TOKEN:
        logger.warning("  -> 401 Unauthorized: Invalid token")
        raise HTTPException(status_code=401, detail="Invalid UMS token")

    # Generate JWT token
    jwt_token = create_jwt(user_id="test-user-001", user_name="Test User")
    logger.info("  -> 200 OK: Returning JWT access_token")
    logger.info(f"  -> JWT: {jwt_token[:50]}...")
    return TokenRefreshResponse(access_token=jwt_token)


@app.get("/api.json")
async def get_models(jwt_data: Tuple = Depends(JWTBearer())):
    """
    Models list endpoint.
    Matches OPENCODE_MODELS_URL/api.json endpoint.
    Requires JWT Bearer token in Authorization header.
    Returns models data from cli_model_list.json.
    """
    user_id, user_name, ep_id, division, department, upr_department, lwr_department, credentials = jwt_data

    logger.info("GET /api.json")
    logger.info(f"  -> User: {user_id} ({user_name})")
    logger.info(f"  -> Department: {department}")

    models = _get_models_with_cli()
    logger.info(f"  -> 200 OK: Returning {len(models)} providers")
    return models


@app.post("/v1/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    jwt_data: Tuple = Depends(JWTBearer())
):
    """
    Chat completions endpoint (OpenAI-compatible).
    Proxies requests to Ollama Cloud.
    Requires JWT Bearer token in Authorization header.
    """
    user_id, user_name, *_ = jwt_data

    logger.info("POST /v1/chat/completions")
    logger.info(f"  -> User: {user_id} ({user_name})")
    logger.info(f"  -> Model: {request.model}")
    logger.info(f"  -> Stream: {request.stream}")
    logger.info(f"  -> Messages: {len(request.messages)}")
    logger.info(f"  -> Tools: {len(request.tools) if request.tools else 0}")

    # Map model name - use request.model directly if not in mapping
    ollama_model = MODEL_MAPPING.get(request.model, request.model)
    logger.info(f"  -> Ollama Model: {ollama_model}")

    messages = _convert_messages(request.messages)
    tools = [t.model_dump() for t in request.tools] if request.tools else None

    try:
        client = get_ollama_client()

        # Build Ollama chat options
        chat_options = {
            "model": ollama_model,
            "messages": messages,
            "stream": request.stream or False,
        }
        if tools:
            chat_options["tools"] = tools
        # Enable thinking for supported models
        if ollama_model in THINKING_MODELS:
            chat_options["think"] = True
            logger.info("  -> Thinking: enabled")

        if request.stream:
            # Streaming response
            def generate_stream():
                request_id = f"chatcmpl-{uuid.uuid4().hex[:24]}"
                created = int(time.time())
                accumulated_tool_calls = []

                for part in client.chat(**chat_options):
                    msg = part.get("message", {})
                    content = msg.get("content", "")
                    thinking = msg.get("thinking", "")
                    tool_calls = msg.get("tool_calls")

                    delta = {}
                    if thinking:
                        delta["reasoning_content"] = thinking
                    if content:
                        delta["content"] = content
                    if tool_calls:
                        # Convert Ollama tool_calls to OpenAI format
                        formatted_tool_calls = []
                        for i, tc in enumerate(tool_calls):
                            formatted_tc = {
                                "index": i,
                                "id": tc.get("id", f"call_{uuid.uuid4().hex[:24]}"),
                                "type": "function",
                                "function": {
                                    "name": tc.get("function", {}).get("name", ""),
                                    "arguments": json.dumps(tc.get("function", {}).get("arguments", {}))
                                }
                            }
                            formatted_tool_calls.append(formatted_tc)
                            accumulated_tool_calls.append(formatted_tc)
                        delta["tool_calls"] = formatted_tool_calls

                    if delta:
                        chunk = {
                            "id": request_id,
                            "object": "chat.completion.chunk",
                            "created": created,
                            "model": request.model,
                            "choices": [{
                                "index": 0,
                                "delta": delta,
                                "finish_reason": None
                            }]
                        }
                        yield f"data: {json.dumps(chunk)}\n\n"

                # Final chunk
                finish_reason = "tool_calls" if accumulated_tool_calls else "stop"
                final_chunk = {
                    "id": request_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": request.model,
                    "choices": [{
                        "index": 0,
                        "delta": {},
                        "finish_reason": finish_reason
                    }]
                }
                yield f"data: {json.dumps(final_chunk)}\n\n"
                yield "data: [DONE]\n\n"

            logger.info("  -> 200 OK: Streaming response")
            return StreamingResponse(
                generate_stream(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                }
            )
        else:
            # Non-streaming response
            response = client.chat(**chat_options)
            msg = response.get("message", {})
            content = msg.get("content", "")
            thinking = msg.get("thinking", "")
            tool_calls = msg.get("tool_calls")

            response_message = {
                "role": "assistant",
                "content": content
            }
            if thinking:
                response_message["reasoning_content"] = thinking

            # Handle tool calls in response
            if tool_calls:
                formatted_tool_calls = []
                for tc in tool_calls:
                    formatted_tc = {
                        "id": tc.get("id", f"call_{uuid.uuid4().hex[:24]}"),
                        "type": "function",
                        "function": {
                            "name": tc.get("function", {}).get("name", ""),
                            "arguments": json.dumps(tc.get("function", {}).get("arguments", {}))
                        }
                    }
                    formatted_tool_calls.append(formatted_tc)
                response_message["tool_calls"] = formatted_tool_calls
                finish_reason = "tool_calls"
            else:
                finish_reason = "stop"

            result = {
                "id": f"chatcmpl-{uuid.uuid4().hex[:24]}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": request.model,
                "choices": [{
                    "index": 0,
                    "message": response_message,
                    "finish_reason": finish_reason
                }],
                "usage": {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0
                }
            }
            logger.info(f"  -> 200 OK: Non-streaming response (finish_reason: {finish_reason})")
            return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"  -> 500 Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ollama API error: {str(e)}")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "valid_ums_token": VALID_UMS_TOKEN,
        "cli_model_list_exists": CLI_MODEL_LIST_FILE.exists(),
        "ollama_api_key_set": bool(os.environ.get("OLLAMA_API_KEY"))
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9013)
