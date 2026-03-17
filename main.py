from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from contextlib import asynccontextmanager
import asyncio
import json
import logging

from src.config import config
from src.models import ChatCompletionRequest, ChatCompletionResponse, ModelList, Model
from src.proxy import proxy
from src.session import session_manager
from src.mapper import map_to_openai_response, generate_chunk, ChunkBuilder

# Configure logging - both console and file
import os
from logging.handlers import RotatingFileHandler

# Create logs directory if not exists
os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler('logs/app.log', maxBytes=10*1024*1024, backupCount=5),  # 10MB, keep 5 files
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


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
        response = await proxy.chat(
            messages=request.messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            stream=False,
            conversation_id=request.conversation_id,
            create_new=request.create_new,
            thinking=request.thinking
        )
        
        # Handle both old string response and new dict response
        content = response.get("content", response) if isinstance(response, dict) else response
        reasoning_content = response.get("reasoning_content") if isinstance(response, dict) else None
        thinking_time = response.get("thinking_time") if isinstance(response, dict) else None
        conversation_id = response.get("conversation_id") if isinstance(response, dict) else None
        
        return map_to_openai_response(
            content=content,
            model=request.model,
            reasoning_content=reasoning_content,
            thinking_time=thinking_time,
            messages=request.messages,
            conversation_id=conversation_id
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
            create_new=request.create_new,
            thinking=request.thinking
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
