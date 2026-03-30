# noinspection PyUnresolvedReferences
from importlib import reload


import godot_formatters.options

godot_formatters.options = reload(godot_formatters.options)
from godot_formatters.options import *


import godot_formatters.utils

godot_formatters.utils = reload(godot_formatters.utils)
from godot_formatters.utils import *


import godot_formatters.godot_providers

# we have to force reload the dependent modules to make lldb update the providers if we're re-loading the module
godot_formatters.godot_providers = reload(godot_formatters.godot_providers)
from godot_formatters.godot_providers import *

import godot_formatters.godot_types

godot_formatters.godot_types = reload(godot_formatters.godot_types)
from godot_formatters.godot_types import *

import godot_formatters.lookup
godot_formatters.lookup = reload(godot_formatters.lookup)
from godot_formatters.lookup import *


godot_formatters.godot_providers.get_synthetic_provider_for_type = get_synthetic_provider_for_type
godot_formatters.godot_providers.get_summary_provider_for_type = get_summary_provider_for_type


# GDEXT STUFF
import godot_formatters.godot_gdext_providers
godot_formatters.godot_gdext_providers = reload(godot_formatters.godot_gdext_providers)
from godot_formatters.godot_gdext_providers import *

import godot_formatters.godot_gdext_types
godot_formatters.godot_gdext_types = reload(godot_formatters.godot_gdext_types)
from godot_formatters.godot_gdext_types import *

godot_formatters.godot_gdext_providers.get_godot_synthetic_provider_for_type = get_synthetic_provider_for_type
godot_formatters.godot_gdext_providers.get_godot_summary_provider_for_type = get_summary_provider_for_type


from lldb import SBDebugger, SBTypeCategory
from lldb import (SBCommandReturnObject, SBExecutionContext, SBTypeCategory, eFormatBytes, eFormatCString, eFormatUnicode32, eNoDynamicValues, eDynamicDontRunTarget, eDynamicCanRunTarget, eBasicTypeInvalid, eBasicTypeVoid, eBasicTypeChar, 
                  eBasicTypeSignedChar, eBasicTypeUnsignedChar, eBasicTypeWChar, eBasicTypeSignedWChar, eBasicTypeUnsignedWChar, eBasicTypeChar16, eBasicTypeChar32, 
                  eBasicTypeChar8, eBasicTypeShort, eBasicTypeUnsignedShort, eBasicTypeInt, eBasicTypeUnsignedInt, eBasicTypeLong, eBasicTypeUnsignedLong, eBasicTypeLongLong, 
                  eBasicTypeUnsignedLongLong, eBasicTypeInt128, eBasicTypeUnsignedInt128, eBasicTypeBool, eBasicTypeHalf, eBasicTypeFloat, eBasicTypeDouble, eBasicTypeLongDouble, 
                  eBasicTypeFloatComplex, eBasicTypeDoubleComplex, eBasicTypeLongDoubleComplex, eBasicTypeObjCID, eBasicTypeObjCClass, eBasicTypeObjCSel, eBasicTypeNullPtr, eReturnStatusSuccessFinishNoResult, eReturnStatusSuccessFinishResult, 
                  eTypeClassClass, eTypeClassEnumeration, eTypeClassPointer, eTypeOptionCascade)
from lldb import ( SBValue, SBAddress, SBData, SBType, SBTypeEnumMember, SBTypeEnumMemberList, SBSyntheticValueProvider, SBError, SBTarget, SBDebugger, SBTypeSummary, SBTypeSynthetic, SBTypeNameSpecifier)


FORMATTER_NAME = "godot_formatter"
CONTAINER_NAME = "_" + FORMATTER_NAME

# TODO: Collate globals better
def clear_globals():
    try:
        GodotSynthProvider.synth_by_id.clear()
        GodotSynthProvider.next_id = 0
        global hex_color_to_name
        hex_color_to_name.clear()
        global constructed_the_table
        constructed_the_table = False
    except Exception as e:
        print("Error clearing globals: " + str(e))


def printAllCategories(debugger: SBDebugger):
    count = debugger.GetNumCategories()
    for i in range(count):
        category = debugger.GetCategoryAtIndex(i)
        print("category: ", category.name)


# ********************************************************
# REGISTRATION
# ********************************************************

IDRE = "([^,]+)"


def id_template(min, max):
    th = f"{IDRE}"
    if min == 1 and max == 1:
        return th
    temp = f"{th}"
    for i in range(min - 1):
        temp += f",{th}"
    for i in range(max - min):
        temp += f"(?:,{th})?"
    return temp


def get_template_regex(name: str, min, max) -> str:
    return f"^(::)?{name}<{id_template(min, max)}>$"


# fmt: on

module = sys.modules[__name__]


def attach_synthetic_to_type(module, category: SBTypeCategory, type_name, synth_class, is_regex=True):
    # print_trace('attaching synthetic %s to "%s", is_regex=%s' %(synth_class.__name__, type_name, is_regex))
    synth = SBTypeSynthetic.CreateWithClassName(module.__name__ + "." + synth_class.__name__)
    synth.SetOptions(eTypeOptionCascade)
    if not category.AddTypeSynthetic(SBTypeNameSpecifier(type_name, is_regex), synth):
        print(f"Failed to add synthetic for {type_name}")

    def summary_fn(valobj, dict):
        return get_synth_summary(synth_class, valobj, dict)

    # LLDB accesses summary fn's by name, so we need to create a unique one.
    summary_fn.__name__ = "_get_synth_summary_" + synth_class.__name__
    setattr(module, summary_fn.__name__, summary_fn)
    print_trace(f"attaching summary {summary_fn.__name__} to {type_name}, is_regex={is_regex}")
    summary = SBTypeSummary.CreateWithFunctionName(__name__ + "." + summary_fn.__name__)
    summary.SetOptions(eTypeOptionCascade)
    if not category.AddTypeSummary(SBTypeNameSpecifier(type_name, is_regex), summary):
        print(f"Failed to add summary for {type_name}")

    # attach_summary_to_type(summary_fn, type_name, is_regex)


def attach_summary_to_type(module, category: SBTypeCategory, type_name, real_summary_fn, is_regex=False, real_fn_name: Optional[str] = None):
    if not real_fn_name:
        real_fn_name = str(real_summary_fn.__qualname__)
    def __spfunc(valobj, dict):
        try:
            return real_summary_fn(valobj, dict)
        except Exception as e:
            err_msg = "ERROR in " + real_fn_name + ": " + str(e)
            print_verbose(err_msg)
            print_verbose(get_exception_trace(e))
            return f"<{err_msg}>"

    # LLDB accesses summary fn's by name, so we need to create a unique one.
    __spfunc.__name__ = "__spfunc__" + real_fn_name.replace(".", "_")
    setattr(module, __spfunc.__name__, __spfunc)

    summary = SBTypeSummary.CreateWithFunctionName(__name__ + "." + __spfunc.__name__)
    summary.SetOptions(eTypeOptionCascade)
    if not category.AddTypeSummary(SBTypeNameSpecifier(type_name, is_regex), summary):
        print(f"Failed to add summary for {type_name}")


def remove_all_summary_providers(category: SBTypeCategory, SUMMARY_PROVIDERS):
    for key in SUMMARY_PROVIDERS:
        try:
            if category.DeleteTypeSummary(SBTypeNameSpecifier(key, True)):
                print_trace(f"Deleted summary for {key}")
            else:
                print_trace(f"No summary found for {key}")
        except Exception as e:
            print_verbose(f"EXCEPTION WHILE REMOVING {key}: " + str(e))


def remove_all_synth_providers(category: SBTypeCategory, SYNTHETIC_PROVIDERS):
    for key in SYNTHETIC_PROVIDERS:
        try:
            if category.DeleteTypeSynthetic(SBTypeNameSpecifier(key, True)):
                print_trace(f"Deleted synthetic for {key}")
            else:
                print_trace(f"No synthetic found for {key}")
        except Exception as e:
            print_verbose(f"EXCEPTION WHILE REMOVING {key}: " + str(e))


def remove_all_providers(category: SBTypeCategory, SUMMARY_PROVIDERS, SYNTHETIC_PROVIDERS):
    remove_all_summary_providers(category, SUMMARY_PROVIDERS)
    remove_all_summary_providers(category, SYNTHETIC_PROVIDERS)
    remove_all_synth_providers(category, SYNTHETIC_PROVIDERS)


def register_all_synth_and_summary_providers(
    module, category: SBTypeCategory, debugger: SBDebugger, SUMMARY_PROVIDERS, SYNTHETIC_PROVIDERS
):
    remove_all_providers(category, SUMMARY_PROVIDERS, SYNTHETIC_PROVIDERS)
    for key in SUMMARY_PROVIDERS:
        try:
            attach_summary_to_type(module, category, key, SUMMARY_PROVIDERS[key], True)
        except Exception as e:
            print_verbose("EXCEPTION: " + str(e))
    for key in SYNTHETIC_PROVIDERS:
        try:
            attach_synthetic_to_type(module, category, key, SYNTHETIC_PROVIDERS[key], True)
        except Exception as e:
            print_verbose("EXCEPTION st: " + str(e))


def monkey_patch_optparse():
    if not "bool" in optparse.Option.TYPES:
        optparse.Option.TYPES = optparse.Option.TYPES + ("bool",)
    if not "bool" in optparse.Option.TYPE_CHECKER:
        optparse.Option.TYPE_CHECKER["bool"] = lambda option, opt, value: value.lower() in [
            "true",
            "t",
            "yes",
            "y",
            "1",
        ]


# ********************************************************
# COMMANDS
# ********************************************************

# fmt: off
class _LLDBCommandBase:
    program = ""
    description = ""

    @classmethod
    def register_lldb_command(cls, debugger: SBDebugger, module_name: str, container_name: str, alias_name: str):
        # now add an alias
        alias = f'{container_name}_{cls.program}'
        if not cls.program:
            print("ERROR: No program name specified for command")
            return
        try:
            parser = cls.create_options()
            cls.__doc__ = parser.format_help() if parser else cls.description
            # Add any commands contained in this module to LLDB
            command = "command script add -o -c %s.%s %s %s" % (
                module_name,
                cls.__name__,
                container_name,
                cls.program,
            )
            debugger.HandleCommand(command)
        except Exception as e:
            print("ERROR: " + str(e))
            print('The "{0}" command failed to install.'.format(cls.program))
            return
        prefix = alias_name if alias_name else container_name
        full_program_name = prefix + " " + cls.program

        print('The "{0}" command has been installed, type "help {0}" for detailed help.'.format(full_program_name))

    @classmethod
    def create_options(cls):
        return None

    def get_short_help(self):
        return self.description

    def get_long_help(self):
        return self.description

    def __init__(self, debugger, unused):
        pass


class ReloadCommand(_LLDBCommandBase):
    program = "reload"
    description = "Reloads all synthetic types and such."

    def __call__(
        self,
        debugger: SBDebugger,
        command,
        exe_ctx: SBExecutionContext,
        result: SBCommandReturnObject,
    ):
        # Use the Shell Lexer to properly parse up command options just like a
        # shell would
        register_all_providers(debugger)
        # not returning anything is akin to returning success
        return


class GetOptsCommand(_LLDBCommandBase):
    program = "get_opts"
    description = "This command prints a list of the current option settings for the Godot formatter script."

    def __call__(
        self,
        debugger: SBDebugger,
        command,
        exe_ctx: SBExecutionContext,
        result: SBCommandReturnObject,
    ):
        # Use the Shell Lexer to properly parse up command options just like a
        # shell would
        results = []
        dir_opts = dir(Opts)
        max_attr_len = max(len(attr) for attr in dir(Opts))
        for attr in dir(Opts):
            if attr.startswith("__"):
                continue
            val = getattr(Opts, attr)
            if val is None or val == "":
                val = "<None>"
            help_string = HELP_STRING_MAP[str(attr)]
            res = f"{attr:{max_attr_len}} - {help_string}\n    - current value: {val}"
            results.append(res)
        result.AppendMessage("\n".join(results))
        result.SetStatus(eReturnStatusSuccessFinishResult)
        # not returning anything is akin to returning success
        return


class SetOptsCommand(_LLDBCommandBase):
    program = "set_opts"
    description = "This command sets the options for the Godot formatter script."

    @classmethod
    def create_options(cls):
        usage = "usage: %prog [options]"

        # Pass add_help_option = False, since this keeps the command in line
        #  with lldb commands, and we wire up "help command" to work by
        # providing the long & short help methods below.
        parser = optparse.OptionParser(
            description=cls.description,
            prog=cls.program,
            usage=usage,
            add_help_option=False,
            formatter=optparse.IndentedHelpFormatter(2, 30, width=80),
        )

        for attr in dir(GodotFormatterOptions):
            if attr.startswith("__"):
                continue
            # get the type of the attribute
            attr_val = getattr(GodotFormatterOptions, attr)
            attr_type = type(attr_val)
            # get the attribute docstring
            help_string = HELP_STRING_MAP[attr] + f" (default: {attr_val})\n"
            _ = parser.add_option(
                f"--{attr.lower().replace('_', '-')}",
                action="store",
                type=attr_type.__name__,
                dest=attr,
                help=help_string,
                metavar=f"<{str(attr_type.__name__).upper()}>",
                # default=attr_val,
            )
        # parser.print_help()
        return parser

    def get_short_help(self):
        return self.description

    def get_long_help(self):
        return self.help_string

    def __init__(self, debugger, unused):
        self.parser = self.create_options()
        self.help_string = self.parser.format_help()

    def __call__(
        self,
        debugger: SBDebugger,
        command,
        exe_ctx: SBExecutionContext,
        result: SBCommandReturnObject,
    ):
        # Use the Shell Lexer to properly parse up command options just like a
        # shell would
        command_args = shlex.split(command)
        try:
            (options, args) = self.parser.parse_args(command_args)
        except:
            if command_args and len(command_args) > 0 and ("--help" in command_args or "-h" in command_args):
                print(self.get_long_help())
                return
            # if you don't handle exceptions, passing an incorrect argument to
            # the OptionParser will cause LLDB to exit (courtesy of OptParse
            # dealing with argument errors by throwing SystemExit)
            print("Error: Unknown option")
            print(self.get_long_help())
            result.SetError("option parsing failed")
            return

        option: str
        set_option = False
        for option in options.__dict__:
            if option.startswith("__"):
                continue
            if options.__dict__[option] is None:
                continue
            set_option = True
            Opts.__setattr__(option, options.__dict__[option])
            print(f"Set option {option} to {options.__dict__[option]}")
        if not set_option:
            result.SetError("No options were set")
            self.parser.print_help()
            return

        print("Options have been set. Resetting formatters...")
        register_all_providers(debugger)
        result.SetStatus(eReturnStatusSuccessFinishNoResult)
        # not returning anything is akin to returning success
        return
    

    
def register_all_providers(debugger: SBDebugger):
    global module
    cpp_category: SBTypeCategory = debugger.GetDefaultCategory()
    rust_category: SBTypeCategory = debugger.GetCategory("Rust")
    if not rust_category:
        debugger.HandleCommand("type category enable Rust")
        rust_category = debugger.GetCategory("Rust")
    if not rust_category:
        print("Failed to enable Rust category, using C++ category instead")
        rust_category = cpp_category
    # No longer needed, enabling the Rust category now works and we don't want to clobber existing C++ providers
    # that happen to share the same name
    # else:
    #     #ensure that the cpp category has no summary providers for gdext types
    #     remove_all_providers(cpp_category, GDEXT_SUMMARY_PROVIDERS, GDEXT_SYNTHETIC_PROVIDERS)
    register_all_synth_and_summary_providers(module, cpp_category, debugger, SUMMARY_PROVIDERS, SYNTHETIC_PROVIDERS)
    register_all_synth_and_summary_providers(module, rust_category, debugger, GDEXT_SUMMARY_PROVIDERS, GDEXT_SYNTHETIC_PROVIDERS)
    #GDEXT STUFF


def __lldb_init_module(debugger: SBDebugger, dict):
    clear_globals()
    monkey_patch_optparse()
    register_all_providers(debugger)
    print(f"{FORMATTER_NAME} synth and summary types have been loaded")
    # for some godforsaken reason, the container name doesn't work through vscode repl unless it's aliased
    debugger.HandleCommand(f'command container add {CONTAINER_NAME} -h "{FORMATTER_NAME} commands" -H "{FORMATTER_NAME} <subcommand> [<subcommand-options>]" -o')
    debugger.HandleCommand(f'command alias {FORMATTER_NAME} {CONTAINER_NAME}')
    SetOptsCommand.register_lldb_command(debugger, __name__, CONTAINER_NAME, FORMATTER_NAME)
    GetOptsCommand.register_lldb_command(debugger, __name__, CONTAINER_NAME, FORMATTER_NAME)
    ReloadCommand.register_lldb_command(debugger, __name__, CONTAINER_NAME, FORMATTER_NAME)
