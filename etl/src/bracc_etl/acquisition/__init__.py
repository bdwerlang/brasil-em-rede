"""Local acquisition primitives; callers own source-specific pagination and policy."""

from .client import Acquisition, AcquisitionError, Manifest

__all__ = ["Acquisition", "AcquisitionError", "Manifest"]
