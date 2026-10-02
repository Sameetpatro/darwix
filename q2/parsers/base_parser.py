from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Union
from q2.models.raw_document import RawDocument


class BaseParser(ABC):
    """Abstract interface for all document parsers."""

    @abstractmethod
    def can_parse(self, file_path: Union[str, Path]) -> bool:
        """Determines if this parser handles the given file type or content."""
        pass

    @abstractmethod
    def parse(self, file_path: Union[str, Path]) -> List[RawDocument]:
        """Extracts text, headings, sections, and tables into structured RawDocument instances."""
        pass
