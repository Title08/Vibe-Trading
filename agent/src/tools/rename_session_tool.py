"""Rename Session Tool."""

from __future__ import annotations

import json

from src.agent.tools import BaseTool


class RenameSessionTool(BaseTool):
    """Tool to rename the current chat session."""

    name = "rename_session"
    description = "Rename the current chat session to better reflect the ongoing conversation topic. Only use this if the topic has shifted significantly."
    parameters = {
        "type": "object",
        "properties": {
            "new_title": {
                "type": "string",
                "description": "The new title for the chat session (max 5 words).",
            }
        },
        "required": ["new_title"],
    }
    
    def __init__(self, session_id: str | None = None):
        self.session_id = session_id

    def execute(self, new_title: str) -> str:
        if not self.session_id:
            return json.dumps({"status": "error", "error": "No session active"}, ensure_ascii=False)
        
        try:
            from src.session.store import SessionStore
            from src.config.paths import SESSIONS_DIR
            store = SessionStore(SESSIONS_DIR)
            session = store.get_session(self.session_id)
            if not session:
                return json.dumps({"status": "error", "error": "Session not found"}, ensure_ascii=False)
            if session.is_locked:
                return json.dumps({"status": "error", "error": "Session title is locked by the user and cannot be changed"}, ensure_ascii=False)
            
            session.title = new_title
            from datetime import datetime
            session.updated_at = datetime.now().isoformat()
            store.update_session(session)
            
            # Optionally emit event via HTTP or EventBus. But since this is a backend tool
            # doing a DB update, the next refresh will pick it up. If EventBus is needed,
            # it's better injected, but this is sufficient.
            return json.dumps({"status": "success", "message": f"Session renamed to: {new_title}"}, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"status": "error", "error": str(e)}, ensure_ascii=False)
