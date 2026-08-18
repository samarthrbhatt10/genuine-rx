"""
OCR Resolver — Image to Medicine resolution pipeline.
"""
from .pipeline import resolve_prescription_image
from .matcher import match_medicine_text, ResolveResult

__all__ = ["resolve_prescription_image", "match_medicine_text", "ResolveResult"]
