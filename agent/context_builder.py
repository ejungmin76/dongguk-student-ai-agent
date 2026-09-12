"""Build minimal, citable response context from raw multi-tool results."""

import json
import math
from collections.abc import Mapping
from typing import Any

from pydantic import ValidationError

from agent.schemas import (
    ActionReference,
    Capability,
    ContextItem,
    ContextOmission,
    ErrorDetail,
    PlanExecutionResult,
    ResponseContext,
    SourceReference,
    StepExecutionState,
)


class ContextBudgetError(ValueError):
    pass


class ContextBuilder:
    """Project Tool envelopes into the smallest response-safe common contract."""

    def __init__(self, *, token_budget: int = 2_500) -> None:
        if token_budget < 256:
            raise ValueError("token_budget must be at least 256")
        self.token_budget = token_budget

    def build(self, execution: PlanExecutionResult) -> ResponseContext:
        items: list[dict[str, Any]] = []
        sources: list[SourceReference] = []
        actions: list[ActionReference] = []
        errors: list[ErrorDetail] = []

        for step in execution.steps:
            if step.error is not None:
                errors.append(step.error)
            if step.output is None:
                continue

            output = step.output
            errors.extend(self._validated_models(output.get("errors"), ErrorDetail))
            sources.extend(
                self._validated_models(output.get("sources"), SourceReference)
            )
            actions.extend(
                self._validated_models(output.get("actions"), ActionReference)
            )

            if step.state not in {
                StepExecutionState.SUCCESS,
                StepExecutionState.PARTIAL,
            }:
                continue
            data = output.get("data")
            if not isinstance(data, Mapping):
                errors.append(
                    ErrorDetail(
                        code="CONTEXT_INVALID_TOOL_DATA",
                        message="도구 결과를 응답 컨텍스트로 변환할 수 없습니다.",
                    )
                )
                continue
            items.append(
                ContextItem(
                    step_id=step.step_id,
                    capability=step.capability,
                    data=self._project_data(step.capability, data),
                ).model_dump(mode="json")
            )

        payload = {
            "status": execution.status,
            "items": items,
            "sources": self._deduplicate_models(sources),
            "actions": self._deduplicate_models(actions),
            "errors": self._deduplicate_models(errors),
            "truncated": False,
            "omissions": [],
        }
        self._fit_to_budget(payload)

        estimated_tokens = self.estimate_tokens(payload)
        if estimated_tokens > self.token_budget:
            raise ContextBudgetError("response context cannot fit the token budget")
        return ResponseContext(
            **payload,
            token_budget=self.token_budget,
            estimated_tokens=estimated_tokens,
        )

    @staticmethod
    def estimate_tokens(value: Any) -> int:
        """Conservative Korean-safe estimate until a provider tokenizer is installed."""

        serialized = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        return math.ceil(len(serialized) / 2)

    def _fit_to_budget(self, payload: dict[str, Any]) -> None:
        omissions: dict[str, int] = {}

        def record_omission(path: str) -> None:
            omissions[path] = omissions.get(path, 0) + 1
            payload["truncated"] = True
            payload["omissions"] = [
                ContextOmission(
                    path=item_path,
                    reason="token_budget",
                    count=count,
                ).model_dump(mode="json")
                for item_path, count in sorted(omissions.items())
            ]

        while self.estimate_tokens(payload) > self.token_budget:
            list_path = self._largest_nested_list(payload["items"])
            if list_path is not None:
                parent, key, path = list_path
                parent[key].pop()
                record_omission(path)
                continue

            if payload["items"]:
                payload["items"].pop()
                record_omission("items")
                continue
            if payload["actions"]:
                payload["actions"].pop()
                record_omission("actions")
                continue
            if payload["sources"]:
                payload["sources"].pop()
                record_omission("sources")
                continue
            if payload["errors"]:
                payload["errors"].pop()
                record_omission("errors")
                continue
            break

    @classmethod
    def _largest_nested_list(
        cls,
        items: list[dict[str, Any]],
    ) -> tuple[dict[str, Any], str, str] | None:
        candidates: list[tuple[int, dict[str, Any], str, str]] = []

        def collect(value: Any, path: str) -> None:
            if isinstance(value, dict):
                for key, child in value.items():
                    child_path = f"{path}.{key}" if path else key
                    if isinstance(child, list) and child:
                        candidates.append(
                            (
                                cls.estimate_tokens(child),
                                value,
                                key,
                                child_path,
                            )
                        )
                    collect(child, child_path)
            elif isinstance(value, list):
                for index, child in enumerate(value):
                    collect(child, f"{path}[{index}]")

        collect(items, "items")
        if not candidates:
            return None
        _, parent, key, path = max(candidates, key=lambda item: item[0])
        return parent, key, path

    @staticmethod
    def _validated_models(values: Any, model_type: type[Any]) -> list[Any]:
        if not isinstance(values, list):
            return []
        validated: list[Any] = []
        for value in values:
            try:
                validated.append(model_type.model_validate(value))
            except ValidationError:
                continue
        return validated

    @staticmethod
    def _deduplicate_models(models: list[Any]) -> list[dict[str, Any]]:
        unique: list[dict[str, Any]] = []
        seen: set[str] = set()
        for model in models:
            dumped = model.model_dump(mode="json")
            key = json.dumps(dumped, ensure_ascii=False, sort_keys=True)
            if key not in seen:
                seen.add(key)
                unique.append(dumped)
        return unique

    @classmethod
    def _project_data(
        cls,
        capability: Capability,
        data: Mapping[str, Any],
    ) -> dict[str, Any]:
        projectors = {
            Capability.STUDENT_PROFILE: cls._project_student_profile,
            Capability.ACADEMIC_RECORDS: cls._project_academic_records,
            Capability.CURRENT_SCHEDULE: cls._project_current_schedule,
            Capability.UNIVERSITY_KNOWLEDGE: cls._project_university_knowledge,
            Capability.NDRIMS_MENU: cls._project_ndrims_menu,
        }
        projector = projectors.get(capability, cls._strip_sensitive_fields)
        return projector(data)

    @staticmethod
    def _pick(data: Mapping[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
        return {field: data[field] for field in fields if field in data}

    @classmethod
    def _project_student_profile(cls, data: Mapping[str, Any]) -> dict[str, Any]:
        return cls._pick(
            data,
            (
                "admission_year",
                "current_semester",
                "status",
                "program_track",
                "primary_major_name",
                "secondary_major_name",
            ),
        )

    @classmethod
    def _project_academic_records(cls, data: Mapping[str, Any]) -> dict[str, Any]:
        return cls._pick(
            data,
            (
                "cumulative_gpa",
                "gpa_credits",
                "attempted_credits",
                "earned_credits",
                "term_summaries",
                "category_summaries",
                "records",
            ),
        )

    @classmethod
    def _project_current_schedule(cls, data: Mapping[str, Any]) -> dict[str, Any]:
        return cls._pick(
            data,
            (
                "year",
                "semester",
                "total_credits",
                "courses",
                "conflicts",
            ),
        )

    @classmethod
    def _project_university_knowledge(cls, data: Mapping[str, Any]) -> dict[str, Any]:
        results = data.get("results")
        if not isinstance(results, list):
            return {}
        return {
            "results": [
                cls._pick(
                    result,
                    (
                        "source_id",
                        "heading_path",
                        "content",
                        "document_status",
                        "effective_year",
                        "effective_from",
                        "effective_to",
                    ),
                )
                for result in results
                if isinstance(result, Mapping)
            ]
        }

    @classmethod
    def _project_ndrims_menu(cls, data: Mapping[str, Any]) -> dict[str, Any]:
        candidates = data.get("candidates")
        result = cls._pick(data, ("requires_user_selection",))
        if isinstance(candidates, list):
            result["candidates"] = [
                cls._pick(
                    candidate,
                    ("menu_key", "title", "breadcrumb", "external_menu_id"),
                )
                for candidate in candidates
                if isinstance(candidate, Mapping)
            ]
        return result

    @classmethod
    def _strip_sensitive_fields(cls, data: Mapping[str, Any]) -> dict[str, Any]:
        private_keys = {"student_number", "display_name", "execution_id"}

        def sanitize(value: Any) -> Any:
            if isinstance(value, Mapping):
                return {
                    key: sanitize(child)
                    for key, child in value.items()
                    if key not in private_keys
                }
            if isinstance(value, list):
                return [sanitize(child) for child in value]
            return value

        return sanitize(data)
