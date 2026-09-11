from __future__ import annotations

from urllib.parse import urlparse

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from pgvector.django import HnswIndex, VectorField

from apps.knowledge.models import EMBEDDING_DIMENSIONS


class NdrimsMenu(models.Model):
    """A verified navigational node visible inside the student nDRIMS application."""

    menu_key = models.SlugField(max_length=120, unique=True)
    title = models.CharField(max_length=200)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="children",
    )
    sort_order = models.PositiveSmallIntegerField(default=0)
    external_menu_id = models.CharField(max_length=200, blank=True)
    source_url = models.URLField(max_length=1_000)
    verified_at = models.DateField()
    is_active = models.BooleanField(default=True)
    embedding = VectorField(dimensions=EMBEDDING_DIMENSIONS, null=True, blank=True)
    embedding_model = models.CharField(max_length=100, blank=True)
    embedding_source_hash = models.CharField(max_length=64, blank=True)
    embedded_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["parent_id", "sort_order", "menu_key"]
        constraints = [
            models.CheckConstraint(
                condition=~Q(pk=F("parent")),
                name="ndrims_menu_not_own_parent",
            ),
        ]
        indexes = [
            HnswIndex(
                name="ndrims_menu_embedding_hnsw",
                fields=["embedding"],
                m=16,
                ef_construction=64,
                opclasses=["vector_cosine_ops"],
            ),
        ]
        verbose_name = "nDRIMS 메뉴"
        verbose_name_plural = "nDRIMS 메뉴"

    def clean(self) -> None:
        super().clean()
        if urlparse(self.source_url).hostname != "ndrims.dongguk.edu":
            raise ValidationError({"source_url": "nDRIMS 공식 도메인만 메뉴 출처로 등록할 수 있습니다."})

    @property
    def breadcrumb(self) -> list[str]:
        """Build the extension navigation path from verified parent nodes."""

        nodes: list[str] = []
        current: NdrimsMenu | None = self
        seen: set[int] = set()
        while current is not None:
            if current.pk is not None and current.pk in seen:
                raise ValidationError("nDRIMS 메뉴 계층에 순환 참조가 있습니다.")
            if current.pk is not None:
                seen.add(current.pk)
            nodes.append(current.title)
            current = current.parent
        return list(reversed(nodes))

    def __str__(self) -> str:
        return " > ".join(self.breadcrumb)
