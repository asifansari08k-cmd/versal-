from fastapi import FastAPI, Request
from fastapi.responses import Response
import httpx
import json
import time

app = FastAPI()

BACKEND_URL_FILE = (
    "https://raw.githubusercontent.com/"
    "themagmalord333-oss/MAGMA-API/main/backend-url.json"
)


async def get_backend_url():
    url = f"{BACKEND_URL_FILE}?t={time.time_ns()}"

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(
            url,
            headers={
                "Cache-Control": "no-cache",
                "User-Agent": "MAGMA-Vercel-Proxy"
            }
        )

        response.raise_for_status()

        data = response.json()

    backend = data.get("url", "").strip().rstrip("/")

    if not backend.startswith("https://"):
        raise ValueError("Invalid backend URL")

    return backend


@app.api_route(
    "/{path:path}",
    methods=[
        "GET",
        "POST",
        "PUT",
        "PATCH",
        "DELETE",
        "OPTIONS",
        "HEAD"
    ]
)
async def proxy(request: Request, path: str):

    try:
        backend = await get_backend_url()

        target_url = backend + "/" + path

        if request.url.query:
            target_url += "?" + str(request.url.query)

        body = await request.body()

        headers = dict(request.headers)

        headers.pop("host", None)
        headers.pop("content-length", None)

        async with httpx.AsyncClient(
            timeout=50,
            follow_redirects=True
        ) as client:

            response = await client.request(
                method=request.method,
                url=target_url,
                content=body,
                headers=headers
            )

        excluded_headers = {
            "content-length",
            "transfer-encoding",
            "connection",
            "content-encoding"
        }

        response_headers = {
            key: value
            for key, value in response.headers.items()
            if key.lower() not in excluded_headers
        }

        response_headers["Access-Control-Allow-Origin"] = "*"

        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=response_headers,
            media_type=response.headers.get("content-type")
        )

    except Exception as e:

        return {
            "status": False,
            "error": "Backend unavailable",
            "message": str(e)
        }