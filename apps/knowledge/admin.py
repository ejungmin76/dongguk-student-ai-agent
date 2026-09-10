from django.contrib import admin

from .models import KnowledgeChunk, KnowledgeDocument, KnowledgeTermAlias


@admin.register(KnowledgeDocument)
class KnowledgeDocumentAdmin(admin.ModelAdmin):
    list_display = ("source_id", "title", "effective_year", "updated_at")
    search_fields = ("source_id", "title")


@admin.register(KnowledgeChunk)
class KnowledgeChunkAdmin(admin.ModelAdmin):
    list_display = ("chunk_id", "document", "section_ordinal", "chunk_ordinal", "embedding_model")
    search_fields = ("chunk_id", "content")
    autocomplete_fields = ("document",)
    readonly_fields = ("embedding",)


@admin.register(KnowledgeTermAlias)
class KnowledgeTermAliasAdmin(admin.ModelAdmin):
    list_display = ("alias", "canonical_term", "approval_status", "updated_at")
    list_filter = ("approval_status",)
    search_fields = ("alias", "canonical_term")
