from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseAgent(ABC):
    """
    """
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    async def process(self, task: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        pass
