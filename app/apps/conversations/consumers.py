import json
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from .chat_turn import process_chat_turn


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        session = self.scope.get("session")
        if not session:
            await self.close(code=4001)
            return
        uid = session.get("user_account_id")
        if not uid:
            await self.close(code=4001)
            return
        qs = parse_qs(self.scope.get("query_string", b"").decode())
        tid = qs.get("tenant_id", [None])[0]
        if not tid:
            await self.close(code=4002)
            return
        try:
            self.tenant_id = int(tid)
        except (TypeError, ValueError):
            await self.close(code=4002)
            return
        self.user_account_id = uid
        await self.accept()

    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            return
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            await self.send(
                text_data=json.dumps({"type": "error", "code": "invalid_json"})
            )
            return
        action = data.get("action") or "message"
        if action != "message":
            await self.send(
                text_data=json.dumps({"type": "error", "code": "unknown_action"})
            )
            return
        content = data.get("content")
        conv_id = data.get("conversation_id")
        kb_id = data.get("knowledge_base_id")
        if conv_id is not None:
            try:
                conv_id = int(conv_id)
            except (TypeError, ValueError):
                await self.send(
                    text_data=json.dumps({"type": "error", "code": "invalid_conversation_id"})
                )
                return
        if kb_id is not None:
            try:
                kb_id = int(kb_id)
            except (TypeError, ValueError):
                await self.send(
                    text_data=json.dumps({"type": "error", "code": "invalid_knowledge_base_id"})
                )
                return
        run = database_sync_to_async(process_chat_turn)
        result = await run(
            self.tenant_id,
            self.user_account_id,
            conv_id,
            kb_id,
            content,
        )
        if result.get("error"):
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "error",
                        "code": result.get("error"),
                        "detail": result.get("detail"),
                    }
                )
            )
            return
        await self.send(
            text_data=json.dumps(
                {
                    "type": "ready",
                    "conversation_id": result["conversation_id"],
                }
            )
        )
        assistant_text = result.get("assistant_text") or ""
        step = 48
        for i in range(0, len(assistant_text), step):
            await self.send(
                text_data=json.dumps(
                    {"type": "delta", "text": assistant_text[i : i + step]}
                )
            )
        await self.send(
            text_data=json.dumps(
                {
                    "type": "done",
                    "conversation_id": result["conversation_id"],
                    "user_message_id": result["user_message_id"],
                    "assistant_message_id": result["assistant_message_id"],
                }
            )
        )
