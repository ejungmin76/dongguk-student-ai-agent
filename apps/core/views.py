import json

from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse, StreamingHttpResponse
from django.middleware.csrf import get_token
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.views.decorators.http import require_POST
from pydantic import ValidationError

from agent.conversation import ConversationAccessError, ConversationExpiredError

from .schemas import ChatRequestSchema
from .services import AgentChatService
from .streaming import AgentChatStreamService, encode_sse


agent_chat_service = AgentChatService()
agent_chat_stream_service = AgentChatStreamService(chat_service=agent_chat_service)


def browser_subject(request) -> str:
    """Anonymous, server-issued browser identity; no student data is involved."""
    if not request.session.session_key:
        request.session.create()
    return f"anonymous-browser:{request.session.session_key}"


def health_check(request):
    return JsonResponse(
        {
            "status": "ok",
            "service": "dongguk-student-ai-agent",
        }
    )


@ensure_csrf_cookie
def csrf_token(request):
    return JsonResponse({"csrf_token": get_token(request)})


def api_error(*, code: str, message: str, status: int) -> JsonResponse:
    return JsonResponse({"error": {"code": code, "message": message}}, status=status)


@require_POST
def agent_chat(request):
    """Authenticated, session-bound JSON entry point for the web UI."""

    if request.content_type != "application/json":
        return api_error(code="UNSUPPORTED_MEDIA_TYPE", message="application/json 요청만 허용됩니다.", status=415)
    try:
        payload = ChatRequestSchema.model_validate_json(request.body)
    except (ValidationError, ValueError, json.JSONDecodeError):
        return api_error(code="INVALID_REQUEST", message="message와 선택적 session_id 형식을 확인해 주세요.", status=400)

    try:
        response = agent_chat_service.chat(
            authenticated_subject=browser_subject(request),
            message=payload.message,
            session_id=str(payload.session_id) if payload.session_id else None,
        )
    except ConversationAccessError:
        return api_error(code="SESSION_FORBIDDEN", message="접근할 수 없는 대화 세션입니다.", status=403)
    except ConversationExpiredError:
        return api_error(code="SESSION_EXPIRED", message="대화 세션이 만료되었습니다. 새 대화를 시작해 주세요.", status=410)
    except ObjectDoesNotExist:
        return api_error(code="SESSION_NOT_FOUND", message="대화 세션을 찾을 수 없습니다.", status=404)
    except (RuntimeError, TypeError):
        return api_error(code="AGENT_UNAVAILABLE", message="현재 답변을 준비하지 못했습니다. 잠시 후 다시 시도해 주세요.", status=503)

    return JsonResponse(response.model_dump(mode="json"))


@require_POST
def agent_chat_stream(request):
    if request.content_type != "application/json":
        return api_error(code="UNSUPPORTED_MEDIA_TYPE", message="application/json 요청만 허용됩니다.", status=415)
    try:
        payload = ChatRequestSchema.model_validate_json(request.body)
        subject = browser_subject(request)
        run = agent_chat_stream_service.start(authenticated_subject=subject, session_id=str(payload.session_id) if payload.session_id else None)
    except ConversationAccessError:
        return api_error(code="SESSION_FORBIDDEN", message="접근할 수 없는 대화 세션입니다.", status=403)
    except ConversationExpiredError:
        return api_error(code="SESSION_EXPIRED", message="대화 세션이 만료되었습니다. 새 대화를 시작해 주세요.", status=410)
    except (ValidationError, ValueError, json.JSONDecodeError):
        return api_error(code="INVALID_REQUEST", message="message와 선택적 session_id 형식을 확인해 주세요.", status=400)
    except ObjectDoesNotExist:
        return api_error(code="SESSION_NOT_FOUND", message="대화 세션을 찾을 수 없습니다.", status=404)
    response = StreamingHttpResponse(agent_chat_stream_service.generate(run_id=run.run_id, authenticated_subject=subject, message=payload.message), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response


@csrf_exempt
@require_POST
def agent_chat_stream_extension(request):
    """Extension-only stream endpoint using a random extension session header."""
    if request.content_type != "application/json":
        return api_error(code="UNSUPPORTED_MEDIA_TYPE", message="application/json 요청만 허용됩니다.", status=415)
    extension_id = request.headers.get("X-DGU-Extension-Session", "").strip()
    if len(extension_id) < 16 or len(extension_id) > 128:
        return api_error(code="INVALID_EXTENSION_SESSION", message="확장프로그램 세션을 확인해 주세요.", status=400)
    try:
        payload = ChatRequestSchema.model_validate_json(request.body)
        subject = f"anonymous-extension:{extension_id}"
        run = agent_chat_stream_service.start(authenticated_subject=subject, session_id=str(payload.session_id) if payload.session_id else None)
    except ConversationAccessError:
        return api_error(code="SESSION_FORBIDDEN", message="접근할 수 없는 대화 세션입니다.", status=403)
    except ConversationExpiredError:
        return api_error(code="SESSION_EXPIRED", message="대화 세션이 만료되었습니다. 새 대화를 시작해 주세요.", status=410)
    except (ValidationError, ValueError, json.JSONDecodeError):
        return api_error(code="INVALID_REQUEST", message="message와 선택적 session_id 형식을 확인해 주세요.", status=400)
    response = StreamingHttpResponse(agent_chat_stream_service.generate(run_id=run.run_id, authenticated_subject=subject, message=payload.message), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response


def stream_events(request, run_id):
    try:
        after = max(0, int(request.GET.get("after", "0")))
        events = agent_chat_stream_service.replay(run_id=run_id, authenticated_subject=browser_subject(request), after=after)
    except ValueError:
        return api_error(code="INVALID_REQUEST", message="after는 0 이상의 정수여야 합니다.", status=400)
    except ConversationAccessError:
        return api_error(code="SESSION_FORBIDDEN", message="접근할 수 없는 대화 세션입니다.", status=403)
    except ObjectDoesNotExist:
        return api_error(code="STREAM_NOT_FOUND", message="스트림을 찾을 수 없습니다.", status=404)
    return StreamingHttpResponse((encode_sse(event) for event in events), content_type="text/event-stream")


@require_POST
def cancel_stream(request, run_id):
    try:
        canceled = agent_chat_stream_service.cancel(run_id=run_id, authenticated_subject=browser_subject(request))
    except ConversationAccessError:
        return api_error(code="SESSION_FORBIDDEN", message="접근할 수 없는 대화 세션입니다.", status=403)
    except ObjectDoesNotExist:
        return api_error(code="STREAM_NOT_FOUND", message="스트림을 찾을 수 없습니다.", status=404)
    return JsonResponse({"stream_id": str(run_id), "canceled": canceled}, status=202 if canceled else 409)
