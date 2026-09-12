const DJANGO_API = process.env.DJANGO_API_URL ?? "http://127.0.0.1:8000";

export async function POST(request: Request) {
  try {
    const upstream = await fetch(`${DJANGO_API}/api/chat/stream/extension/`, {
      method: "POST",
      headers: {
        "content-type": "application/json",
        "x-dgu-extension-session": request.headers.get("x-dgu-extension-session") ?? "",
      },
      body: await request.text(),
      cache: "no-store",
    });
    return new Response(upstream.body, {
      status: upstream.status,
      headers: {
        "content-type": upstream.headers.get("content-type") ?? "text/event-stream",
        "cache-control": "no-cache, no-transform",
        "x-accel-buffering": "no",
      },
    });
  } catch {
    return Response.json(
      { error: { message: "Django API에 연결할 수 없습니다." } },
      { status: 502 },
    );
  }
}
