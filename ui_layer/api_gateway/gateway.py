from fastapi import FastAPI, Request, HTTPException, WebSocket, Response
from fastapi.middleware.cors import CORSMiddleware
import httpx
import websockets
import asyncio
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

app = FastAPI(title="SnLag Modern API Gateway")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ORCHESTRATION_SERVICE_URL = os.getenv("ORCHESTRATION_SERVICE_URL", "http://localhost:8000")
ORCHESTRATION_WS_URL = os.getenv("ORCHESTRATION_WS_URL", "ws://localhost:8000")

@app.get("/health")
async def health():
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{ORCHESTRATION_SERVICE_URL}/health")
            return response.json()
        except Exception:
            return {"status": "error", "message": "Backend Offline"}

@app.websocket("/ws/translate/{user_id}")
async def websocket_proxy(websocket: WebSocket, user_id: int):
    await websocket.accept()
    try:
        async with websockets.connect(f"{ORCHESTRATION_WS_URL}/ws/translate/{user_id}") as target_ws:
            async def forward_to_backend():
                try:
                    while True:
                        message = await websocket.receive()
                        if "bytes" in message:
                            await target_ws.send(message["bytes"])
                        elif "text" in message:
                            await target_ws.send(message["text"])
                except Exception:
                    pass

            async def forward_to_client():
                try:
                    while True:
                        data = await target_ws.recv()
                        if isinstance(data, bytes):
                            await websocket.send_bytes(data)
                        else:
                            await websocket.send_text(data)
                except Exception:
                    pass

            await asyncio.wait(
                [asyncio.create_task(forward_to_backend()),
                 asyncio.create_task(forward_to_client())],
                return_when=asyncio.FIRST_COMPLETED,
            )
    except Exception as e:
        print(f"Proxy Connection Error: {e}")
    finally:
        try:
            await websocket.close()
        except Exception:
            pass

@app.api_route("/{path_name:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def gateway_proxy(request: Request, path_name: str = ""):
    async with httpx.AsyncClient(timeout=60.0) as client:
        method = request.method
        url = f"{ORCHESTRATION_SERVICE_URL}/{path_name}"
        if request.url.query:
            url += f"?{request.url.query}"

        content = await request.body()
        headers = {k: v for k, v in request.headers.items() if k.lower() not in ["host", "content-length"]}

        try:
            response = await client.request(method, url, content=content, headers=headers)
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers)
            )
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Backend Error: {str(e)}")
