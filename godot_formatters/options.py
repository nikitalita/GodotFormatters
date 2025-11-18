# ********************************************************
# OPTIONS
# ********************************************************

import shlex


class GodotFormatterOptions:
    PRINT_VERBOSE = False
    PRINT_TRACE = False
    SUMMARY_STRING_MAX_LENGTH = 100
    MAX_AMOUNT_OF_CHILDREN_IN_SUMMARY = 6
    NAMED_COLOR_ANNOTATION = True
    MAP_KEY_VAL_STYLE: bool = True
    SANITIZE_STRING_SUMMARY = True
    MIDEBUGGER_COMPAT = False
    FILTER = ""  #'"' + '" , "'.join([".*update.*", ".*__init__.*"]) + '"'


def get_filter():
    if not Opts.FILTER:
        return []
    thing = [s.strip('"') for s in shlex.split(Opts.FILTER) if s != ","]
    return thing


HELP_STRING_MAP = {
    "PRINT_VERBOSE": "Print verbose output",
    "PRINT_TRACE": "Print trace output",
    "SUMMARY_STRING_MAX_LENGTH": "Maximum length of a summary string",
    "MAX_AMOUNT_OF_CHILDREN_IN_SUMMARY": "Maximum amount of children to display in a summary string",
    "NAMED_COLOR_ANNOTATION": "Annotate color summaries with their named color if applicable",
    "MAP_KEY_VAL_STYLE": 'Display children in Map-like templates in a key-value list style (e.g. ["key"] = "value"). If false, will display children in an indexed-list style (e.g. [0] = ["key"]: "value")',
    "SANITIZE_STRING_SUMMARY": "Sanitize string summaries to escape all formatting characters and quotes",
    "MIDEBUGGER_COMPAT": "Force compatibility settings with the MIDebugger interface (i.e. the official MS C++ vscode debugger `cppdbg`). This is not necessary if using a native LLDB interface (e.g. `lldp-dap` debugger extension for vscode)",
    "FILTER": "List of regex filters to apply to trace output",
}


# Compatibility settings
def force_compat(force_mi_compat: bool):
    if force_mi_compat:
        # MIDebugger refuses to display map children when this is True, forced to False
        Opts.MAP_KEY_VAL_STYLE = False
        # MIDebugger chokes and dies when there are mixed escaped and non-escaped quotes in a string summary, so this is forced to be True
        Opts.SANITIZE_STRING_SUMMARY = True


Opts: GodotFormatterOptions = GodotFormatterOptions()

# Summary string formats
NULL_SUMMARY = "<null>"
NIL_SUMMARY = "<nil>"  # Variant nil
EMPTY_SUMMARY = "<empty>"  # Empty string, nodepath, etc.
INVALID_SUMMARY = "<invalid>"  # Invalid pointer, uninitialized objects, etc.
ERROR_SUMMARY = "<!ERROR!>"  # Error summary
LIST_FORMAT = "{type_no_template}[{size}]{{{children}}}"

# Synthetic list-like configs; because linked-lists need to traverse the list to get a specific element, we need to cache the members to be performant.
NO_CACHE_MEMBERS = False
CACHE_MIN = 500
CACHE_FETCH_MAX = 5000

STRINGS_STILL_32_BIT = True  # if true, strings are still 32-bit
MAX_DEPTH = 3
