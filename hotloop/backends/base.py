import abc
from typing import Optional, Tuple

class BaseBackend(abc.ABC):
    """Abstract base class for Hotloop compilation backends."""

    @abc.abstractmethod
    def build(self, file_path: str, engine: str = "auto") -> Tuple[bool, str, Optional[str]]:
        """
        Builds the specified Python source file to a native shared library (.so).
        Returns (success, message, output_so_path).
        """
        pass
