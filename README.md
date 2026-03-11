# VOC Bot - GitHub Issue Auto-Responder

GitHub Issue에 올라오는 사용자 질문에 대해 공식 문서(docs)를 근거로 자동 응답하는 PydanticAI 기반 AI Agent.

## 주요 특징

- **문서 기반 답변**: 공식 문서만을 근거로 답변하여 hallucination 방지
- **적응형 탐색 (Adaptive Retrieval)**: 질문 난이도에 따라 문서 탐색 깊이를 자동 조절
- **다국어 지원**: 질문 언어(한국어/영어)에 맞춰 자동으로 같은 언어로 응답
- **인라인 인용**: 답변 본문에 문서 링크를 포함하고 하단에 참고 문서 목록 제공
- **에스컬레이션**: 문서로 답변 불가 시 `needs-human-review` 라벨 자동 추가
- **후속 댓글 지원**: Issue에 달린 추가 질문에도 자동 응답
- **담당자 자동 배정**: 새 Issue에 config.ini의 사용자 중 랜덤 배정

## 아키텍처

```
┌─────────────────────────────────────────────────┐
│                   VOC Bot Agent                  │
│                                                  │
│  Input: issue title + body (+ comment)           │
│                                                  │
│  Tools:                                          │
│   ├─ list_doc_pages() → 전체 페이지 목록 반환     │
│   ├─ fetch_doc_page(path) → 페이지 내용 반환      │
│   └─ search_docs(keyword) → 키워드로 페이지 검색  │
│                                                  │
│  Output: VocResponse (structured)                │
│   ├─ answer (인라인 인용 포함)                    │
│   ├─ references [{title, url}]                   │
│   ├─ confidence: sufficient | insufficient       │
│   └─ escalation_needed: bool                     │
└─────────────────────────────────────────────────┘
```

### 적응형 탐색 흐름

1. `list_doc_pages()`로 전체 페이지 목록 확인
2. 이슈 카테고리 판별 (Bug Report / Enhancement Request / Questions)
3. 관련도 높은 페이지부터 `fetch_doc_page(path)`로 내용 확인
4. 매 페이지 fetch 후 충분한 근거가 모였는지 판단
   - 충분 → 답변 생성 (조기 종료)
   - 부족 → 다음 관련 페이지 탐색
5. 모든 관련 페이지 확인 후에도 부족 → `escalation_needed: true`

## 프로젝트 구조

```
opencode-voc-bot/
├── src/
│   ├── __init__.py
│   ├── config.py              # 설정 (pydantic-settings, .env 지원)
│   ├── models.py              # Pydantic 입출력 모델 (VocResponse 등)
│   ├── tools.py               # Docs 탐색 도구 (list, fetch, search)
│   ├── agent.py               # PydanticAI Agent 정의 (시스템 프롬프트, tools)
│   └── main.py                # CLI 진입점
├── tests/
│   ├── test_config.py
│   ├── test_models.py
│   ├── test_tools.py
│   ├── test_agent.py
│   ├── test_main.py
│   └── test_integration.py
├── mock-api-server/           # OpenAI-compatible mock server (Ollama Cloud 프록시)
├── .github/workflows/
│   └── voc-bot.yml            # GitHub Actions 워크플로우
├── config.ini                 # 담당자 목록
├── requirements.txt
├── .env.example
└── pytest.ini
```

## 로컬 개발

### 사전 요구사항

- Python 3.11+
- 실행 중인 Docs 사이트 (Astro/Starlight 기반)
- OpenAI-compatible LLM API 엔드포인트

### 설치

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 환경 변수 설정

```bash
cp .env.example .env
# .env 파일 편집
```

| 변수 | 설명 | 예시 |
|---|---|---|
| `LLM_BASE_URL` | LLM API 엔드포인트 | `http://localhost:9013/v1` |
| `LLM_API_KEY` | LLM API 키 | `your-api-key` |
| `LLM_MODEL` | LLM 모델 ID | `qwen3.5:cloud` |
| `DOCS_BASE_URL` | Docs 사이트 URL | `http://localhost:4321/docs` |

### CLI 실행

```bash
# 기본 사용 (.env에서 설정 로드)
python -m src.main \
  -t "MCP 서버 설정 방법이 궁금합니다" \
  -b "MCP 서버를 설정하려고 하는데 어떻게 해야 하나요?"

# CLI 인자로 설정 override
python -m src.main \
  -t "How to configure custom tools?" \
  -b "I want to add custom tools. Where do I configure them?" \
  --llm-base-url "https://api.example.com/v1" \
  --llm-api-key "your-key" \
  --llm-model "gpt-4" \
  --docs-base-url "https://docs.example.com"

# 후속 댓글 응답
python -m src.main \
  -t "MCP 서버 설정 방법이 궁금합니다" \
  -b "MCP 서버를 설정하려고 하는데 어떻게 해야 하나요?" \
  -c "JSON 설정 파일은 어디에 위치하나요?"
```

### 테스트 실행

```bash
python -m pytest tests/ -v
```

## GitHub Actions 배포

### 워크플로우 동작

`.github/workflows/voc-bot.yml`이 다음 이벤트에 트리거:

| 이벤트 | 동작 |
|---|---|
| Issue 생성 (`issues: opened`) | VOC Bot 응답 + 담당자 랜덤 배정 |
| Issue 댓글 (`issue_comment: created`) | 후속 질문에 VOC Bot 응답 |

무한 루프 방지: `github-actions[bot]`의 댓글은 자동 무시.

### 배포 절차

#### 1. config.ini 수정

`config.ini`에 실제 GitHub 사용자 ID를 등록:

```ini
[ASSIGNEES]
users = alice, bob, charlie
```

#### 2. GitHub Secrets 등록

Repository → Settings → Secrets and variables → Actions에서 등록:

| Secret | 설명 |
|---|---|
| `LLM_BASE_URL` | LLM API 엔드포인트 (예: `https://api.example.com/v1`) |
| `LLM_API_KEY` | LLM API 인증 키 |
| `LLM_MODEL` | 사용할 모델 ID (예: `qwen3.5:cloud`) |
| `DOCS_BASE_URL` | Docs 사이트 URL (예: `https://github.samsungds.net/pages/CodeAssistant/Open-Code-Docs`) |

#### 3. Label 생성

Repository → Issues → Labels에서 `needs-human-review` 라벨 생성.
(에스컬레이션 시 자동으로 추가됨)

#### 4. 코드 Push & Merge

```bash
git push origin feat/voc-bot-agent
# GitHub에서 PR 생성 후 main 브랜치로 merge
```

Merge 후, Issue가 생성되면 자동으로 VOC Bot이 응답합니다.

## Issue 카테고리

Bot은 3가지 카테고리의 Issue를 처리합니다:

| 카테고리 | 필드 | Bot 동작 |
|---|---|---|
| **Bug Report** | CodeMate with OpenCode 버전, OS, 설명, 스크린샷 | 트러블슈팅/알려진 이슈 문서 우선 검색. 문서에 없으면 에스컬레이션. |
| **Enhancement Request** | 설명, 스크린샷 | 기존 기능 존재 여부 확인. 없으면 에스컬레이션. |
| **Firewall Request** | Requester Name, Knox-ID, Source IP Range (Class C) | 문서 검색 없이 즉시 응답. 3영업일 내 처리 안내 + 에스컬레이션. |
| **Questions** | 질문 | 문서 전체 검색 후 답변. |

## 기술 스택

| 구성 요소 | 기술 |
|---|---|
| AI Agent 프레임워크 | [PydanticAI](https://ai.pydantic.dev/) |
| LLM 통신 | OpenAI-compatible `/v1/chat/completions` |
| HTTP 클라이언트 | httpx (async) |
| HTML 파싱 | BeautifulSoup4 |
| 설정 관리 | pydantic-settings (.env + 환경변수) |
| 데이터 모델 | Pydantic v2 (structured output) |
| 테스트 | pytest + pytest-asyncio + pytest-httpx |
| CI/CD | GitHub Actions |

## 응답 예시

### 한국어 질문

```
MCP 서버는 설정 파일에서 구성할 수 있습니다. `config.json` 파일의 `mcp_servers` 섹션에서
서버 엔드포인트를 정의하시기 바랍니다 ([MCP 서버](https://docs.example.com/mcp-servers) 참고).

### 참고 문서
- [MCP 서버](https://docs.example.com/mcp-servers)
- [설정](https://docs.example.com/config)

---
Confidence: sufficient
```

### 에스컬레이션 (문서 근거 부족)

```
문서만으로는 정확한 답변을 확인할 수 없습니다. 담당자의 확인이 필요합니다.

> ⚠️ 담당자의 확인이 필요합니다.

---
Confidence: insufficient
```

(이 경우 `needs-human-review` 라벨이 자동으로 추가됩니다)
