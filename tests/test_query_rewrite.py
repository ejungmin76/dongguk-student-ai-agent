import json

from django.test import SimpleTestCase

from agent.planners import build_query_rewriter_input, query_rewriter_agent
from agent.query_rewrite import QueryRewritePolicy, QueryRewritePolicyError
from agent.schemas import (
    ContextField,
    FollowUpMode,
    FollowUpResolution,
    QueryRewriteProposal,
    QueryTarget,
)


class QueryRewritePolicyTests(SimpleTestCase):
    def setUp(self):
        self.policy = QueryRewritePolicy()
        self.follow_up = FollowUpResolution(
            mode=FollowUpMode.RESOLVED,
            referenced_turn_sequences=[3],
            confidence=0.9,
            rationale="앞 질문의 졸업요건 대상을 이어서 묻는다.",
        )

    def test_rag_rewrite_preserves_original_and_adds_only_trusted_context(self):
        proposal = QueryRewriteProposal(
            target=QueryTarget.UNIVERSITY_KNOWLEDGE,
            context_fields=[ContextField.PRIMARY_MAJOR, ContextField.ADMISSION_YEAR],
            include_follow_up_reference=True,
            rationale="전공과 입학연도에 따라 적용 기준이 달라진다.",
        )
        result = self.policy.rewrite(
            original_query="그럼 전공은 몇 학점이야?",
            proposal=proposal,
            trusted_context={
                ContextField.PRIMARY_MAJOR: "컴퓨터·AI학부",
                ContextField.ADMISSION_YEAR: 2026,
            },
            follow_up=self.follow_up,
        )

        self.assertEqual(result.original_query, "그럼 전공은 몇 학점이야?")
        self.assertTrue(result.rewritten_query.startswith(result.original_query))
        self.assertIn("컴퓨터·AI학부", result.rewritten_query)
        self.assertIn("2026", result.rewritten_query)
        self.assertEqual(result.referenced_turn_sequence, 3)
        self.assertFalse(result.unchanged)

    def test_academic_rewrite_keeps_personal_context_out_of_query_text(self):
        proposal = QueryRewriteProposal(
            target=QueryTarget.ACADEMIC_RECORDS,
            context_fields=[ContextField.TARGET_TERM],
            rationale="사용자가 지정한 학기만 구조화된 조회 조건으로 사용한다.",
        )
        result = self.policy.rewrite(
            original_query="지난 학기 성적 보여줘",
            proposal=proposal,
            trusted_context={ContextField.TARGET_TERM: "2026-1"},
        )

        self.assertEqual(result.rewritten_query, "지난 학기 성적 보여줘")
        self.assertTrue(result.unchanged)
        self.assertEqual(result.applied_context[0].value, "2026-1")

    def test_unavailable_or_wrong_target_context_is_rejected_instead_of_guessed(self):
        wrong_target = QueryRewriteProposal(
            target=QueryTarget.NDRIMS_MENU,
            context_fields=[ContextField.PRIMARY_MAJOR],
            rationale="허용되지 않은 전공 정보를 메뉴 검색에 추가하려 한다.",
        )
        with self.assertRaises(QueryRewritePolicyError):
            self.policy.rewrite(
                original_query="기숙사 신청 어디서 해?",
                proposal=wrong_target,
                trusted_context={ContextField.PRIMARY_MAJOR: "컴퓨터·AI학부"},
            )

        unavailable = QueryRewriteProposal(
            target=QueryTarget.UNIVERSITY_KNOWLEDGE,
            context_fields=[ContextField.ADMISSION_YEAR],
            rationale="값이 없는 입학연도를 요구한다.",
        )
        with self.assertRaises(QueryRewritePolicyError):
            self.policy.rewrite(
                original_query="졸업요건 알려줘",
                proposal=unavailable,
                trusted_context={},
            )

    def test_unvalidated_follow_up_cannot_be_attached(self):
        proposal = QueryRewriteProposal(
            target=QueryTarget.UNIVERSITY_KNOWLEDGE,
            include_follow_up_reference=True,
            rationale="이전 대화 참조를 요청한다.",
        )
        ambiguous = FollowUpResolution(
            mode=FollowUpMode.CLARIFICATION,
            referenced_turn_sequences=[1, 3],
            confidence=0,
            rationale="후속 대상이 모호하다.",
        )
        with self.assertRaises(QueryRewritePolicyError):
            self.policy.rewrite(
                original_query="그거 알려줘",
                proposal=proposal,
                trusted_context={},
                follow_up=ambiguous,
            )

    def test_rewriter_agent_input_excludes_personal_values_and_history_text(self):
        payload = json.loads(
            build_query_rewriter_input(
                original_query="그럼 전공은 몇 학점이야?",
                target=QueryTarget.UNIVERSITY_KNOWLEDGE,
                available_context_fields=[
                    ContextField.PRIMARY_MAJOR,
                    ContextField.ADMISSION_YEAR,
                ],
                has_validated_follow_up=True,
            )
        )
        self.assertEqual(payload["target"], "university_knowledge")
        self.assertEqual(payload["available_context_fields"], ["primary_major", "admission_year"])
        self.assertNotIn("컴퓨터·AI학부", json.dumps(payload, ensure_ascii=False))
        self.assertEqual(query_rewriter_agent.tools, [])
