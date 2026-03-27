# -*- coding: UTF-8 -*-
"""WebUI modules.

This module provides lazy imports to avoid importing torch/numpy
when the WebUI is first loaded.
"""

# Lazy imports - import only when needed
# from .utils import *
# from .generation import get_generator, ImageGenerator
# from .tracing import get_tracer, ModelTracer

__all__ = ["utils", "generation", "tracing"]
