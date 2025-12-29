"""
Integration backends for logs, metrics, and traces.

Supports multiple backends with automatic fallback.
"""
from .base import LogBackend, MetricBackend, TraceBackend
from .detector import BackendDetector

__all__ = ["LogBackend", "MetricBackend", "TraceBackend", "BackendDetector"]
