from importlib import reload


import datetime
import shlex
import sys
from time import sleep
import traceback
import optparse
import re
import json

from enum import Enum
import weakref
from types import TracebackType
from typing import final, Optional


# fmt: off
from lldb import (SBCommandReturnObject, SBExecutionContext, SBTypeCategory, eFormatBytes, eFormatCString, eFormatUnicode32, eNoDynamicValues, eDynamicDontRunTarget, eDynamicCanRunTarget, eBasicTypeInvalid, eBasicTypeVoid, eBasicTypeChar, # pyright: ignore[reportMissingModuleSource]
                  eBasicTypeSignedChar, eBasicTypeUnsignedChar, eBasicTypeWChar, eBasicTypeSignedWChar, eBasicTypeUnsignedWChar, eBasicTypeChar16, eBasicTypeChar32, 
                  eBasicTypeChar8, eBasicTypeShort, eBasicTypeUnsignedShort, eBasicTypeInt, eBasicTypeUnsignedInt, eBasicTypeLong, eBasicTypeUnsignedLong, eBasicTypeLongLong, 
                  eBasicTypeUnsignedLongLong, eBasicTypeInt128, eBasicTypeUnsignedInt128, eBasicTypeBool, eBasicTypeHalf, eBasicTypeFloat, eBasicTypeDouble, eBasicTypeLongDouble, 
                  eBasicTypeFloatComplex, eBasicTypeDoubleComplex, eBasicTypeLongDoubleComplex, eBasicTypeObjCID, eBasicTypeObjCClass, eBasicTypeObjCSel, eBasicTypeNullPtr, eReturnStatusSuccessFinishNoResult, eReturnStatusSuccessFinishResult, 
                  eTypeClassClass, eTypeClassEnumeration, eTypeClassPointer, eTypeOptionCascade)
from lldb import ( SBValue, SBAddress, SBData, SBType, SBTypeEnumMember, SBTypeEnumMemberList, SBSyntheticValueProvider, SBError, SBTarget, SBDebugger, SBTypeSummary, SBTypeSynthetic, SBTypeNameSpecifier)  # pyright: ignore[reportMissingModuleSource]
# fmt: on


import godot_formatters.options

from godot_formatters.options import *

def print_verbose(val: str):
    if Opts.PRINT_VERBOSE or Opts.PRINT_TRACE:
        print(val)


def print_trace(val: str, *args, **kwargs):
    if Opts.PRINT_TRACE:
        # curr_time = datetime.datetime.now().strftime("%H:%M:%S.%f")
        # format = f"[{curr_time}] {val}"
        print(val, *args, **kwargs)


# ********************************************************
# DEBUG TRACING
# ********************************************************


def self_none_if_invalid(func):
    def wrapper(*args, **kwargs):
        if not not_null_check(args[1]):
            return None
        return func(*args, **kwargs)

    return wrapper

def self_none_if_invalid_ret(func):
    def wrapper(*args, **kwargs):
        if not not_null_check(args[1]):
            return None
        ret = func(*args, **kwargs)
        if not not_null_check(ret):
            return None
        return ret
    return wrapper

def wrap_in_try_except_ret_error_summary(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print(f"Error calling {func.__name__}")
            print(str(e))
            traceback.print_exc()   
            return ERROR_SUMMARY
    return wrapper

def wrap_in_try_except_ret_none(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print(f"Error calling {func.__name__}")
            print(str(e))
            traceback.print_exc()
            return None
    return wrapper

def wrap_in_try_except_ret_false(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print(f"Error calling {func.__name__}")
            print(str(e))
            traceback.print_exc()
            return False
    return wrapper

def wrap_in_try_except_ret_0(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print(f"Error calling {func.__name__}")
            print(str(e))
            traceback.print_exc()
            return 0    
    return wrapper

def self_zero_if_invalid(func):
    def wrapper(*args, **kwargs):
        if not not_null_check(args[1]):
            return 0
        return func(*args, **kwargs)

    return wrapper


def get_start_tr_format(func_name: str):
    global level
    return ("  " * level) + func_name + " {"


def get_end_tr_format(func_name: str):
    global level
    return ("  " * level) + "} // " + func_name


def get_func_name(func, args):
    return str(func.__qualname__)


def get_arg_str(arg):
    # check if this can be turned into a string
    ret = "<unknown>"
    if arg is None:
        return "None"
    if hasattr(arg, "GetName") or isinstance(arg, SBValue) or isinstance(arg, SBType):
        return get_valobj_name(arg)
    if isinstance(arg, str) or hasattr(arg, "__str__"):
        ret = str(arg)
        if not (ret.startswith("<") and ret.endswith(">") and "object at" in ret):
            return ret
        else:
            ret = ret.split(" ")[0] + ">"
    if hasattr(arg, "__class__"):
        return "<" + arg.__class__.__name__ + ">"
    return ret


def _mk_func_call(func, *args, **kwargs):
    if len(args) == 1 and len(kwargs) == 0:
        return func(args[0])
    return func(*args, **kwargs)


def mk_func_call(func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except Exception as e:
        print(f"Error calling {func.__name__}")
        print(f"Args length: {len(args)}")
        print(f"kwargs length: {len(kwargs)}")
        is_method = "." in func.__qualname__

        def sanitize(i, arg):
            if i == 0 and is_method:
                return "self"
            elif isinstance(arg, dict):
                return "<dict>"
            return arg

        args_str = ", ".join([get_arg_str(sanitize(i, arg)) for i, arg in enumerate(args)])
        print(f"Args: {args_str}")
        kwargs_str = ", ".join([f"{key}={get_arg_str(val)}" for key, val in kwargs.items()])
        print(f"Kwargs: {kwargs_str}")
        print(str(e))
        traceback.print_exc()
        sleep(2)
        return None


level = 0


def trace_func_call(func, *args, **kwargs):
    global level
    func_name = str(func.__qualname__)
    is_method = "." in func_name
    filters = get_filter()
    # filters = []
    matched = len(filters) == 0
    for filter in get_filter():
        regex = re.compile(filter)
        if regex.match(func_name):
            matched = True
            break
    if not matched:
        return _mk_func_call(func, *args, **kwargs)
    func_name = (
        func_name.replace("SynthProvider", "SP")
        .replace("SummaryProvider", "SumProv")
        .replace("SyntheticProvider", "SP")
    )
    if len(args) > 0 and isinstance(args[0], SBSyntheticValueProvider) and hasattr(args[0], "valobj"):
        func_name += f"<{get_valobj_name(args[0].valobj)}>"  # pyright: ignore[reportAttributeAccessIssue]

    def sanitize(i, arg):
        if i == 0 and is_method:
            return "self"
        elif isinstance(arg, dict):
            return "<dict>"
        return arg

    args_str = ", ".join([get_arg_str(sanitize(i, arg)) for i, arg in enumerate(args)])
    args_str += ", ".join([f"{key}={get_arg_str(val)}" for key, val in kwargs.items()])
    print_verbose(get_start_tr_format(f"{func_name}({args_str})"))
    level += 1
    ret = mk_func_call(func, *args, **kwargs)
    level -= 1
    ret_str = get_arg_str(ret)
    print_verbose(get_end_tr_format(func_name) + f" -> {ret_str}")
    return ret


def get_gsp_print_str(func_name: str, args):
    if len(args) > 0 and isinstance(args[0], SBSyntheticValueProvider):
        valobj = None
        if hasattr(args[0], "valobj"):
            valobj = args[0].valobj
        return get_start_tr_format(func_name) + f" on {get_valobj_name(valobj)}"
    return get_start_tr_format(func_name)


def print_trace_dec(func):
    def _pr_trace_wrap(*args, **kwargs):
        return trace_func_call(func, *args, **kwargs)

    if not Opts.PRINT_TRACE:
        return func
    _pr_trace_wrap.__name__ = func.__name__
    _pr_trace_wrap.__qualname__ = func.__qualname__
    return _pr_trace_wrap


def trace_none_if_invalid_dec(func):
    def wrapper(*args, **kwargs):
        if not not_null_check(args[1]):
            func_name = get_func_name(func, args)
            print_verbose(get_gsp_print_str(func_name, args))
            print_verbose(get_end_tr_format(func_name) + ": Aborting due to invalid args[1]")
            return None
        return trace_func_call(func, *args, **kwargs)

    if not Opts.PRINT_TRACE:
        return self_none_if_invalid(func)
    wrapper.__name__ = func.__name__
    wrapper.__qualname__ = func.__qualname__
    return wrapper


# ********************************************************
# UTILITIES
# ********************************************************


@print_trace_dec
def should_use_key_val_style(key_template_type) -> bool:
    return (
        Opts.MAP_KEY_VAL_STYLE
        and key_template_type is not None
        and (is_string_type(key_template_type) or is_basic_integer_type(key_template_type))
    )


def GetFloat(valobj: SBValue) -> float:
    dataArg: SBData = valobj.GetData()
    if valobj.GetByteSize() > 4:
        # real_t is a double
        return dataArg.GetDouble(SBError(), 0)  # type: ignore
    else:
        # real_t is a float
        return dataArg.GetFloat(SBError(), 0)  # type: ignore


def GetFloatStr(valobj: SBValue, short: bool = False) -> str:
    val = GetFloat(valobj)
    if short:
        return "{:.3f}".format(val)
    return str(val)


def is_basic_printable_type(type: SBType):
    if type.GetTypeClass() == eTypeClassEnumeration:
        return True

    basic_type = type.GetCanonicalType().GetBasicType()
    if basic_type == eBasicTypeVoid:
        return False
    if basic_type == eBasicTypeInvalid:
        return False
    if basic_type == eBasicTypeObjCID:
        return False
    if basic_type == eBasicTypeObjCClass:
        return False
    if basic_type == eBasicTypeObjCSel:
        return False
    return True


def is_basic_string_type(type: SBType):
    # check to see if it's a const char*, const wchar_t*, const char16_t*, const char32_t*
    if not type.IsPointerType():
        return False
    if not "const" in type.name:
        return False
    basic_type = type.GetCanonicalType().GetBasicType()
    if basic_type == eBasicTypeChar:
        return True
    if basic_type == eBasicTypeWChar:
        return True
    if basic_type == eBasicTypeChar16:
        return True
    if basic_type == eBasicTypeChar32:
        return True
    return False


def is_basic_integer_type(type: SBType):
    if type is None:
        return False
    if type.GetTypeClass() == eTypeClassEnumeration:
        return True
    basic_type = type.GetCanonicalType().GetBasicType()
    if basic_type == eBasicTypeChar:
        return True
    if basic_type == eBasicTypeSignedChar:
        return True
    if basic_type == eBasicTypeUnsignedChar:
        return True
    if basic_type == eBasicTypeWChar:
        return True
    if basic_type == eBasicTypeSignedWChar:
        return True
    if basic_type == eBasicTypeUnsignedWChar:
        return True
    if basic_type == eBasicTypeChar16:
        return True
    if basic_type == eBasicTypeChar32:
        return True
    if basic_type == eBasicTypeChar8:
        return True
    if basic_type == eBasicTypeShort:
        return True
    if basic_type == eBasicTypeUnsignedShort:
        return True
    if basic_type == eBasicTypeInt:
        return True
    if basic_type == eBasicTypeUnsignedInt:
        return True
    if basic_type == eBasicTypeLong:
        return True
    if basic_type == eBasicTypeUnsignedLong:
        return True
    if basic_type == eBasicTypeLongLong:
        return True
    if basic_type == eBasicTypeUnsignedLongLong:
        return True
    if basic_type == eBasicTypeInt128:
        return True
    if basic_type == eBasicTypeUnsignedInt128:
        return True
    if basic_type == eBasicTypeBool:
        return True

    return False


def get_enum_string(valobj: SBValue) -> str:
    type: SBType = valobj.GetType()
    enumMembers: SBTypeEnumMemberList = type.GetEnumMembers()
    starting_value = valobj.GetValueAsUnsigned()
    if enumMembers.IsValid() and enumMembers.GetSize() > 0:
        member: SBTypeEnumMember
        member_names: list[str] = []
        member_values: list[int] = []
        for member in enumMembers:
            member_names.append(member.name)
            member_values.append(member.unsigned)
        if member_values.count(starting_value) == 0:
            # this is probably a flag
            flag_summary = ""
            remaining_value = starting_value
            for i, member_value in enumerate(member_values):
                if member_value & remaining_value:
                    if flag_summary != "":
                        flag_summary += " | "
                    flag_summary += member_names[i]
                    # remove the flag from the start_value
                    remaining_value &= ~member_value
            if remaining_value != 0:
                if remaining_value != starting_value:
                    flag_summary += " | "
                flag_summary += "0x" + format(remaining_value, "x")
            # flag_summary += " (" + str(starting_value) + ")"
            return flag_summary
        else:
            # get the index of the value
            name = member_names[member_values.index(starting_value)]
            return name  # + " (" + str(starting_value) + ")"
    return "<Invalid Enum> (" + str(starting_value) + ")"


def get_basic_printable_string(valobj: SBValue) -> str:
    type: SBType = valobj.GetType()
    if type.GetTypeClass() == eTypeClassEnumeration:
        return get_enum_string(valobj)
    # char_pointer_type: SBType = valobj.target.GetBasicType(eBasicTypeChar).GetPointerType()

    basic_type = type.GetCanonicalType().GetBasicType()
    if basic_type == eBasicTypeInvalid:
        return INVALID_SUMMARY
    if basic_type == eBasicTypeVoid:
        return "<void>"
    if basic_type == eBasicTypeObjCID:
        return str(valobj.GetSummary())
    if basic_type == eBasicTypeObjCClass:
        return str(valobj.GetSummary())
    if basic_type == eBasicTypeObjCSel:
        return str(valobj.GetSummary())
    if basic_type == eBasicTypeNullPtr:
        return NULL_SUMMARY
    if basic_type == eBasicTypeChar:
        return str(valobj.GetValueAsSigned())
    if basic_type == eBasicTypeSignedChar:
        return str(valobj.GetValueAsSigned())
    if basic_type == eBasicTypeUnsignedChar:
        return str(valobj.GetValueAsUnsigned())
    if basic_type == eBasicTypeWChar:
        return str(valobj.GetValueAsSigned())
    if basic_type == eBasicTypeSignedWChar:
        return str(valobj.GetValueAsSigned())
    if basic_type == eBasicTypeUnsignedWChar:
        return str(valobj.GetValueAsUnsigned())
    if basic_type == eBasicTypeChar16:
        return str(valobj.GetValueAsSigned())
    if basic_type == eBasicTypeChar32:
        return str(valobj.GetValueAsSigned())
    if basic_type == eBasicTypeChar8:
        return str(valobj.GetValueAsSigned())
    if basic_type == eBasicTypeShort:
        return str(valobj.GetValueAsSigned())
    if basic_type == eBasicTypeUnsignedShort:
        return str(valobj.GetValueAsUnsigned())
    if basic_type == eBasicTypeInt:
        return str(valobj.GetValueAsSigned())
    if basic_type == eBasicTypeUnsignedInt:
        return str(valobj.GetValueAsUnsigned())
    if basic_type == eBasicTypeLong:
        return str(valobj.GetValueAsSigned())
    if basic_type == eBasicTypeUnsignedLong:
        return str(valobj.GetValueAsUnsigned())
    if basic_type == eBasicTypeLongLong:
        return str(valobj.GetValueAsSigned())
    if basic_type == eBasicTypeUnsignedLongLong:
        return str(valobj.GetValueAsUnsigned())
    if basic_type == eBasicTypeInt128:
        return str(valobj.GetValueAsSigned())
    if basic_type == eBasicTypeUnsignedInt128:
        return str(valobj.GetValueAsUnsigned())
    if basic_type == eBasicTypeBool:
        return str(valobj.GetValueAsUnsigned())
    if basic_type == eBasicTypeHalf:
        return GetFloatStr(valobj)
    if basic_type == eBasicTypeFloat:
        return GetFloatStr(valobj)
    if basic_type == eBasicTypeDouble:
        return GetFloatStr(valobj)
    if basic_type == eBasicTypeLongDouble:
        return GetFloatStr(valobj)
    if basic_type == eBasicTypeFloatComplex:
        return GetFloatStr(valobj)
    if basic_type == eBasicTypeDoubleComplex:
        return GetFloatStr(valobj)
    if basic_type == eBasicTypeLongDoubleComplex:
        return GetFloatStr(valobj)
    return INVALID_SUMMARY


def is_valid_pointer(ptr: SBValue) -> bool:
    if not ptr:
        print_verbose("is_valid_pointer(): ptr is None")
        return False
    if not ptr.IsValid():
        print_verbose("is_valid_pointer(): ptr is not valid SBValue")
        return False
    if not ptr.GetType().IsPointerType():
        print_verbose("is_valid_pointer(): ptr is not a pointer")
        return False
    if ptr.GetValueAsUnsigned() == 0:
        print_verbose("is_valid_pointer(): ptr = nullptr")
        return False
    if not ptr.Dereference().IsValid():
        print_verbose("is_valid_pointer(): ptr dereference is not valid")
        return False
    return True


def pointer_exists_and_is_null(ptr: SBValue) -> bool:
    if ptr is None or not ptr.IsValid():
        return False
    if not ptr.GetType().IsPointerType():
        return False
    if ptr.GetValueAsUnsigned() == 0:
        return True
    return False


def strip_quotes(val: str):
    if val.startswith('U"'):
        val = val.removeprefix('U"').removesuffix('"')
    else:
        val = val.removeprefix('"').removesuffix('"')
    return val


# Cowdata size is located at the cowdata address - 8 bytes (sizeof(uint64_t))
def get_exception_trace(e: Exception, before_exception_limit=5, _this_call_depth=2) -> str:
    stack_prefix = "Traceback (most recent call last):\n"
    exception_trace = traceback.format_exception(type(e), e, e.__traceback__)
    stack_trace_str = "".join(exception_trace[1:]).replace("\\n", "\n")
    if before_exception_limit > 0:
        before_exc_stack_trace = traceback.format_stack(limit=(before_exception_limit + 2))
        stack_trace_str = (
            "".join(before_exc_stack_trace[:-_this_call_depth]).replace("\\n", "\n") + "Handled:\n" + stack_trace_str
        )
    return stack_prefix + stack_trace_str


def print_exception_trace(e: Exception, before_exception_limit=5) -> None:
    print(get_exception_trace(e, before_exception_limit, 3))


@print_trace_dec
def get_offset_of_object_member(obj: SBValue, member: str) -> int:
    if not obj.IsValid():
        return -1
    # check if obj is a pointer
    if obj.GetType().IsPointerType():
        obj = obj.Dereference()
        if not obj.IsValid():
            return -1
    obj_addr: SBValue = obj.AddressOf()
    element_addr_val = obj_addr.GetValueAsUnsigned()
    member_val: SBValue = obj.GetChildMemberWithName(member)
    member_addr: SBValue = member_val.AddressOf()
    member_addr_val = member_addr.GetValueAsUnsigned()
    return member_addr_val - element_addr_val  # type: ignore


def not_null_check(valobj: Optional[SBValue]) -> bool:
    if not valobj or not valobj.IsValid():
        return False
    return True


@print_trace_dec
def get_synth_summary(synth_class, valobj: SBValue, dict):
    obj = valobj
    if valobj.IsSynthetic():
        obj = valobj.GetNonSyntheticValue()
    synth = synth_class(obj, dict, 1)
    summary = synth.get_summary()
    return summary


def ValCheck(val: SBValue) -> SBValue:
    if not val:
        raise Exception("SBValue is None")
    error = val.GetError()
    if error.Fail() or not val.IsValid():
        fmt_err = f"{val.GetName()}: " if val.GetName() else ""
        if error.Fail():
            raise Exception(fmt_err + error.GetCString())
        else:
            raise Exception(fmt_err + "SBValue is not valid")
    return val


# ********************************************************
# GODOT-SPECIFIC UTILITIES
# ********************************************************


NON_RECURSIVE = [
    "String",
    "Vector2",
    "Vector2i",
    "Rect2",
    "Rect2i",
    "Vector3",
    "Vector3i",
    "Transform2D",
    "Vector4",
    "Vector4i",
    "Plane",
    "Quaternion",
    "AABB",
    "Basis",
    "Transform3D",
    "Projection",
    "Color",
    "StringName",
    "NodePath",
    "RID",
    # "Callable",
    "Signal",
    "ObjectID",
]


def get_valobj_name(valobj) -> str:
    fmt = "-{0}-"
    if valobj is None or not hasattr(valobj, "GetName"):
        return fmt.format("NULL")
    elif not valobj.IsValid():
        return "<INVALID>"
    return fmt.format(valobj.GetName())


@print_trace_dec
def is_string_type(type: SBType):
    if type is None:
        return False
    type_class = type.GetTypeClass()
    if type_class == eTypeClassClass or type_class == eTypeClassPointer:
        _class_type = type
        if type_class == eTypeClassPointer:
            _class_type = type.GetPointeeType()
        type_name: str = _class_type.GetUnqualifiedType().GetDisplayTypeName()
        if type_name == "String":
            return True
        elif type_name == "StringName":
            return True
        elif type_name == "StringBuffer":
            return True
        elif type_name == "NodePath":
            return True
    elif is_basic_string_type(type):
        return True

    return False


@print_trace_dec
def get_cowdata_size_or_none(_cowdata: SBValue, null_means_zero=True) -> Optional[int]:
    # global cow_err_str
    size = 0
    if not _cowdata or not _cowdata.IsValid():
        print_verbose("COWDATASIZE Invalid: _cowdata is not valid")
        stack_fmt = traceback.format_stack()
        print_verbose("".join(stack_fmt[:-1]).replace("\\n", "\n"))
        return None
    try:
        _ptr: SBValue = _cowdata.GetChildMemberWithName("_ptr")
        if null_means_zero and pointer_exists_and_is_null(_ptr):
            return 0
        if not is_valid_pointer(_ptr):
            print_verbose("COWDATASIZE Invalid: _ptr is not valid")
            return None
        _cowdata_template_type: SBType = _cowdata.GetType().GetTemplateArgumentType(0)
        if not _cowdata_template_type.IsValid():
            print_verbose("COWDATASIZE Invalid: _cowdata template type is not valid")
            return None
        uint64_type: SBType = _cowdata.GetTarget().GetBasicType(eBasicTypeUnsignedLongLong)
        ptr_addr_val = _ptr.GetValueAsUnsigned()
        if ptr_addr_val - 8 < 0:
            print_verbose("COWDATASIZE Invalid: ptr_addr_val - 8 is less than 0: " + str(ptr_addr_val))
            return None
        size_child: SBValue = _ptr.CreateValueFromAddress("size", ptr_addr_val - 8, uint64_type)
        if not size_child.IsValid():
            print_verbose("COWDATASIZE Invalid: Size value at ptr_addr - 8 is not valid")
            return None
        size = size_child.GetValueAsSigned()
        if size < 0:
            print_verbose("COWDATASIZE Invalid: Size is less than 0: " + str(size))
            return None
        if size > 0:
            item_size = _ptr.GetType().GetByteSize()
            last_val = _ptr.CreateValueFromAddress(
                "_tmp_tail",
                ptr_addr_val + ((size - 1) * item_size),
                _ptr.GetType().GetPointeeType(),
            )
            if not last_val.IsValid():
                print_verbose("COWDATASIZE Invalid: Last value is not valid: " + str(last_val))
                return None
    except Exception as e:
        print_verbose("COWDATASIZE Exception: " + str(e))
        print_verbose(get_exception_trace(e))
        return None

    return size


def is_cowdata_valid(_cowdata: SBValue) -> bool:
    size = get_cowdata_size_or_none(_cowdata)
    if size is None:
        return False
    return True


def get_cowdata_size(_cowdata: SBValue) -> int:
    size = get_cowdata_size_or_none(_cowdata)
    if size is None:
        return 0
    return size
