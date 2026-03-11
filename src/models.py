from typing import Literal

from pydantic import BaseModel, Field


class IssueInput(BaseModel):
    title: str = Field(description="GitHub issue 제목")
    body: str = Field(description="GitHub issue 본문")


class Reference(BaseModel):
    title: str = Field(description="참고 문서 제목")
    url: str = Field(description="참고 문서 URL")


class VocResponse(BaseModel):
    answer: str = Field(
        description="인라인 인용을 포함한 답변. 사용자 질문의 언어와 동일한 언어로 작성."
    )
    references: list[Reference] = Field(
        description="답변에서 참고한 문서 목록"
    )
    confidence: Literal["sufficient", "insufficient"] = Field(
        description="문서 근거의 충분성"
    )
    escalation_needed: bool = Field(
        description="담당자 에스컬레이션 필요 여부"
    )
