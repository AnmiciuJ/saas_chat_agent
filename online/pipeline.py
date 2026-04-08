"""
在线对话编排主流程。

接收用户问题，协调意图识别、知识检索、重排序、记忆组装与大模型推理，
以流式方式返回生成片段。
"""

from typing import AsyncGenerator

from online.intent import rewrite_query
from online.retrieval import hybrid_retrieve
from online.rerank import rerank_candidates
from online.memory import assemble_context
from online.llm_client import stream_completion


async def run_chat_pipeline(
    tenant_id: int,
    conversation_id: int,
    user_message: str,
    knowledge_base_id: int | None = None,
) -> AsyncGenerator[str, None]:
    """
    执行完整的在线对话链路，返回异步生成器逐片段产出回复文本。
    """
    rewritten = await rewrite_query(user_message)

    candidates = await hybrid_retrieve(
        tenant_id=tenant_id,
        knowledge_base_id=knowledge_base_id,
        query=rewritten,
    )

    ranked = await rerank_candidates(query=rewritten, candidates=candidates)

    context_pack = await assemble_context(
        tenant_id=tenant_id,
        conversation_id=conversation_id,
        retrieval_results=ranked,
    )

    async for chunk in stream_completion(
        context=context_pack,
        user_message=user_message,
    ):
        yield chunk
