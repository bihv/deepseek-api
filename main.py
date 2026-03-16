from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from contextlib import asynccontextmanager
import asyncio
import json

from src.config import config
from src.models import ChatCompletionRequest, ChatCompletionResponse, ModelList, Model
from src.proxy import proxy
from src.session import session_manager
from src.mapper import map_to_openai_response, generate_chunk, ChunkBuilder


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    if config.browser.use_browser:
        await proxy.start()
    
    yield
    
    if proxy._browser:
        await proxy.close()


app = FastAPI(
    title="DeepSeek API Proxy",
    description="OpenAI-compatible API for DeepSeek web",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    status = session_manager.get_status()
    return {
        "status": "healthy" if status["active"] else "degraded",
        "session": status
    }


@app.get("/v1/models")
async def list_models():
    """List available models."""
    return ModelList(
        data=[Model(id="deepseek-chat", object="model", created=1700000000, owned_by="deepseek")]
    )


@app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(request: ChatCompletionRequest):
    """OpenAI-compatible chat completions endpoint."""
    if request.stream:
        return StreamingResponse(stream_chat(request), media_type="text/event-stream")
    
    try:
        content = await proxy.chat(
            messages=request.messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            stream=False,
            conversation_id=request.conversation_id,
            create_new=request.create_new
        )
        return map_to_openai_response(
            content=content,
            model=request.model,
            prompt_tokens=10,
            completion_tokens=len(content.split())
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def stream_chat(request: ChatCompletionRequest):
    """Stream chat responses."""
    try:
        chunk_builder = ChunkBuilder(model=request.model)
        
        async for chunk_content in proxy.chat_streaming(
            messages=request.messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            conversation_id=request.conversation_id,
            create_new=request.create_new
        ):
            chunk = chunk_builder.build(content=chunk_content)
            yield f"data: {chunk.model_dump_json()}\n\n"
        
        final_chunk = chunk_builder.build(content="", finish_reason="stop")
        yield f"data: {final_chunk.model_dump_json()}\n\n"
        yield "data: [DONE]\n\n"
    except Exception as e:
        error = {"error": {"message": str(e), "type": "error"}}
        yield f"data: {json.dumps(error)}\n\n"


@app.get("/session/status")
async def session_status():
    """Get session status."""
    return session_manager.get_status()


@app.post("/session/refresh")
async def refresh_session():
    """Force refresh session."""
    success = await session_manager.refresh(config.deepseek.base_url)
    if success:
        return {"status": "success", "message": "Session refreshed"}
    raise HTTPException(status_code=401, detail="Session refresh failed")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.server.host, port=config.server.port)
