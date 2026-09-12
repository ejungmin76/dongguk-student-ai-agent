"""Official university knowledge retrieval tools.

Imports are lazy to keep the embedding adapter importable without a package
initialization cycle (embedding imports the chunking module in this package).
"""

def __getattr__(name: str):
    if name in {"UniversityKnowledgeSearchTool", "build_search_university_knowledge_tool"}:
        from .search_university_knowledge import UniversityKnowledgeSearchTool, build_search_university_knowledge_tool
        return {"UniversityKnowledgeSearchTool": UniversityKnowledgeSearchTool, "build_search_university_knowledge_tool": build_search_university_knowledge_tool}[name]
    raise AttributeError(name)

__all__ = [
    "UniversityKnowledgeSearchTool",
    "build_search_university_knowledge_tool",
]
