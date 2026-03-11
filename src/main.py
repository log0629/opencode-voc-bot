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


async def async_main(title: str, body: str) -> None:
    settings = Settings()
    print("=== VOC Bot Agent ===")
    print(f"Issue Title: {title}")
    print(f"Issue Body: {body[:100]}{'...' if len(body) > 100 else ''}")
    print(f"Docs URL: {settings.docs_base_url}")
    print(f"LLM: {settings.llm_model} @ {settings.llm_base_url}")
    print("=====================\n")

    print("Analyzing issue and searching documentation...\n")

    try:
        response = await run_agent(settings, title, body)
        print(format_output(response, docs_base_url=settings.docs_base_url))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="VOC Bot - GitHub Issue Auto-responder")
    parser.add_argument("--title", "-t", required=True, help="GitHub issue title")
    parser.add_argument("--body", "-b", required=True, help="GitHub issue body")
    args = parser.parse_args()

    asyncio.run(async_main(args.title, args.body))


if __name__ == "__main__":
    main()
