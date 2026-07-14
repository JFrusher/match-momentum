from .base import BaseDataSource
from .custom_json import CustomJSONSource

SOURCES = {
    "custom_json": CustomJSONSource,
}

__all__ = ["BaseDataSource", "SOURCES"]
