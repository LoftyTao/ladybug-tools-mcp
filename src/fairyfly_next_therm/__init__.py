"""Fairyfly-Next THERM library (AGPL-3.0 derivative).

Derived from ladybug-tools/fairyfly-therm and modified in 2026 to target
upstream fairyfly-core>=0.2.49, add transient/hygrothermal THMZ support, and
invoke the isolated pyHygroThermFEM-Fairyfly solver backend.
"""
from fairyfly.logutil import get_logger

# load all functions that extend fairyfly-core
import fairyfly_next_therm._extend_fairyfly

# use the same logger settings across Fairyfly-Next extensions
# this does NOT mean that the logs will be written to the same file but they will have
# the same formatting, level, etc.
logger = get_logger(name=__name__)
