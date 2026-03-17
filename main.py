from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from contextlib import asynccontextmanager
import asyncio
import json
import logging

from src.config import config
from src.models import ChatCompletionRequest, ChatCompletionResponse, ModelList, Model
from src.proxy import router
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
        await router.start_all()
    
    yield
    
    await router.close_all()


app = FastAPI(
    title="Multi-Provider AI Chat API",
    description="OpenAI-compatible API for DeepSeek and Gemini web",
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
        data=[
            Model(id="deepseek-chat", object="model", created=1700000000, owned_by="deepseek"),
            Model(id="gemini-2.0-flash", object="model", created=1700000000, owned_by="google"),
            Model(id="gemini-2.0-flash-lite", object="model", created=1700000000, owned_by="google"),
            Model(id="gemini-1.5-pro", object="model", created=1700000000, owned_by="google"),
            Model(id="gemini-1.5-flash", object="model", created=1700000000, owned_by="google"),
        ]
    )


@app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(request: ChatCompletionRequest):
    """OpenAI-compatible chat completions endpoint."""
    # Get provider based on model
    try:
        provider = router.get_provider_by_model(request.model)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    if request.stream:
        return StreamingResponse(stream_chat(request, provider), media_type="text/event-stream")
    
    try:
        response = await provider.chat(
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
    except NotImplementedError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def stream_chat(request: ChatCompletionRequest, provider):
    """Stream chat responses."""
    try:
        chunk_builder = ChunkBuilder(model=request.model)
        
        async for chunk_content in provider.chat_streaming(
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
    except NotImplementedError as e:
        error = {"error": {"message": str(e), "type": "not_implemented"}}
        yield f"data: {json.dumps(error)}\n\n"
    except Exception as e:
        error = {"error": {"message": str(e), "type": "error"}}
        yield f"data: {json.dumps(error)}\n\n"


@app.get("/session/status")
async def session_status():
    """Get session status."""
    return {
        "deepseek": session_manager.get_status(),
        "gemini": {"available": True}
    }


@app.post("/session/refresh")
async def refresh_session(provider: str = "deepseek"):
    """Force refresh session."""
    if provider == "deepseek":
        success = await session_manager.refresh(config.deepseek.base_url)
        if success:
            return {"status": "success", "message": "DeepSeek session refreshed"}
        raise HTTPException(status_code=401, detail="DeepSeek session refresh failed")
    else:
        raise HTTPException(status_code=400, detail=f"Session refresh for {provider} not supported")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.server.host, port=config.server.port)
