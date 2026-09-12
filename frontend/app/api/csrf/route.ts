const DJANGO_API = process.env.DJANGO_API_URL ?? "http://127.0.0.1:8000";

export async function GET() {
  try {
    const upstream = await fetch(`${DJANGO_API}/api/csrf/`, {
      cache: "no-store",
    });
    const headers = new Headers({
      "content-type": upstream.headers.get("content-type") ?? "application/json",
      "cache-control": "no-store",
    });
    const cookie = upstream.headers.get("set-cookie");
    if (cookie) headers.set("set-cookie", cookie);
    return new Response(await upstream.text(), {
      status: upstream.status,
      headers,
    });
  } catch {
    return Response.json(
      { error: { message: "Django API에 연결할 수 없습니다." } },
      { status: 502 },
    );
  }
}
