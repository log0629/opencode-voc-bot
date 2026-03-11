import argparse
import asyncio
import sys

from src.config import Settings
from src.agent import run_agent


def format_output(response, docs_base_url: str = "") -> str:
    """VocResponse를 사람이 읽기 좋은 형태로 포맷한다."""
    output_parts = []

    # 답변 본문
    output_parts.append(response.answer)

    # 참고 문서
    if response.references:
        output_parts.append("")
        output_parts.append("### 참고 문서" if _is_korean(response.answer) else "### References")
        for ref in response.references:
            url = ref.url
            # full URL이 아닌 경우 docs_base_url 기반으로 변환
            if not url.startswith("http") and docs_base_url:
                base = docs_base_url.rstrip("/")
                if url.startswith("/"):
                    # 절대 경로 (e.g., /docs/cli) → origin + path
                    from urllib.parse import urlparse
                    parsed = urlparse(base)
                    url = f"{parsed.scheme}://{parsed.netloc}{url}"
                else:
                    # 상대 경로 (e.g., cli) → base + / + path
                    url = f"{base}/{url}"
            output_parts.append(f"- [{ref.title}]({url})")

    # 에스컬레이션
    if response.escalation_needed:
        output_parts.append("")
        if _is_korean(response.answer):
            output_parts.append("> ⚠️ 담당자의 확인이 필요합니다.")
        else:
            output_parts.append("> ⚠️ Human review is required.")

    # 메타 정보
    output_parts.append("")
    output_parts.append("---")
    output_parts.append(f"Confidence: {response.confidence}")

    return "\n".join(output_parts)


def _is_korean(text: str) -> bool:
    """텍스트에 한글이 포함되어 있는지 간단히 판단한다."""
    return any("\uac00" <= ch <= "\ud7a3" for ch in text)


async def async_main(args) -> None:
    # CLI 인자가 있으면 override, 없으면 .env/환경변수에서 로드
    overrides = {}
    if args.llm_base_url:
        overrides["llm_base_url"] = args.llm_base_url
    if args.llm_api_key:
        overrides["llm_api_key"] = args.llm_api_key
    if args.llm_model:
        overrides["llm_model"] = args.llm_model
    if args.docs_base_url:
        overrides["docs_base_url"] = args.docs_base_url

    settings = Settings(**overrides)

    print("=== VOC Bot Agent ===", file=sys.stderr)
    print(f"Issue Title: {args.title}", file=sys.stderr)
    print(f"Issue Body: {args.body[:100]}{'...' if len(args.body) > 100 else ''}", file=sys.stderr)
    print(f"Docs URL: {settings.docs_base_url}", file=sys.stderr)
    print(f"LLM: {settings.llm_model} @ {settings.llm_base_url}", file=sys.stderr)
    print("=====================\n", file=sys.stderr)

    if args.comment:
        print(f"Follow-up Comment: {args.comment[:100]}{'...' if len(args.comment) > 100 else ''}", file=sys.stderr)
    print("Analyzing issue and searching documentation...\n", file=sys.stderr)

    try:
        response = await run_agent(settings, args.title, args.body, comment=args.comment or "")
        print(format_output(response, docs_base_url=settings.docs_base_url))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="VOC Bot - GitHub Issue Auto-responder")
    parser.add_argument("--title", "-t", required=True, help="GitHub issue title")
    parser.add_argument("--body", "-b", required=True, help="GitHub issue body")
    parser.add_argument("--llm-base-url", help="LLM API base URL (e.g., https://api.example.com/v1)")
    parser.add_argument("--llm-api-key", help="LLM API key")
    parser.add_argument("--llm-model", help="LLM model ID (e.g., qwen3.5:cloud)")
    parser.add_argument("--docs-base-url", help="Docs site base URL")
    parser.add_argument("--comment", "-c", help="Follow-up comment to respond to")
    args = parser.parse_args()

    asyncio.run(async_main(args))


if __name__ == "__main__":
    main()
