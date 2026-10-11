from fastapi import WebSocket


class OverlayConnectionManager:
    """Tracks live overlay WebSocket connections, keyed by overlay_token."""

    def __init__(self) -> None:
        self._connections: dict[str, list[WebSocket]] = {}

    async def connect(self, overlay_token: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.setdefault(overlay_token, []).append(websocket)

    def disconnect(self, overlay_token: str, websocket: WebSocket) -> None:
        connections = self._connections.get(overlay_token, [])
        if websocket in connections:
            connections.remove(websocket)
        if not connections:
            self._connections.pop(overlay_token, None)

    async def push(self, overlay_token: str, payload: dict) -> int:
        """Send to every open overlay for this token; returns how many received it."""
        delivered = 0
        for websocket in list(self._connections.get(overlay_token, [])):
            try:
                await websocket.send_json(payload)
                delivered += 1
            except Exception:
                # A half-closed OBS socket must not fail the webhook (sociabuzz would retry).
                self.disconnect(overlay_token, websocket)
        return delivered


manager = OverlayConnectionManager()
