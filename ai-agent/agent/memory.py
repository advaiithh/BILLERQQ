"""
Conversation memory — tracks session context for follow-up questions.

Stores:
    - Last customer referenced (for pronoun resolution: "his", "her", "their")
    - Last intent (for context)
    - Conversation history (last 10 turns)
    - Auto-expiry after 30 minutes of inactivity
"""

import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Session expiry: 30 minutes
SESSION_EXPIRY_SECONDS = 30 * 60

# Max conversation history turns to keep
MAX_HISTORY_TURNS = 10


class ConversationMemory:
    """Memory for a single conversation session."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.last_customer_id: Optional[int] = None
        self.last_customer_name: Optional[str] = None
        self.last_intent: Optional[str] = None
        self.conversation_history: list[dict] = []
        self.last_activity: float = time.time()

    def is_expired(self) -> bool:
        """Check if this session has expired due to inactivity."""
        return (time.time() - self.last_activity) > SESSION_EXPIRY_SECONDS

    def touch(self):
        """Update last activity timestamp."""
        self.last_activity = time.time()

    def update_customer(self, customer_id: int, customer_name: str):
        """Store the last referenced customer for follow-up resolution."""
        self.last_customer_id = customer_id
        self.last_customer_name = customer_name
        logger.debug(
            "Session %s: stored customer %s (ID %d)",
            self.session_id, customer_name, customer_id,
        )

    def update_intent(self, intent: str):
        """Store the last intent."""
        self.last_intent = intent

    def add_turn(self, user_message: str, bot_response: str):
        """Add a conversation turn to history.

        Keeps only the last MAX_HISTORY_TURNS turns to limit LLM context.
        """
        self.conversation_history.append({
            "user": user_message,
            "assistant": bot_response,
        })
        # Trim to max turns
        if len(self.conversation_history) > MAX_HISTORY_TURNS:
            self.conversation_history = self.conversation_history[-MAX_HISTORY_TURNS:]

    def get_context(self) -> dict:
        """Get current session context for the planner.

        Returns:
            Dict with last customer info and recent conversation history.
        """
        return {
            "last_customer_id": self.last_customer_id,
            "last_customer_name": self.last_customer_name,
            "last_intent": self.last_intent,
            "history": self.conversation_history[-5:],  # Last 5 turns for LLM
        }

    def resolve_pronoun(self, text: str) -> str:
        """Replace pronouns with the last known customer name.

        Handles: his, her, their, them, this customer, that customer, same customer

        Args:
            text: User input text.

        Returns:
            Text with pronouns replaced, or original text if no customer in memory.
        """
        if not self.last_customer_name:
            return text

        import re

        # Patterns that refer to the previous customer
        pronoun_patterns = [
            r"\bhis\b",
            r"\bher\b",
            r"\btheir\b",
            r"\bthem\b",
            r"\bthis customer'?s?\b",
            r"\bthat customer'?s?\b",
            r"\bsame customer'?s?\b",
            r"\bthe customer'?s?\b",
        ]

        modified = text
        for pattern in pronoun_patterns:
            if re.search(pattern, modified, re.IGNORECASE):
                modified = re.sub(
                    pattern,
                    f"{self.last_customer_name}'s",
                    modified,
                    flags=re.IGNORECASE,
                )
                logger.debug(
                    "Pronoun resolved: '%s' → '%s'",
                    text, modified,
                )
                return modified

        return text


class MemoryManager:
    """Manages conversation memories across all sessions."""

    def __init__(self):
        self._sessions: dict[str, ConversationMemory] = {}

    def get_session(self, session_id: str) -> ConversationMemory:
        """Get or create a conversation memory for a session.

        Auto-cleans expired sessions.

        Args:
            session_id: Unique session identifier.

        Returns:
            The ConversationMemory for this session.
        """
        # Clean expired sessions periodically
        self._cleanup_expired()

        if session_id not in self._sessions:
            logger.info("Creating new session: %s", session_id)
            self._sessions[session_id] = ConversationMemory(session_id)

        session = self._sessions[session_id]

        # Check if the existing session expired
        if session.is_expired():
            logger.info("Session %s expired, creating new one", session_id)
            self._sessions[session_id] = ConversationMemory(session_id)
            session = self._sessions[session_id]

        session.touch()
        return session

    def _cleanup_expired(self):
        """Remove expired sessions to free memory."""
        expired = [
            sid for sid, mem in self._sessions.items()
            if mem.is_expired()
        ]
        for sid in expired:
            logger.debug("Cleaning up expired session: %s", sid)
            del self._sessions[sid]

    @property
    def active_sessions(self) -> int:
        """Count of active (non-expired) sessions."""
        self._cleanup_expired()
        return len(self._sessions)


# Singleton
memory_manager = MemoryManager()
