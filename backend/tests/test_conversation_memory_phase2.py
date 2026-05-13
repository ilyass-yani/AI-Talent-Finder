from __future__ import annotations

from ai_module.chatbot.conversation_memory import ConversationMemory


class FakeRedisClient:
    def __init__(self):
        self.lists = {}
        self.hashes = {}
        self.expirations = {}

    def ping(self):
        return True

    def rpush(self, key, value):
        self.lists.setdefault(key, []).append(value)

    def ltrim(self, key, start, end):
        items = self.lists.get(key, [])
        self.lists[key] = items[start : end + 1 if end != -1 else None]

    def expire(self, key, ttl):
        self.expirations[key] = ttl

    def hset(self, key, mapping):
        self.hashes.setdefault(key, {}).update(mapping)

    def hget(self, key, field):
        return self.hashes.get(key, {}).get(field)

    def delete(self, *keys):
        for key in keys:
            self.lists.pop(key, None)
            self.hashes.pop(key, None)

    def lrange(self, key, start, end):
        items = self.lists.get(key, [])
        return items[start : end + 1 if end != -1 else None]

    def keys(self, pattern):
        prefix = pattern[:-1] if pattern.endswith("*") else pattern
        return [key for key in self.lists.keys() if key.startswith(prefix)]


def test_conversation_memory_keeps_sessions_isolated():
    client = FakeRedisClient()
    memory = ConversationMemory(client=client, ttl_seconds=120)

    memory.add_message("session-a", "user", "bonjour")
    memory.add_message("session-a", "assistant", "salut")
    memory.add_message("session-b", "user", "hola")
    memory.set_current_criteria("session-a", 12)
    memory.set_current_criteria("session-b", 34)

    assert memory.available() is True
    assert [item["content"] for item in memory.get_history("session-a")] == ["bonjour", "salut"]
    assert [item["content"] for item in memory.get_history("session-b")] == ["hola"]
    assert memory.get_current_criteria("session-a") == 12
    assert memory.get_current_criteria("session-b") == 34
    assert set(memory.list_sessions()) == {"session-a", "session-b"}


def test_conversation_memory_clears_one_session_only():
    client = FakeRedisClient()
    memory = ConversationMemory(client=client)

    memory.add_message("session-a", "user", "bonjour")
    memory.add_message("session-b", "user", "hola")
    memory.clear("session-a")

    assert memory.get_history("session-a") == []
    assert memory.get_history("session-b")[0]["content"] == "hola"