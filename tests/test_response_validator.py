from django.test import SimpleTestCase

from agent.schemas import (
    ActionReference,
    ActionType,
    Capability,
    ContextItem,
    ResponseContext,
    ResponseDraft,
    ResultStatus,
    SourceReference,
    SourceType,
)
from agent.validators import InvalidResponseDraft, ResponseValidator


class ResponseValidatorTests(SimpleTestCase):
    def setUp(self):
        self.validator = ResponseValidator()
        self.source = SourceReference(
            source_id="academic-guide-2026",
            source_type=SourceType.UNIVERSITY_DOCUMENT,
            title="2026학년도 학업이수 가이드",
            url="https://www.dongguk.edu/academic-guide-2026",
            page=12,
        )
        self.action = ActionReference(
            action_id="leave-of-absence",
            action_type=ActionType.NAVIGATE_NDRIMS_MENU,
            label="학사행정 > 학적변동 > 휴학신청",
        )
        self.context = ResponseContext(
            status=ResultStatus.SUCCESS,
            items=[
                ContextItem(
                    step_id="records",
                    capability=Capability.ACADEMIC_RECORDS,
                    data={
                        "earned_credits": "93",
                        "cumulative_gpa": "4.5",
                    },
                ),
                ContextItem(
                    step_id="knowledge",
                    capability=Capability.UNIVERSITY_KNOWLEDGE,
                    data={
                        "results": [
                            {
                                "source_id": "academic-guide-2026",
                                "content": "총 졸업 기준은 130학점입니다.",
                            }
                        ]
                    },
                ),
            ],
            sources=[self.source],
            actions=[self.action],
            token_budget=2500,
            estimated_tokens=100,
        )

    def test_resolves_only_server_owned_sources_and_actions(self):
        draft = ResponseDraft(
            status=ResultStatus.SUCCESS,
            answer="현재 취득학점은 93학점입니다. 공식 문서 기준 총 졸업 기준은 130학점입니다.",
            source_ids=["academic-guide-2026"],
            action_ids=["leave-of-absence"],
        )

        response = self.validator.validate(draft, context=self.context)

        self.assertEqual(response.sources, [self.source])
        self.assertEqual(response.actions, [self.action])
        self.assertEqual(response.status, ResultStatus.SUCCESS)

    def test_unknown_source_or_action_id_is_rejected(self):
        with self.assertRaisesRegex(InvalidResponseDraft, "unknown source_id"):
            self.validator.validate(
                ResponseDraft(
                    status=ResultStatus.SUCCESS,
                    answer="공식 기준을 안내합니다.",
                    source_ids=["invented-source"],
                ),
                context=self.context,
            )
        with self.assertRaisesRegex(InvalidResponseDraft, "unknown action_id"):
            self.validator.validate(
                ResponseDraft(
                    status=ResultStatus.SUCCESS,
                    answer="등록된 메뉴를 안내합니다.",
                    action_ids=["invented-action"],
                ),
                context=self.context,
            )

    def test_official_document_citation_requires_validated_url(self):
        context = self.context.model_copy(
            update={
                "sources": [
                    SourceReference(
                        source_id="missing-url",
                        source_type=SourceType.UNIVERSITY_DOCUMENT,
                        title="출처 URL이 없는 문서",
                    )
                ]
            }
        )
        draft = ResponseDraft(
            status=ResultStatus.SUCCESS,
            answer="공식 문서 기준을 안내합니다.",
            source_ids=["missing-url"],
        )

        with self.assertRaisesRegex(InvalidResponseDraft, "validated URL"):
            self.validator.validate(draft, context=context)

    def test_status_cannot_be_upgraded_or_changed(self):
        partial_context = self.context.model_copy(
            update={"status": ResultStatus.PARTIAL}
        )
        draft = ResponseDraft(
            status=ResultStatus.SUCCESS,
            answer="현재 취득학점은 93학점입니다.",
        )

        with self.assertRaisesRegex(InvalidResponseDraft, "status"):
            self.validator.validate(draft, context=partial_context)

    def test_partial_or_truncated_context_requires_limitation(self):
        partial_context = self.context.model_copy(
            update={"status": ResultStatus.PARTIAL}
        )
        draft = ResponseDraft(
            status=ResultStatus.PARTIAL,
            answer="현재 취득학점은 93학점입니다.",
        )

        with self.assertRaisesRegex(InvalidResponseDraft, "requires a limitation"):
            self.validator.validate(draft, context=partial_context)

    def test_new_calculated_number_is_blocked(self):
        draft = ResponseDraft(
            status=ResultStatus.SUCCESS,
            answer="현재 취득학점은 93학점이며 졸업까지 37학점이 남았습니다.",
            source_ids=["academic-guide-2026"],
        )

        with self.assertRaisesRegex(InvalidResponseDraft, "numeric fact"):
            self.validator.validate(draft, context=self.context)

    def test_context_number_with_different_format_is_allowed(self):
        draft = ResponseDraft(
            status=ResultStatus.SUCCESS,
            answer="현재 누적 평점은 4.5이고 취득학점은 93학점입니다.",
        )

        response = self.validator.validate(draft, context=self.context)

        self.assertEqual(response.answer, draft.answer)

