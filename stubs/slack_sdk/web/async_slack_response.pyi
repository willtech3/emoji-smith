from typing import Any, Dict, Optional

class AsyncSlackResponse(dict[str, Any]):
    data: Dict[str, Any]
    def get(self, key: str, default: Optional[Any] = None) -> Any: ...
