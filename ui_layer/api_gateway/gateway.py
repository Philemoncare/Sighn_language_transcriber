from fastapi import FastAPI, Request, HTTPException, WebSocket, Response
from fastapi.middleware.cors import CORSMiddleware
import httpx
import websockets
import asyncio
import json
import os

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
            response = await client.get(f"{ORCHESTRATION_SERVICE_URL}/admin/system/health")
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
                        data = await websocket.receive_text()
                        await target_ws.send(data)
                except: pass

            async def forward_to_client():
                try:
                    while True:
                        data = await target_ws.recv()
                        await websocket.send_text(data)
                except: pass

            await asyncio.wait(
                [asyncio.create_task(forward_to_backend()),
                 asyncio.create_task(forward_to_client())],
                return_when=asyncio.FIRST_COMPLETED,
            )
    except Exception as e:
        print(f"Proxy Connection Error: {e}")
    finally:
        try: await websocket.close()
        except: pass

@app.api_route("/{path_name:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def gateway_proxy(request: Request, path_name: str = ""):
    async with httpx.AsyncClient(timeout=60.0) as client:
        method = request.method
        # Reconstruct URL with query parameters
        url = f"{ORCHESTRATION_SERVICE_URL}/{path_name}"
        if request.url.query:
            url += f"?{request.url.query}"

        content = await request.body()
        headers = {k: v for k, v in request.headers.items() if k.lower() not in ["host", "content-length"]}

        try:
            response = await client.request(method, url, content=content, headers=headers)

            # Architecture Fix: Handle different content types (static files, images, json)
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers)
            )
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Backend Error: {str(e)}")
