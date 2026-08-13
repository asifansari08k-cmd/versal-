from fastapi import FastAPI, Request
from fastapi.responses import Response
import httpx
import time

app = FastAPI(
    title="MAGMA API Proxy",
    version="1.0.0"
)

BACKEND_URL_FILE = (
    "https://raw.githubusercontent.com/"
    "themagmalord333-oss/MAGMA-API/main/backend-url.json"
)


async def get_backend_url():
    cache_buster = time.time_ns()

    url = f"{BACKEND_URL_FILE}?t={cache_buster}"

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(
            url,
            headers={
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
                "User-Agent": "MAGMA-Vercel-Proxy"
            }
        )

        response.raise_for_status()

        data = response.json()

    backend_url = str(data.get("url", "")).strip().rstrip("/")

    if not backend_url:
        raise ValueError("Backend URL is empty")

    if not backend_url.startswith("https://"):
        raise ValueError("Backend URL must use HTTPS")

    return backend_url


@app.get("/")
async def home():
    return {
        "status": True,
        "service": "MAGMA API Proxy",
        "message": "Proxy is online"
    }


@app.get("/health")
async def health():
    return {
        "status": True,
        "service": "MAGMA API Proxy",
        "message": "Healthy"
    }


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
        backend_url = await get_backend_url()

        target_url = f"{backend_url}/{path}"

        if request.url.query:
            target_url = f"{target_url}?{request.url.query}"

        body = await request.body()

        headers = dict(request.headers)

        headers.pop("host", None)
        headers.pop("content-length", None)
        headers.pop("connection", None)

        async with httpx.AsyncClient(
            timeout=50,
            follow_redirects=True
        ) as client:

            backend_response = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body
            )

        excluded_headers = {
            "content-length",
            "transfer-encoding",
            "connection",
            "content-encoding"
        }

        response_headers = {
            key: value
            for key, value in backend_response.headers.items()
            if key.lower() not in excluded_headers
        }

        response_headers["Access-Control-Allow-Origin"] = "*"
        response_headers["Access-Control-Allow-Methods"] = (
            "GET,POST,PUT,PATCH,DELETE,OPTIONS,HEAD"
        )
        response_headers["Access-Control-Allow-Headers"] = "*"

        return Response(
            content=backend_response.content,
            status_code=backend_response.status_code,
            headers=response_headers
        )

    except httpx.TimeoutException:
        return {
            "status": False,
            "error": "Backend timeout",
            "message": "The MAGMA API backend did not respond in time."
        }

    except httpx.HTTPError as error:
        return {
            "status": False,
            "error": "Backend connection failed",
            "message": str(error)
        }

    except Exception as error:
        return {
            "status": False,
            "error": "Proxy error",
            "message": str(error)
        }