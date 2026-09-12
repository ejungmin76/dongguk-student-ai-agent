from datetime import date

from django.test import TestCase

from agent.schemas.action import ActionType
from agent.schemas.status import ResultStatus
from apps.ndrims.models import NdrimsMenu
from apps.ndrims.services import NdrimsMenuRetriever, index_menu_embeddings
from tools.ndrims.find_menu import NdrimsMenuSearchTool
from tools.ndrims.schemas import NdrimsMenuSearchInput


def vector(first: float, second: float = 0.0) -> list[float]:
    return [first, second] + [0.0] * 766


class FakeEmbedder:
    model_name = "fake-menu-embedding"
    dimensions = 768

    def __init__(self, query_vector=None):
        self.query_vector = query_vector or vector(1.0)
        self.document_calls = 0

    def embed_query(self, query: str) -> list[float]:
        return self.query_vector

    def embed_texts(self, texts):
        self.document_calls += 1
        return [vector(1.0, index / 10) for index, _ in enumerate(texts)]


class NdrimsMenuSearchTests(TestCase):
    source_url = "https://ndrims.dongguk.edu/main/main.clx"

    def menu(self, menu_key, title, embedding, *, parent=None, active=True):
        return NdrimsMenu.objects.create(
            menu_key=menu_key,
            title=title,
            parent=parent,
            source_url=self.source_url,
            verified_at=date(2026, 9, 11),
            is_active=active,
            embedding=embedding,
            embedding_model="fake-menu-embedding",
        )

    def test_returns_registered_active_menu_and_verified_open_url_action(self):
        root = self.menu("course-registration", "수강신청", vector(0.9, 0.1))
        target = self.menu("course-registration-history", "수강신청내역확인", vector(1.0), parent=root)
        self.menu("inactive-menu", "비활성", vector(1.0), active=False)
        retriever = NdrimsMenuRetriever(FakeEmbedder(), minimum_score=0.8)

        result = NdrimsMenuSearchTool(retriever).execute(
            NdrimsMenuSearchInput(question="내 수강목록 어디서 봐?", top_k=1)
        )

        self.assertEqual(result.status, ResultStatus.SUCCESS)
        self.assertEqual(result.data.candidates[0].menu_key, target.menu_key)
        self.assertEqual(result.data.candidates[0].breadcrumb, ["수강신청", "수강신청내역확인"])
        self.assertEqual(result.actions[0].action_type, ActionType.OPEN_URL)
        self.assertEqual(str(result.actions[0].url), self.source_url)
        self.assertFalse(result.data.requires_user_selection)

    def test_same_named_dormitory_actions_require_user_selection(self):
        namsan = self.menu("namsan", "남산학사", vector(0.9, 0.1))
        chungmu = self.menu("chungmu", "충무학사", vector(0.9, 0.1))
        self.menu("namsan-overnight", "외박신청/취소신청", vector(1.0), parent=namsan)
        self.menu("chungmu-overnight", "외박신청/취소신청", vector(1.0), parent=chungmu)
        retriever = NdrimsMenuRetriever(FakeEmbedder(), minimum_score=0.8)

        result = NdrimsMenuSearchTool(retriever).execute(
            NdrimsMenuSearchInput(question="기숙사 외박 신청", top_k=2)
        )

        self.assertEqual(result.status, ResultStatus.SUCCESS)
        self.assertTrue(result.data.requires_user_selection)

    def test_returns_unavailable_when_no_candidate_passes_threshold(self):
        self.menu("grades", "성적", vector(0.0, 1.0))
        retriever = NdrimsMenuRetriever(FakeEmbedder(), minimum_score=0.8)

        result = NdrimsMenuSearchTool(retriever).execute(
            NdrimsMenuSearchInput(question="없는 메뉴", top_k=1)
        )

        self.assertEqual(result.status, ResultStatus.UNAVAILABLE)
        self.assertEqual(result.errors[0].code, "NDRIMS_MENU_NOT_FOUND")

    def test_menu_embedding_index_is_idempotent(self):
        root = self.menu("dormitory", "기숙사", None)
        self.menu("dormitory-overnight", "외박신청", None, parent=root)
        embedder = FakeEmbedder()

        first = index_menu_embeddings(embedder)
        second = index_menu_embeddings(embedder)

        self.assertEqual(first.embedded, 2)
        self.assertEqual(second.skipped, 2)
        self.assertEqual(embedder.document_calls, 1)
