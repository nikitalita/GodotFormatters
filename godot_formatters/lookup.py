from godot_formatters.godot_types import (SYNTHETIC_PROVIDERS, SUMMARY_PROVIDERS)
from typing import Optional
import re

def get_synthetic_provider_for_type(type_name: str) -> Optional[type]:
    for pattern, provider in SYNTHETIC_PROVIDERS.items():
        if re.match(pattern, type_name):
            return provider
    return None

def get_summary_provider_for_type(type_name: str) -> Optional[object]:
    for pattern, provider in SUMMARY_PROVIDERS.items():
        if re.match(pattern, type_name):
            return provider
    for pattern, synth_class in SYNTHETIC_PROVIDERS.items():
        if re.match(pattern, type_name):
            def wrapper(valobj, internal_dict, _options = None):
                synth = synth_class(valobj, internal_dict, 1)
                summary = synth.get_summary()
                return summary
            return wrapper
    return None
