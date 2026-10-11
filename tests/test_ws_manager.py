import asyncio

from app.ws_manager import OverlayConnectionManager


class _DeadSocket:
    async def send_json(self, payload):
        raise RuntimeError("socket closed")


class _LiveSocket:
    def __init__(self):
        self.received = []

    async def send_json(self, payload):
        self.received.append(payload)


def test_push_drops_dead_sockets_and_still_reaches_live_ones():
    manager = OverlayConnectionManager()
    dead, live = _DeadSocket(), _LiveSocket()
    manager._connections["tok"] = [dead, live]

    asyncio.run(manager.push("tok", {"html": "hi"}))

    assert live.received == [{"html": "hi"}]
    assert manager._connections["tok"] == [live]
