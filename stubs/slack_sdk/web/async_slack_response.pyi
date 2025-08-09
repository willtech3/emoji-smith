from typing import Any

class AsyncSlackResponse(dict[str, Any]):
    data: dict[str, Any]
    def get(self, key: str, default: Any | None = None) -> Any: ...
