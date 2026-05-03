#!/usr/bin/env python3
"""
Memory Manager for Multi-Agent Systems
Manages session-based memory for multi-agent workflows
"""

import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
import threading


class MemoryManager:
    """Manages session-based memory for multi-agent systems."""

    def __init__(self, max_sessions=1000, session_timeout=3600):
        self.sessions = {}
        self.max_sessions = max_sessions
        self.session_timeout = session_timeout  # seconds
        self.lock = threading.Lock()

    def create_session(self, user_id: str = None, session_name: str = None) -> str:
        """Create a new session and return its ID."""
        with self.lock:
            session_id = f"{user_id or 'anonymous'}_{uuid.uuid4().hex[:8]}_{int(datetime.now().timestamp())}"

            self.sessions[session_id] = {
                "session_id": session_id,
                "user_id": user_id or "anonymous",
                "session_name": session_name
                or f"Session_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "created_at": datetime.now(),
                "last_accessed": datetime.now(),
                "context": {
                    "user_query": "",
                    "results": {},
                    "history": [],
                    "current_phase": "initializing",
                },
                "status": "active",
            }

            self._cleanup_expired_sessions()

            return session_id

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve session data by ID, updating last-accessed timestamp."""
        with self.lock:
            if session_id in self.sessions:
                self.sessions[session_id]["last_accessed"] = datetime.now()
                return self.sessions[session_id]
            return None

    def update_session_context(self, session_id: str, updates: Dict[str, Any]) -> bool:
        """Update the context dictionary for an existing session."""
        with self.lock:
            if session_id in self.sessions:
                session = self.sessions[session_id]
                session["context"].update(updates)
                session["last_accessed"] = datetime.now()
                return True
            return False

    def add_agent_result(
        self, session_id: str, agent_name: str, result: Any, phase: str = None
    ) -> bool:
        """Record an agent execution result in the session history."""
        with self.lock:
            if session_id in self.sessions:
                session = self.sessions[session_id]

                # Append to execution history
                history_entry = {
                    "agent": agent_name,
                    "result": result,
                    "timestamp": datetime.now().isoformat(),
                    "phase": phase or session["context"]["current_phase"],
                }
                session["context"]["history"].append(history_entry)

                # Update latest result for this agent
                session["context"]["results"][agent_name] = result
                session["last_accessed"] = datetime.now()

                return True
            return False

    def get_context_for_agent(self, session_id: str, agent_name: str) -> str:
        """Build a JSON context string suitable for passing to an agent."""
        session = self.get_session(session_id)
        if not session:
            return "{}"

        context = session["context"]

        # Build agent-facing context with recent history
        agent_context = {
            "session_id": session_id,
            "user_id": session["user_id"],
            "session_name": session["session_name"],
            "user_query": context["user_query"],
            "current_phase": context["current_phase"],
            "previous_results": context["results"],
            "execution_history": context["history"][-5:],
            "timestamp": datetime.now().isoformat(),
        }

        return json.dumps(agent_context, indent=2)

    def set_current_phase(self, session_id: str, phase: str) -> bool:
        """Set the current execution phase for a session."""
        return self.update_session_context(session_id, {"current_phase": phase})

    def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """Return a summary dictionary for the given session."""
        session = self.get_session(session_id)
        if not session:
            return {}

        return {
            "session_id": session_id,
            "user_id": session["user_id"],
            "session_name": session["session_name"],
            "created_at": session["created_at"].isoformat(),
            "last_accessed": session["last_accessed"].isoformat(),
            "current_phase": session["context"]["current_phase"],
            "agents_executed": list(session["context"]["results"].keys()),
            "history_count": len(session["context"]["history"]),
            "status": session["status"],
        }

    def list_user_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        """List all sessions for a given user, sorted by last access time."""
        with self.lock:
            user_sessions = []
            for session_id, session in self.sessions.items():
                if session["user_id"] == user_id:
                    user_sessions.append(self.get_session_summary(session_id))
            return sorted(user_sessions, key=lambda x: x["last_accessed"], reverse=True)

    def _cleanup_expired_sessions(self):
        """Remove sessions that have exceeded the timeout."""
        current_time = datetime.now()
        expired_sessions = []

        for session_id, session in self.sessions.items():
            if (current_time - session["last_accessed"]).seconds > self.session_timeout:
                expired_sessions.append(session_id)

        for session_id in expired_sessions:
            del self.sessions[session_id]

    def close_session(self, session_id: str) -> bool:
        """Mark a session as closed."""
        with self.lock:
            if session_id in self.sessions:
                self.sessions[session_id]["status"] = "closed"
                return True
            return False


# Global memory manager instance
memory_manager = MemoryManager()
