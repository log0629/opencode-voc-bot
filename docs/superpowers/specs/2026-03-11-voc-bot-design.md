# VOC Bot Design Spec

## Overview

GitHub issue에 올라오는 사용자 질문에 대해 docs를 근거로 1차 응답을 자동 생성하는 agent.
단순 데모가 아닌, hallucination을 최소화하고 근거 기반의 정확한 답변을 제공하는 고품질 VOC bot.

## Decisions

| 항목 | 결정 |
|---|---|
| 언어/프레임워크 | Python + PydanticAI |
| 트리거 | CLI 먼저 → 나중에 GitHub Actions 연동 |
| Docs 탐색 | 실시간 크롤링 (On-demand HTTP fetch) |
| 탐색 전략 | 적응형 탐색 (Adaptive Retrieval) |
| 근거 표시 | 인라인 인용 + 하단 참고 링크 |
| 답변 불가 시 | 명시 + 관련 문서 안내 + 에스컬레이션 요청 |
| 답변 톤 | 공식적/정중한 톤 |
| 답변 언어 | 질문 언어와 동일 (자동 감지) |
| LLM endpoint | OpenAI-compatible `/v1/chat/completions` |

## Architecture: Multi-step Agent with Tools

### Why This Approach

3가지 방식을 비교한 결과, Multi-step Agent (Tool-based) 방식을 선택.

1. **Single-shot RAG** — 관련 페이지를 한 번에 선택해야 하므로 누락 위험. 여러 문서 종합 어려움. ❌
2. **Multi-step Agent (Tool-based)** — agent가 도구를 반복 호출하며 자율적으로 탐색 깊이 조절. 적응형 탐색에 자연스럽게 부합. ✅
3. **Two-phase Pipeline** — 구조가 고정적이라 유연성 부족. ⚠️

선택 이유:
- 적응형 탐색과 자연스럽게 일치 — 쉬운 질문은 빠르게, 어려운 질문은 철저하게
- PydanticAI의 tool/structured output/dependency injection 강점 활용
- Multi-hop 질문 대응 — 한 페이지에서 발견한 단서로 다른 페이지 추가 탐색 가능
- Hallucination 방지 — tool로 가져온 문서 내용만 근거로 사용하도록 시스템 프롬프트로 강제
- max iterations로 무한 루프 방지

### Architecture Diagram

```
┌─────────────────────────────────────────────────┐
│                   VOC Bot Agent                  │
│                                                  │
│  Input: issue title + body                       │
│                                                  │
│  Tools:                                          │
│   ├─ list_doc_pages() → 전체 페이지 목록 반환     │
│   ├─ fetch_doc_page(path) → 페이지 내용 반환      │
│   └─ search_docs(keyword) → 키워드로 페이지 검색  │
│                                                  │
│  System Prompt:                                  │
│   "문서에서 가져온 내용만 근거로 사용하라"          │
│   "충분한 근거가 모이면 답변을 생성하라"            │
│   "근거가 부족하면 명확히 밝혀라"                  │
│                                                  │
│  Output: structured answer                       │
│   ├─ answer (인라인 인용 포함)                    │
│   ├─ references [{title, url}]                   │
│   ├─ confidence: sufficient | insufficient       │
│   └─ escalation_needed: bool                     │
└─────────────────────────────────────────────────┘
```

### Adaptive Retrieval Flow

1. Agent가 `list_doc_pages()`로 전체 페이지 목록 확인
2. 질문과 관련될 수 있는 페이지를 판단
3. 관련도가 높은 페이지부터 `fetch_doc_page(path)`로 내용 확인
4. 매 페이지 fetch 후 "충분한 근거가 모였는가?" 판단
   - 충분 → 답변 생성 (조기 종료)
   - 부족 → 다음 관련 페이지 탐색
5. 모든 관련 페이지를 확인했는데도 부족 → escalation_needed: true

## Project Structure

```
opencode-voc-bot/
├── mock-api-server/          # GitHub에서 가져온 mock server
├── src/
│   ├── agent.py              # PydanticAI agent 정의 (시스템 프롬프트, tools)
│   ├── tools.py              # docs 탐색 도구 (list, fetch, search)
│   ├── models.py             # Pydantic 입출력 모델 정의
│   ├── config.py             # 설정 (API URL, docs base URL 등)
│   └── main.py               # CLI 진입점
├── requirements.txt
└── .env.example
```

## Data Models

### Input

```python
class IssueInput:
    title: str
    body: str
```

### Output (Structured)

```python
class Reference:
    title: str
    url: str

class VocResponse:
    answer: str                    # 인라인 인용 포함된 답변
    references: list[Reference]    # 하단 참고 링크
    confidence: Literal["sufficient", "insufficient"]
    escalation_needed: bool
```

## Agent Tools

| Tool | 역할 | 구현 |
|---|---|---|
| `list_doc_pages()` | 전체 docs 페이지 목록 반환 | docs 사이트 nav/sitemap에서 추출 |
| `fetch_doc_page(path)` | 특정 페이지 본문 텍스트 반환 | HTTP GET → HTML 파싱 (BeautifulSoup) |
| `search_docs(keyword)` | 키워드로 페이지 내 검색 | 페이지 목록 중 제목/내용에 키워드 포함된 것 필터 |

## System Prompt Rules

1. 반드시 tool로 가져온 문서 내용만 근거로 사용할 것
2. 추측하지 말 것 — 문서에 없으면 "확인할 수 없다"고 명시
3. 충분한 근거가 모이면 답변 생성, 부족하면 계속 탐색
4. 답변에 인라인 인용 + 하단 참고 링크 포함
5. 사용자 질문의 언어와 동일한 언어로 답변
6. 공식적/정중한 톤 사용 (한글: "~하시기 바랍니다", 영문: "Please refer to...")
7. 근거 부족 시 escalation_needed: true 설정

## Safety Guards

- **max iterations**: agent의 tool 호출을 최대 15회로 제한
- **timeout**: 전체 실행 시간 120초 제한
- **중복 fetch 방지**: 이미 가져온 페이지는 다시 fetch하지 않음

## Escalation Behavior

답변 불가 시:
1. 댓글에 "문서만으로는 정확한 답변을 확인할 수 없습니다. 담당자의 확인이 필요합니다." 명시
2. 관련될 수 있는 문서 페이지 링크 안내
3. (GitHub Actions 연동 시) `needs-human-review` 라벨 추가

## Mock API Server

GitHub repo에서 가져온 FastAPI 기반 mock server 사용:
- `POST /v1/chat/completions` — OpenAI-compatible chat endpoint (Ollama Cloud 프록시)
- JWT 인증 필요 (테스트용 토큰: `test-ums-token-12345`)
- 실제 테스트 시 사용자가 OLLAMA_API_KEY 입력

## Docs Site

- Base URL: `http://localhost:4321/docs/`
- Astro (Starlight) 기반
- ~30개 MDX 페이지: agents, cli, commands, config, custom-tools, ecosystem, enterprise, formatters, github, gitlab, ide, keybinds, lsp, mcp-servers, models, modes, network, permissions, plugins, practical-tips, providers, rules, sdk, server, share, skills, themes, tools, troubleshooting, tui, web, windows-wsl, zen
