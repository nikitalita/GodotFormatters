# Description: Godot formatters for lldb

# Add the following lines to your ~/.lldbinit, or run this line directly in the debug console:
# `command script import <PATH_TO_SCRIPT>/lldb_godot_formatters.py`


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
from typing import Any, Callable, Generic, Never, TypeVar, final, Optional

# fmt: off
from lldb import (SBCommandReturnObject, SBExecutionContext, SBPlatform, SBTypeCategory, SBValue, eFormatBytes, eFormatCString, eFormatUnicode16, eFormatUnicode32, eNoDynamicValues, eDynamicDontRunTarget, eDynamicCanRunTarget, eBasicTypeInvalid, eBasicTypeVoid, eBasicTypeChar, 
                  eBasicTypeSignedChar, eBasicTypeUnsignedChar, eBasicTypeWChar, eBasicTypeSignedWChar, eBasicTypeUnsignedWChar, eBasicTypeChar16, eBasicTypeChar32, 
                  eBasicTypeChar8, eBasicTypeShort, eBasicTypeUnsignedShort, eBasicTypeInt, eBasicTypeUnsignedInt, eBasicTypeLong, eBasicTypeUnsignedLong, eBasicTypeLongLong, 
                  eBasicTypeUnsignedLongLong, eBasicTypeInt128, eBasicTypeUnsignedInt128, eBasicTypeBool, eBasicTypeHalf, eBasicTypeFloat, eBasicTypeDouble, eBasicTypeLongDouble, 
                  eBasicTypeFloatComplex, eBasicTypeDoubleComplex, eBasicTypeLongDoubleComplex, eBasicTypeObjCID, eBasicTypeObjCClass, eBasicTypeObjCSel, eBasicTypeNullPtr, eReturnStatusSuccessFinishNoResult, eReturnStatusSuccessFinishResult, 
                  eTypeClassClass, eTypeClassEnumeration, eTypeClassPointer, eTypeOptionCascade)
from lldb import ( SBValue, SBAddress, SBData, SBType, SBTypeEnumMember, SBTypeEnumMemberList, SBSyntheticValueProvider, SBError, SBTarget, SBDebugger, SBTypeSummary, SBTypeSynthetic, SBTypeNameSpecifier)
# fmt: on
# fmt: off

# avoid circular import
get_synthetic_provider_for_type: Callable[[str], Optional[type]]
get_summary_provider_for_type: Callable[[str], Optional[type]]


from importlib import reload

import godot_formatters.utils

# godot_formatters.utils = reload(godot_formatters.utils)
from godot_formatters.utils import *

from godot_formatters.utils import (
    print_trace_dec,
    print_verbose,
    GetFloat,
    get_cowdata_size_or_none,
    GetFloatStr,
)

import godot_formatters.options

# godot_formatters.options = reload(godot_formatters.options)
from godot_formatters.options import *

UINT32_MAX = 4294967295
INT32_MAX = 2147483647





# ********************************************************
# SUMMARY PROVIDERS
# ********************************************************
class VariantType(Enum):
    NIL = 0
    BOOL = 1
    INT = 2
    FLOAT = 3
    STRING = 4
    VECTOR2 = 5
    VECTOR2I = 6
    RECT2 = 7
    RECT2I = 8
    VECTOR3 = 9
    VECTOR3I = 10
    TRANSFORM2D = 11
    VECTOR4 = 12
    VECTOR4I = 13
    PLANE = 14
    QUATERNION = 15
    AABB = 16
    BASIS = 17
    TRANSFORM3D = 18
    PROJECTION = 19
    COLOR = 20
    STRING_NAME = 21
    NODE_PATH = 22
    RID = 23
    OBJECT = 24
    CALLABLE = 25
    SIGNAL = 26
    DICTIONARY = 27
    ARRAY = 28
    PACKED_BYTE_ARRAY = 29
    PACKED_INT32_ARRAY = 30
    PACKED_INT64_ARRAY = 31
    PACKED_FLOAT32_ARRAY = 32
    PACKED_FLOAT64_ARRAY = 33
    PACKED_STRING_ARRAY = 34
    PACKED_VECTOR2_ARRAY = 35
    PACKED_VECTOR3_ARRAY = 36
    PACKED_COLOR_ARRAY = 37
    PACKED_VECTOR4_ARRAY = 38
    VARIANT_MAX = 39


@print_trace_dec
def get_variant_type(valobj: SBValue) -> VariantType | None:
    if valobj.IsSynthetic():
        valobj = valobj.GetNonSyntheticValue()
    type_member = valobj.GetChildMemberWithName("type")
    if not type_member.IsValid():
        return None
    type = type_member.GetValueAsUnsigned()
    return VariantType(type)

def is_variant_type_non_recursive(type: VariantType | None) -> bool:
    return type is not None and type not in [
        VariantType.PACKED_BYTE_ARRAY,
        VariantType.PACKED_INT32_ARRAY,
        VariantType.PACKED_INT64_ARRAY,
        VariantType.PACKED_FLOAT32_ARRAY,
        VariantType.PACKED_FLOAT64_ARRAY,
        VariantType.PACKED_STRING_ARRAY,
        VariantType.PACKED_VECTOR2_ARRAY,
        VariantType.PACKED_VECTOR3_ARRAY,
        VariantType.PACKED_COLOR_ARRAY,
        VariantType.PACKED_VECTOR4_ARRAY,
        VariantType.OBJECT, 
        VariantType.DICTIONARY, 
        VariantType.ARRAY, 
        VariantType.CALLABLE, 
        VariantType.SIGNAL, 
        VariantType.VARIANT_MAX]

@print_trace_dec
def Variant_GetValue(valobj: SBValue):
    # we need to get the type of the variant
    type = valobj.GetChildMemberWithName("type").GetValueAsUnsigned()
    # switch on type
    data: SBValue = valobj.GetChildMemberWithName("_data")
    mem: SBValue = data.GetChildMemberWithName("_mem")
    mem_addr: SBAddress = mem.GetAddress()
    packed_array: SBValue = data.GetChildMemberWithName("packed_array")
    packed_array_addr: SBAddress = packed_array.GetAddress()
    target: SBTarget = valobj.target
    if type == VariantType.NIL.value:
        return None
    elif type == VariantType.BOOL.value:
        return data.GetChildMemberWithName("_bool")
    elif type == VariantType.INT.value:
        return data.GetChildMemberWithName("_int")
    elif type == VariantType.FLOAT.value:
        return data.GetChildMemberWithName("_float")
    elif type == VariantType.TRANSFORM2D.value:
        _transform2d = data.GetChildMemberWithName("_transform2d")
        if is_valid_pointer(_transform2d):
            return _transform2d
        else:
            return None
    elif type == VariantType.AABB.value:
        _aabb = data.GetChildMemberWithName("_aabb")
        if is_valid_pointer(_aabb):
            return _aabb
        else:
            return None
    elif type == VariantType.BASIS.value:
        _basis = data.GetChildMemberWithName("_basis")
        if is_valid_pointer(_basis):
            return _basis
        else:
            return None
    elif type == VariantType.TRANSFORM3D.value:
        _transform3d = data.GetChildMemberWithName("_transform3d")
        if is_valid_pointer(_transform3d):
            return _transform3d
        else:
            return None
    elif type == VariantType.PROJECTION.value:
        _projection = data.GetChildMemberWithName("_projection")
        if is_valid_pointer(_projection):
            return _projection
        else:
            return None
    elif type == VariantType.STRING.value:  # For _mem values, we have to cast them to the correct type
        # find the type for "String"
        stringType: SBType = target.FindFirstType("::String")
        string: SBValue = target.CreateValueFromAddress("[string]", mem_addr, stringType)
        return string
    elif type == VariantType.VECTOR2.value:
        vector2Type: SBType = target.FindFirstType("::Vector2")
        vector2: SBValue = target.CreateValueFromAddress("[vector2]", mem_addr, vector2Type)
        return vector2
    elif type == VariantType.VECTOR2I.value:
        vector2IType: SBType = target.FindFirstType("::Vector2i")
        vector2i: SBValue = target.CreateValueFromAddress("[vector2i]", mem_addr, vector2IType)
        return vector2i
    elif type == VariantType.RECT2.value:
        rect2Type: SBType = target.FindFirstType("::Rect2")
        rect2: SBValue = target.CreateValueFromAddress("[rect2]", mem_addr, rect2Type)
        return rect2
    elif type == VariantType.RECT2I.value:
        rect2IType: SBType = target.FindFirstType("::Rect2i")
        rect2i: SBValue = target.CreateValueFromAddress("[rect2i]", mem_addr, rect2IType)
        return rect2i
    elif type == VariantType.VECTOR3.value:
        vector3Type: SBType = target.FindFirstType("::Vector3")
        vector3: SBValue = target.CreateValueFromAddress("[vector3]", mem_addr, vector3Type)
        return vector3
    elif type == VariantType.VECTOR3I.value:
        vector3iType: SBType = target.FindFirstType("::Vector3i")
        vector3i: SBValue = target.CreateValueFromAddress("[vector3i]", mem_addr, vector3iType)
        return vector3i
    elif type == VariantType.VECTOR4.value:
        vector4Type: SBType = target.FindFirstType("::Vector4")
        vector4: SBValue = target.CreateValueFromAddress("[vector4]", mem_addr, vector4Type)
        return vector4
    elif type == VariantType.VECTOR4I.value:
        vector4iType: SBType = target.FindFirstType("::Vector4i")
        vector4i: SBValue = target.CreateValueFromAddress("[vector4i]", mem_addr, vector4iType)
        return vector4i
    elif type == VariantType.PLANE.value:
        planeType: SBType = target.FindFirstType("::Plane")
        plane: SBValue = target.CreateValueFromAddress("[plane]", mem_addr, planeType)
        return plane
    elif type == VariantType.QUATERNION.value:
        quaternionType: SBType = target.FindFirstType("::Quaternion")
        quaternion: SBValue = target.CreateValueFromAddress("[quaternion]", mem_addr, quaternionType)
        return quaternion
    elif type == VariantType.COLOR.value:
        colorType: SBType = target.FindFirstType("::Color")
        color: SBValue = target.CreateValueFromAddress("[color]", mem_addr, colorType)
        return color
    elif type == VariantType.STRING_NAME.value:
        stringNameType: SBType = target.FindFirstType("::StringName")
        stringName: SBValue = target.CreateValueFromAddress("[stringName]", mem_addr, stringNameType)
        return stringName
    elif type == VariantType.NODE_PATH.value:
        nodePathType: SBType = target.FindFirstType("::NodePath")
        nodePath: SBValue = target.CreateValueFromAddress("[nodePath]", mem_addr, nodePathType)
        return nodePath
    elif type == VariantType.RID.value:
        ridType: SBType = target.FindFirstType("::RID")
        rid: SBValue = target.CreateValueFromAddress("[rid]", mem_addr, ridType)
        return rid
    elif type == VariantType.OBJECT.value:
        objDataType: SBType = target.FindFirstType("Variant::ObjData")
        objData: SBValue = target.CreateValueFromAddress("[objData]", mem_addr, objDataType)
        return objData.GetChildMemberWithName("obj")
    elif type == VariantType.CALLABLE.value:
        callableType: SBType = target.FindFirstType("::Callable")
        callable: SBValue = target.CreateValueFromAddress("[callable]", mem_addr, callableType)
        return callable
    elif type == VariantType.SIGNAL.value:
        signalType: SBType = target.FindFirstType("::Signal")
        signal: SBValue = target.CreateValueFromAddress("[signal]", mem_addr, signalType)
        return signal
    elif type == VariantType.DICTIONARY.value:
        dictionaryType: SBType = target.FindFirstType("::Dictionary")
        dictionary: SBValue = target.CreateValueFromAddress("[dictionary]", mem_addr, dictionaryType)
        return dictionary
    elif type == VariantType.ARRAY.value:
        arrayType: SBType = target.FindFirstType("::Array")
        array: SBValue = target.CreateValueFromAddress("[array]", mem_addr, arrayType)
        return array
    else:
        if not is_valid_pointer(packed_array):
            return None
        if type == VariantType.PACKED_BYTE_ARRAY.value:
            packedByteArrayType: SBType = target.FindFirstType("Variant::PackedArrayRef<unsigned char>")
            packedByteArray: SBValue = target.CreateValueFromAddress(
                "packedByteArrayref", packed_array_addr, packedByteArrayType
            )
            return packedByteArray.GetChildMemberWithName("array")
        elif type == VariantType.PACKED_INT32_ARRAY.value:
            packedInt32ArrayType: SBType = target.FindFirstType("Variant::PackedArrayRef<int>")
            packedInt32Array: SBValue = target.CreateValueFromAddress(
                "packedInt32Arrayref", packed_array_addr, packedInt32ArrayType
            )
            return packedInt32Array.GetChildMemberWithName("array")
        elif type == VariantType.PACKED_INT64_ARRAY.value:
            packedInt64ArrayType: SBType = target.FindFirstType("Variant::PackedArrayRef<long long>")
            packedInt64Array: SBValue = target.CreateValueFromAddress(
                "packedInt64Arrayref", packed_array_addr, packedInt64ArrayType
            )
            return packedInt64Array.GetChildMemberWithName("array")
        elif type == VariantType.PACKED_FLOAT32_ARRAY.value:
            packedFloat32ArrayType: SBType = target.FindFirstType("Variant::PackedArrayRef<float>")
            packedFloat32Array: SBValue = target.CreateValueFromAddress(
                "packedFloat32Arrayref", packed_array_addr, packedFloat32ArrayType
            )
            return packedFloat32Array.GetChildMemberWithName("array")
        elif type == VariantType.PACKED_FLOAT64_ARRAY.value:
            packedFloat64ArrayType: SBType = target.FindFirstType("Variant::PackedArrayRef<double>")
            packedFloat64Array: SBValue = target.CreateValueFromAddress(
                "packedFloat64Arrayref", packed_array_addr, packedFloat64ArrayType
            )
            return packedFloat64Array.GetChildMemberWithName("array")
        elif type == VariantType.PACKED_VECTOR2_ARRAY.value:
            packedVector2ArrayType: SBType = target.FindFirstType("Variant::PackedArrayRef<Vector2>")
            packedVector2Array: SBValue = target.CreateValueFromAddress(
                "packedVector2Arrayref", packed_array_addr, packedVector2ArrayType
            )
            return packedVector2Array.GetChildMemberWithName("array")
        elif type == VariantType.PACKED_VECTOR3_ARRAY.value:
            packedVector3ArrayType: SBType = target.FindFirstType("Variant::PackedArrayRef<Vector3>")
            packedVector3Array: SBValue = target.CreateValueFromAddress(
                "packedVector3Arrayref", packed_array_addr, packedVector3ArrayType
            )
            return packedVector3Array.GetChildMemberWithName("array")
        elif type == VariantType.PACKED_STRING_ARRAY.value:
            packedStringArrayType: SBType = target.FindFirstType("Variant::PackedArrayRef<String>")
            packedStringArray: SBValue = target.CreateValueFromAddress(
                "packedStringArrayref", packed_array_addr, packedStringArrayType
            )
            return packedStringArray.GetChildMemberWithName("array")
        elif type == VariantType.PACKED_COLOR_ARRAY.value:
            packedColorArrayType: SBType = target.FindFirstType("Variant::PackedArrayRef<Color>")
            packedColorArray: SBValue = target.CreateValueFromAddress(
                "packedColorArrayref", packed_array_addr, packedColorArrayType
            )
            return packedColorArray.GetChildMemberWithName("array")
        elif type == VariantType.PACKED_VECTOR4_ARRAY.value:
            packedVector4ArrayType: SBType = target.FindFirstType("Variant::PackedArrayRef<Vector4>")
            packedVector4Array: SBValue = target.CreateValueFromAddress(
                "packedVector4Arrayref", packed_array_addr, packedVector4ArrayType
            )
            return packedVector4Array.GetChildMemberWithName("array")
    return None


class _SBSyntheticValueProviderWithSummary(SBSyntheticValueProvider):
    def get_summary(self, max_children=Opts.MAX_AMOUNT_OF_CHILDREN_IN_SUMMARY, max_str_len=Opts.SUMMARY_STRING_MAX_LENGTH) -> str:
        raise Exception("Not implemented")

    def check_valid(self, obj: SBValue) -> bool:
        raise Exception("Not implemented")


class GodotSynthProvider(_SBSyntheticValueProviderWithSummary):
    synth_by_id: weakref.WeakValueDictionary[int, _SBSyntheticValueProviderWithSummary] = weakref.WeakValueDictionary()
    next_id = 0

    @print_trace_dec
    def __init__(self, valobj: SBValue, internal_dict, is_summary=False):
        super().__init__(valobj)  # Not needed, but we need to call it to satisfy the linter
        self.valobj = valobj
        self.internal_dict = internal_dict
        self.is_summary = is_summary
        self.obj_id = GodotSynthProvider.next_id
        GodotSynthProvider.synth_by_id[self.obj_id] = self
        GodotSynthProvider.next_id += 1

    # SBSyntheticValueProvider, override these
    def num_children(self, max=UINT32_MAX) -> int:
        raise Exception("Not implemented")

    @print_trace_dec
    def update(self) -> None:
        pass

    def has_children(self) -> bool:
        raise Exception("Not implemented")

    def get_child_at_index(self, idx: int) -> SBValue:
        raise Exception("Not implemented")

    # Don't override this, override get_index_of_child instead
    @print_trace_dec
    def get_child_index(self, name: str) -> Optional[int]:
        if name == "$$object-id$$":
            return self.obj_id
        try:
            return self.get_index_of_child(name)
        except Exception as e:
            print_verbose(str(e))
            raise e

    @print_trace_dec
    def get_index_of_child(self, name: str) -> Optional[int]:
        raise Exception("Not implemented")

    # _SBSyntheticValueProviderWithSummary
    @print_trace_dec
    def get_summary(self, max_children=Opts.MAX_AMOUNT_OF_CHILDREN_IN_SUMMARY, max_str_len=Opts.SUMMARY_STRING_MAX_LENGTH) -> str:
        if not self.check_valid(self.valobj):
            return INVALID_SUMMARY
        return GenericShortSummary(self.valobj, self.internal_dict, summary_length=max_str_len, no_children=True)

    def check_valid(self, obj: SBValue) -> bool:
        print("check_valid not implemented")
        return False

# template function
T = TypeVar('T', bound=_SBSyntheticValueProviderWithSummary)

def get_synth_provider_for_object(cls: type[T], valobj: SBValue, internal_dict, is_summary) -> T:
    obj_id = valobj.GetIndexOfChildWithName("$$object-id$$")
    if obj_id in GodotSynthProvider.synth_by_id:
        synth_prov = GodotSynthProvider.synth_by_id[obj_id]  # type: ignore
        if isinstance(synth_prov, cls):
            return synth_prov
        else:
            print(f"ERROR: Synth provider for {valobj.GetDisplayTypeName()} is not of type {cls.__name__}, is {type(synth_prov).__name__}")
    return cls(valobj.GetNonSyntheticValue(), internal_dict, is_summary)  # type: ignore


class Variant_SyntheticProvider(GodotSynthProvider):
    def __init__(self, valobj: SBValue, internal_dict, is_summary=False):
        super().__init__(valobj, internal_dict, is_summary)
        self.update()

    @print_trace_dec
    def check_valid(self, obj: SBValue) -> bool:
        variant_type = obj.GetChildMemberWithName("type").GetValueAsUnsigned()
        data = Variant_GetValue(obj)
        if variant_type < VariantType.NIL.value or variant_type >= VariantType.VARIANT_MAX.value:
            return False
        if VariantType.NIL.value == variant_type:
            return True
        if data is None or not data.IsValid():
            return False
        return True

    @print_trace_dec
    def _get_variant_type(self):
        return self.valobj.GetChildMemberWithName("type").GetValueAsUnsigned()

    @print_trace_dec
    def update(self):
        self.data = Variant_GetValue(self.valobj)
        self.variant_type = self._get_variant_type()

    @print_trace_dec
    def get_summary(self, max_children=Opts.MAX_AMOUNT_OF_CHILDREN_IN_SUMMARY, max_str_len=Opts.SUMMARY_STRING_MAX_LENGTH):
        if not self.check_valid(self.valobj):
            return INVALID_SUMMARY
        type = self.variant_type
        if type == VariantType.NIL.value:
            return NIL_SUMMARY
        if not not_null_check(self.data) or not self.data:
            return INVALID_SUMMARY
        data: SBValue = self.data
        if type == VariantType.BOOL.value:
            return "true" if data.GetValueAsUnsigned() != 0 else "false"
        elif type == VariantType.INT.value:
            return str(data.GetValueAsSigned())
        elif type == VariantType.FLOAT.value:
            return GetFloatStr(data)
        elif type == VariantType.OBJECT.value:
            prefix = "{" + str(data.GetType().GetPointeeType().GetDisplayTypeName()) + "*:"
            # TODO: avoiding infinite recursion here by not calling GenericShortSummary
            # return prefix + GenericShortSummary(data, self.internal_dict, len(prefix)+1, True) + "}"
            return prefix + "{...}}"
        else:
            summary = data.GetSummary()
            if not summary:
                summary = "{" + data.GetDisplayTypeName() + ":{...}}"
            return summary

    def num_children(self, max=UINT32_MAX):
        if self.variant_type <= VariantType.NIL.value or self.variant_type >= VariantType.VARIANT_MAX.value:
            return 0
        else:
            if self.data is None:
                return 0
            return 1

    def has_children(self):
        return self.num_children() != 0

    def get_index_of_child(self, name: str):
        return 0 if self.has_children() else None

    def get_child_at_index(self, idx: int) -> SBValue:
        return self.data or SBValue()


def StringName_SummaryProvider(valobj: SBValue, internal_dict):
    _data: SBValue = valobj.GetChildMemberWithName("_data")
    if _data.GetValueAsUnsigned() == 0:
        return NULL_SUMMARY
    # `cname` was removed in 4.6
    cname = _data.GetChildMemberWithName("cname")
    if not not_null_check(cname) or cname.GetValueAsSigned() == 0:
        return _data.GetChildMemberWithName("name").GetSummary()
    else:
        return _data.GetChildMemberWithName("cname").GetSummary()


def Ref_SummaryProvider(valobj: SBValue, internal_dict):
    return GenericShortSummary(valobj, internal_dict)

def get_summary_or_invalid_summary(valobj: SBValue) -> str:
    if not not_null_check(valobj):
        return INVALID_SUMMARY
    summary = valobj.GetSummary()
    return summary

def NodePath_SummaryProvider(valobj: SBValue, internal_dict):
    rstr = ""
    data: SBValue = valobj.GetChildMemberWithName("data")
    if data and data.IsValid() and data.GetValueAsUnsigned() == 0:
        return NULL_SUMMARY
    if not is_valid_pointer(data):
        return INVALID_SUMMARY
    path_obj = data.GetChildMemberWithName("path")
    path = Vector_SyntheticProvider(path_obj.GetNonSyntheticValue(), internal_dict)
    subpath_obj = data.GetChildMemberWithName("subpath")
    subpath = Vector_SyntheticProvider(subpath_obj.GetNonSyntheticValue(), internal_dict)
    path_size = path.num_children()
    subpath_size = subpath.num_children()
    if path_size == 0 and subpath_size == 0:
        return EMPTY_SUMMARY
    is_absolute = data.GetChildMemberWithName("absolute").GetValueAsUnsigned()
    if is_absolute != 0:
        rstr = "/"
    for i in range(path_size):
        child = path.get_child_at_index(i)
        rstr += strip_quotes(get_summary_or_invalid_summary(child))
        if i < path.num_children() - 1:
            rstr += "/"
    if subpath_size > 0:
        rstr += ":"
    for i in range(subpath_size):
        child = subpath.get_child_at_index(i)
        rstr += strip_quotes(get_summary_or_invalid_summary(child))
        if i < subpath_size - 1:
            rstr += ":"
    return rstr


@print_trace_dec
def Quaternion_SummaryProvider(valobj: SBValue, internal_dict):
    return "{{{0}, {1}, {2}, {3}}}".format(
        GetFloat(valobj.GetChildMemberWithName("x")),
        GetFloat(valobj.GetChildMemberWithName("y")),
        GetFloat(valobj.GetChildMemberWithName("z")),
        GetFloat(valobj.GetChildMemberWithName("w")),
    )


@print_trace_dec
def ObjectID_SummaryProvider(valobj: SBValue, internal_dict):
    fmt = "<ObjectID={0}>"
    id: SBValue = valobj.GetChildMemberWithName("id")
    if not id.IsValid():
        return fmt.format(INVALID_SUMMARY)
    val = id.GetValueAsUnsigned()
    if val == 0:
        return fmt.format(NULL_SUMMARY)
    return fmt.format(val)


@print_trace_dec
def Signal_SummaryProvider(valobj: SBValue, internal_dict):
    # Signal has a StringName name and an ObjectID object
    name: SBValue = valobj.GetChildMemberWithName("name")
    object: SBValue = valobj.GetChildMemberWithName("object")
    name_summary, object_summary = name.GetSummary(), object.GetSummary()
    if not name_summary or not object_summary:
        return INVALID_SUMMARY
    if NULL_SUMMARY in name_summary and NULL_SUMMARY in object_summary:
        return "{{<Signal> {0}}}".format(NULL_SUMMARY)
    return "{{<Signal> name:{0}, object:{1}}}".format(name_summary, object_summary)


@print_trace_dec
def Callable_SummaryProvider(valobj: SBValue, internal_dict):
    # If `method` is blank, and `custom` is not a null pointer, then it's a CallableCustom
    method: SBValue = valobj.GetChildMemberWithName("method")  # StringName
    method_name: str = method.GetSummary()
    if method_name == NULL_SUMMARY or method_name == EMPTY_SUMMARY:
        custom: SBValue = valobj.GetChildMemberWithName("custom")
        if custom.GetValueAsUnsigned() != 0:
            # TODO: Avoiding infinite recursion here by not calling GenericShortSummary
            custom_type: SBType = custom.GetType()
            if not custom_type.IsValid():
                return "{{<CallableCustom> {0}}}".format(INVALID_SUMMARY)
            return "{{<CallableCustom> {0}:{{...}}}}".format(custom_type.GetPointeeType().GetDisplayTypeName())
            # return "CallableCustom: " + GenericShortSummary(custom, internal_dict)
        else:
            # get the object
            obj_id: SBValue = valobj.GetChildMemberWithName("object")
            obj_id_val = obj_id.GetValueAsUnsigned()
            if obj_id_val == 0:
                return "{<Callable> " + NULL_SUMMARY + "}"
            return "{{<Callable> object:{0}, method:{1}}}".format(obj_id_val, method_name)


@print_trace_dec
def Vector2_SummaryProvider(valobj: SBValue, internal_dict):
    return "({0}, {1})".format(
        GetFloat(valobj.GetChildMemberWithName("x")),
        GetFloat(valobj.GetChildMemberWithName("y")),
    )


@print_trace_dec
def Vector3_SummaryProvider(valobj: SBValue, internal_dict):
    return "({0}, {1}, {2})".format(
        GetFloat(valobj.GetChildMemberWithName("x")),
        GetFloat(valobj.GetChildMemberWithName("y")),
        GetFloat(valobj.GetChildMemberWithName("z")),
    )


@print_trace_dec
def Vector4_SummaryProvider(valobj: SBValue, internal_dict):
    return "({0}, {1}, {2}, {3})".format(
        GetFloat(valobj.GetChildMemberWithName("x")),
        GetFloat(valobj.GetChildMemberWithName("y")),
        GetFloat(valobj.GetChildMemberWithName("z")),
        GetFloat(valobj.GetChildMemberWithName("w")),
    )


@print_trace_dec
def Vector2i_SummaryProvider(valobj: SBValue, internal_dict):
    return "({0}, {1})".format(
        valobj.GetChildMemberWithName("x").GetValueAsSigned(),
        valobj.GetChildMemberWithName("y").GetValueAsSigned(),
    )


@print_trace_dec
def Vector3i_SummaryProvider(valobj: SBValue, internal_dict):
    return "({0}, {1}, {2})".format(
        valobj.GetChildMemberWithName("x").GetValueAsSigned(),
        valobj.GetChildMemberWithName("y").GetValueAsSigned(),
        valobj.GetChildMemberWithName("z").GetValueAsSigned(),
    )


@print_trace_dec
def Vector4i_SummaryProvider(valobj: SBValue, internal_dict):
    return "({0}, {1}, {2}, {3})".format(
        valobj.GetChildMemberWithName("x").GetValueAsSigned(),
        valobj.GetChildMemberWithName("y").GetValueAsSigned(),
        valobj.GetChildMemberWithName("z").GetValueAsSigned(),
        valobj.GetChildMemberWithName("w").GetValueAsSigned(),
    )


@print_trace_dec
def Rect2_SummaryProvider(valobj: SBValue, internal_dict):
    return "{{position: ({0}, {1}), size: ({2}, {3})}}".format(
        GetFloat(valobj.GetChildMemberWithName("position").GetChildMemberWithName("x")),
        GetFloat(valobj.GetChildMemberWithName("position").GetChildMemberWithName("y")),
        GetFloat(valobj.GetChildMemberWithName("size").GetChildMemberWithName("x")),
        GetFloat(valobj.GetChildMemberWithName("size").GetChildMemberWithName("y")),
    )


@print_trace_dec
def Rect2i_SummaryProvider(valobj: SBValue, internal_dict):
    return "{{position: ({0}, {1}), size: ({2}, {3})}}".format(
        valobj.GetChildMemberWithName("position").GetChildMemberWithName("x").GetValueAsSigned(),
        valobj.GetChildMemberWithName("position").GetChildMemberWithName("y").GetValueAsSigned(),
        valobj.GetChildMemberWithName("size").GetChildMemberWithName("x").GetValueAsSigned(),
        valobj.GetChildMemberWithName("size").GetChildMemberWithName("y").GetValueAsSigned(),
    )


def ConstructNamedColorTable(global_named_colors_table: SBValue) -> dict[str, str]:
    table: dict[str, str] = dict[str, str]()
    try:
        for i in range(global_named_colors_table.GetNumChildren()):
            named_color = ValCheck(global_named_colors_table.GetChildAtIndex(i))
            name_val = ValCheck(named_color.GetChildMemberWithName("name"))
            name_val_summary = name_val.GetSummary()
            if not name_val_summary:  # nullptr at the end of the array
                break
            name = strip_quotes(name_val_summary)
            color = ValCheck(named_color.GetChildMemberWithName("color"))
            hex_str = GetHexColor(*GetColorVals(color))
            table[hex_str] = name
    except Exception as e:
        print_verbose(f"EXCEPTION ConstructNamedColorTable: " + str(e))
        return dict[str, str]()
    return table


constructed_the_table = False
hex_color_to_name: dict[str, str] = {}


def TryConstructNamedColorTable(target: SBTarget) -> None:
    global constructed_the_table
    if not constructed_the_table:
        global hex_color_to_name
        named_colors = target.FindFirstGlobalVariable("named_colors")
        if not named_colors or not named_colors.IsValid() or named_colors.GetNumChildren() == 0:
            return  # return without setting constructed_the_table; we might not be in the right context to do this
        hex_color_to_name = ConstructNamedColorTable(named_colors)
        constructed_the_table = True
        # print_trace(str(hex_color_to_name))


def GetColorAlias(valobj: SBValue, vals: Optional[tuple[float, float, float, float]] = None) -> str:
    r, g, b, a = vals if vals else GetColorVals(valobj)
    hex_str = GetHexColor(r, g, b, a)
    TryConstructNamedColorTable(valobj.target)
    if hex_str in hex_color_to_name:
        hex_str = hex_color_to_name[hex_str]
    return hex_str


def GetHexColor(r, g, b, a) -> str:
    def _get_hex(val: float):
        new_val = max(min(round(val * 255), 255), 0)
        return "{:02x}".format(new_val)

    r_hex, g_hex, b_hex, a_hex = _get_hex(r), _get_hex(g), _get_hex(b), _get_hex(a)
    return "#{0}{1}{2}{3}".format(r_hex, g_hex, b_hex, a_hex)


def GetColorVals(valobj: SBValue):
    return (
        GetFloat(valobj.GetChildMemberWithName("r")),
        GetFloat(valobj.GetChildMemberWithName("g")),
        GetFloat(valobj.GetChildMemberWithName("b")),
        GetFloat(valobj.GetChildMemberWithName("a")),
    )


@print_trace_dec
def Color_SummaryProvider(valobj: SBValue, internal_dict):
    r, g, b, a = GetColorVals(valobj)
    if not Opts.NAMED_COLOR_ANNOTATION:
        hex_str = GetHexColor(r, g, b, a)
    else:
        hex_str = GetColorAlias(valobj, (r, g, b, a))
    return "{{<{0}> r:{1:.3f}, g:{2:.3f}, b:{3:.3f}, a:{4:.3f}}}".format(hex_str, r, g, b, a)


@print_trace_dec
def Plane_SummaryProvider(valobj: SBValue, internal_dict):
    return "{{normal: {0}, d: {1}}}".format(
        valobj.GetChildMemberWithName("normal").GetSummary(),
        valobj.GetChildMemberWithName("d").GetValueAsSigned(),
    )


@print_trace_dec
def AABB_SummaryProvider(valobj: SBValue, internal_dict):
    return "{{position: {{{0}}}, size: {{{1}}}}}".format(
        valobj.GetChildMemberWithName("position").GetSummary(),
        valobj.GetChildMemberWithName("size").GetSummary(),
    )


@print_trace_dec
def Transform2D_SummaryProvider(valobj: SBValue, internal_dict):
    # transform2d has a Vector2 `origin`, Vector2 `x`, and Vector2 `y`
    x_row = valobj.GetChildMemberWithName("columns").GetChildAtIndex(0)
    y_row = valobj.GetChildMemberWithName("columns").GetChildAtIndex(1)
    o_row = valobj.GetChildMemberWithName("columns").GetChildAtIndex(2)
    return "{{x: {0}, y: {1}, o: {2}}}".format(x_row.GetSummary(), y_row.GetSummary(), o_row.GetSummary())


@print_trace_dec
def Transform3D_SummaryProvider(valobj: SBValue, internal_dict):
    # transform3d has a Basis `basis` and Vector3 `origin`
    return "{{basis: {0}, origin: {1}}}".format(
        valobj.GetChildMemberWithName("basis").GetSummary(),
        valobj.GetChildMemberWithName("origin").GetSummary(),
    )


@print_trace_dec
def Projection_SummaryProvider(valobj: SBValue, internal_dict):
    # projection has 	`Vector4 columns[4]`
    return "{{columns: {{{0}, {1}, {2}, {3}}}}}".format(
        valobj.GetChildMemberWithName("columns").GetChildAtIndex(0).GetSummary(),
        valobj.GetChildMemberWithName("columns").GetChildAtIndex(1).GetSummary(),
        valobj.GetChildMemberWithName("columns").GetChildAtIndex(2).GetSummary(),
        valobj.GetChildMemberWithName("columns").GetChildAtIndex(3).GetSummary(),
    )


@print_trace_dec
def Basis_SummaryProvider(valobj: SBValue, internal_dict):
    # basis has a Vector3[3] `rows` (NOT `elements`)
    # need to translate into (xx, xy, xy), (yx, yy, yz), (zx, zy, zz)
    x_row = valobj.GetChildMemberWithName("rows").GetChildAtIndex(0)
    y_row = valobj.GetChildMemberWithName("rows").GetChildAtIndex(1)
    z_row = valobj.GetChildMemberWithName("rows").GetChildAtIndex(2)
    return "{{{0}, {1}, {2}}}".format(x_row.GetSummary(), y_row.GetSummary(), z_row.GetSummary())


@print_trace_dec
def RID_SummaryProvider(valobj: SBValue, internal_dict):
    return "<RID=" + str(valobj.GetChildMemberWithName("_id").GetValueAsUnsigned()) + ">"


@print_trace_dec
def String_SummaryProvider(valobj: SBValue, internal_dict):
    _cowdata: SBValue = valobj.GetChildMemberWithName("_cowdata")
    size = get_cowdata_size_or_none(_cowdata)
    if size is None:
        # check if this is a pointer to a pointer
        type = valobj.GetType()
        if type.IsPointerType() and type.GetPointeeType().IsPointerType():
            return "{...}"
        return INVALID_SUMMARY
    if size == 0:
        return EMPTY_SUMMARY

    # While cowdata has been promoted to 64-bits, this is still the limit for strings
    if STRINGS_STILL_32_BIT and size > INT32_MAX:
        return INVALID_SUMMARY
    _ptr: SBValue = _cowdata.GetChildMemberWithName("_ptr")
    _ptr.format = eFormatUnicode32
    data = _ptr.GetPointeeData(0, size)
    error: SBError = SBError()
    arr: bytearray = bytearray()
    for i in range(data.size):
        var = data.GetUnsignedInt8(error, i)
        arr.append(var)
    starr = arr.decode("utf-32LE")
    if starr.endswith("\x00"):
        starr = starr[:-1]
    if Opts.SANITIZE_STRING_SUMMARY: # Sanitize string summaries to escape all formatting characters and quotes
        new_str = ""
        for char in starr:
            if ord(char) < 32 or char == '"':
                new_str += '\\' + char
            else:
                new_str += char
        starr = new_str
    return '"{0}"'.format(starr)


@print_trace_dec
def CharString_SummaryProvider(valobj: SBValue, internal_dict):
    _cowdata: SBValue = valobj.GetChildMemberWithName("_cowdata")
    size = get_cowdata_size_or_none(_cowdata)
    type = valobj.GetType()
    if size is None:
        # check if this is a pointer to a pointer
        type = valobj.GetType()
        if type.IsPointerType() and type.GetPointeeType().IsPointerType():
            return "{...}"
        return INVALID_SUMMARY
    if size == 0:
        return EMPTY_SUMMARY
    template_type = type.GetTemplateArgumentType(0)
    format = eFormatCString
    if template_type == eBasicTypeChar16 or template_type == eBasicTypeWChar:
        format = eFormatUnicode16
    elif template_type == eBasicTypeChar32:
        format = eFormatUnicode32
    # While cowdata has been promoted to 64-bits, this is still the limit for strings
    if STRINGS_STILL_32_BIT and size > INT32_MAX:
        return INVALID_SUMMARY
    _ptr: SBValue = _cowdata.GetChildMemberWithName("_ptr")
    _ptr.format = format
    if Opts.SANITIZE_STRING_SUMMARY:
        ret = _ptr.GetSummary()
        if ret is None:
            print_trace("String_SummaryProvider: _ptr.GetSummary() returned None")
            return EMPTY_SUMMARY
        if ret.startswith('U"'):
            ret = '"' + ret.removeprefix('U"')
        return ret
    data = _ptr.GetPointeeData(0, size)
    error: SBError = SBError()
    arr: bytearray = bytearray()
    for i in range(data.size):
        var = data.GetUnsignedInt8(error, i)
        arr.append(var)
    starr = arr.decode("utf-8")
    if starr.endswith("\x00"):
        starr = starr[:-1]
    return '"{0}"'.format(starr)


def get_unqual_type_name(type: SBType) -> str:
    if type is None or not type.IsValid():
        return "<ERROR>"
    var = str(type.GetUnqualifiedType().GetDisplayTypeName())
    return var.removeprefix("godot::").removeprefix("::")

@print_trace_dec
def GenericShortSummary(
    valobj: SBValue,
    internal_dict,
    summary_length=0,
    skip_base_class=False,
    no_children=False,
    depth=0,
) -> str:
    if not valobj or not valobj.IsValid():
        return INVALID_SUMMARY
    depth += 1
    START_SUMMARY_LENGTH = summary_length
    is_child = summary_length != 0
    MAX_LEN = Opts.SUMMARY_STRING_MAX_LENGTH - (20 if is_child else 0)
    if summary_length > Opts.SUMMARY_STRING_MAX_LENGTH or depth > MAX_DEPTH:
        # bail out
        return "{...}"
    type: SBType = valobj.GetType()
    if is_basic_printable_type(type):
        return get_basic_printable_string(valobj)

    if type.IsPointerType():
        type = type.GetPointeeType()
    unqual_type_name = get_unqual_type_name(type)
    if unqual_type_name == "Variant":
        variant_type = get_variant_type(valobj)
        if is_variant_type_non_recursive(variant_type):
            return Variant_SyntheticProvider(valobj.GetNonSyntheticValue(), internal_dict).get_summary()
    if unqual_type_name == "Object" or unqual_type_name == "RefCounted":  # these lead to circular references
        return "{...}"
    if unqual_type_name.startswith("Ref<"):
        reference: SBValue = valobj.GetChildMemberWithName("reference")
        if not reference.IsValid():
            return "{" + INVALID_SUMMARY + "}"
        if reference.GetValueAsUnsigned() == 0:
            return "{" + NULL_SUMMARY + "}"
        deref: SBValue = reference.Dereference()
        if not deref.IsValid():
            return "{" + INVALID_SUMMARY + "}"
        prefix = "{[" + str(deref.GetDisplayTypeName()) + "]:"
        summary = GenericShortSummary(
            deref,
            internal_dict,
            START_SUMMARY_LENGTH + len(prefix),
            True,
            no_children,
            depth,
        )
        return prefix + summary + "}"
    summ = None
    if valobj.GetTypeSynthetic():  # Synthetic types will call this function again and could lead to infinite recursion.
        if unqual_type_name == "Variant":
            # Avoid putting it through the synthetic provider.
            variant_value = Variant_GetValue(valobj.GetNonSyntheticValue())
            if variant_value is None:
                return INVALID_SUMMARY
            return GenericShortSummary(
                variant_value,
                internal_dict,
                summary_length,
                skip_base_class,
                no_children,
                depth,
            )
        else:
            synth_provider_type = get_synthetic_provider_for_type(unqual_type_name)
            # check if it's derived from _ListOfChildren_SyntheticProvider
            # check if it's derived from _LinkedListLike_SyntheticProvider
            
            
            if synth_provider_type is not None:
                bases_str = str(synth_provider_type.__bases__)
                is_subclass_of_list_of_children = "_ListOfChildren_SyntheticProvider" in bases_str
                is_subclass_of_proxy = "_Proxy_SyntheticProvider" in bases_str
                if is_subclass_of_list_of_children or is_subclass_of_proxy:
                    synh_prov: _ListOfChildren_SyntheticProvider | _Proxy_SyntheticProvider = get_synth_provider_for_object(synth_provider_type, valobj, internal_dict, is_summary=True)
                    return synh_prov.get_summary(max_children=3, max_str_len=MAX_LEN - START_SUMMARY_LENGTH)
                # print the type name of the synth provider
                # print the parent class of the synth provider
            return unqual_type_name + "{...}"
    else:
        try:
            summ = valobj.GetSummary()
        except Exception as e:
            summ = " GetSummary() EXCEPTION: " + str(e)
            summ += " " + str(valobj.GetDisplayTypeName())
    if summ:
        return summ
    if no_children:
        return "{...}"
    base_classes: list[SBType] = type.get_bases_array()
    base_class_names = [base_class.GetName() for base_class in base_classes]
    summ_str = "{"
    try:
        num_children = valobj.GetNumChildren()
        skipped_base_class = False
        for i in range(num_children):
            child: SBValue = valobj.GetChildAtIndex(i)
            prefix = child.name + ":"
            if skip_base_class and base_class_names.count(child.name) > 0:
                skipped_base_class = True
                continue
            if is_basic_printable_type(child.GetType()):
                summ_str += prefix + get_basic_printable_string(child)
            else:
                summ_str += prefix + GenericShortSummary(
                    child,
                    internal_dict,
                    len(summ_str) + START_SUMMARY_LENGTH,
                    False,
                    no_children,
                    depth,
                )
            if len(summ_str) + START_SUMMARY_LENGTH > MAX_LEN:
                if i < len(valobj) - 1:
                    summ_str += ", ..."
                break
            if i < len(valobj) - 1:
                summ_str += ", "
        if summ_str == "{":
            summ_str += "..."
        if not summ_str.endswith(", ...") and skipped_base_class:
            summ_str += ", ..."
        summ_str += "}"
    except Exception as e:
        summ_str += " !!EXCEPTION: " + str(e)
        summ_str += " " + str(valobj.GetDisplayTypeName())
    return summ_str


def key_value_summary(valobj: SBValue, internal_dict, key_val_style):
    key = valobj.GetChildMemberWithName("key")
    value = valobj.GetChildMemberWithName("value")
    if key_val_style:
        return GenericShortSummary(value, internal_dict)
    return "{0}: {1}".format(
        GenericShortSummary(key, internal_dict),
        GenericShortSummary(value, internal_dict),
    )


def map_element_summary(valobj: SBValue, internal_dict, data_name):
    data: SBValue = valobj.GetChildMemberWithName(data_name)
    if not data or not data.IsValid():
        return None
    key = data.GetChildMemberWithName("key")
    style = should_use_key_val_style(key.GetType() if not_null_check(key) else None)
    return key_value_summary(data, internal_dict, style)


def KeyValue_SummaryProvider(valobj: SBValue, internal_dict):
    key = valobj.GetChildMemberWithName("key")
    style = should_use_key_val_style(key.GetType() if not_null_check(key) else None)
    return key_value_summary(valobj, internal_dict, style)


def HashMapElement_SummaryProvider(valobj: SBValue, internal_dict):
    return map_element_summary(valobj, internal_dict, "data")


def RBMapElement_SummaryProvider(valobj: SBValue, internal_dict):
    return map_element_summary(valobj, internal_dict, "_data")

HASHMAP_TRACE_ENABLED = False

def hashmap_trace(func):
    if not HASHMAP_TRACE_ENABLED:
        return func
    def _pr_trace_wrap(*args, **kwargs):
        # get the function return type
        exception_return_value = None
        if isinstance(func.__annotations__, dict):
            return_type = func.__annotations__.get("return")
            if return_type == int:
                exception_return_value = 0
            if return_type == str:
                exception_return_value = ERROR_SUMMARY
            else:
                exception_return_value = None
        else:
            exception_return_value = None
        try:
            # if not Opts.PRINT_VERBOSE:
            #     return func(*args, **kwargs)
            return trace_func_call(func, *args, **kwargs)
        except Exception as e:
            print_exception_trace(e)
            return exception_return_value

    _pr_trace_wrap.__name__ = func.__name__
    _pr_trace_wrap.__qualname__ = func.__qualname__
    return _pr_trace_wrap

# Disabled for now, causing crashes
class HashMapElement_SyntheticProvider(GodotSynthProvider):
    key_val_element_style: bool = Opts.MAP_KEY_VAL_STYLE

    @hashmap_trace
    def __init__(self, valobj: SBValue, internal_dict, is_summary=False):
        super().__init__(valobj, internal_dict, is_summary)
        # self.update()

    @hashmap_trace
    def update(self):
        pass

    @hashmap_trace
    def check_valid(self, obj: SBValue) -> bool:
        if not obj or not obj.IsValid():
            return False
        return True

    @hashmap_trace
    def get_index_of_child(self, name):
        if name == "[key]" or name == "key":
            return 0
        elif name == "[value]" or name == "value":
            return 1
        return None

    @hashmap_trace
    def get_data(self) -> Optional[SBValue]:
        if not self.check_valid(self.valobj):
            return None
        return self.valobj.GetChildMemberWithName("data")

    @hashmap_trace
    def get_key(self) -> Optional[SBValue]:
        data = self.get_data()
        if not data or not data.IsValid():
            return None
        key = data.GetChildMemberWithName("key")
        type = key.GetType()
        return self.valobj.CreateValueFromData("[key]", key.GetData(), type)

    @hashmap_trace
    def get_value(self) -> Optional[SBValue]:
        data = self.get_data()
        if not data or not data.IsValid():
            return None
        value = data.GetChildMemberWithName("value")
        type = value.GetType()
        return self.valobj.CreateValueFromData("[value]", value.GetData(), type)

    @hashmap_trace
    def get_child_at_index(self, idx: int) -> SBValue:
        if idx < 0 or idx > 1:
            return SBValue()
        if idx == 0:
            return self.get_key() or SBValue()
        else:
            return self.get_value() or SBValue()
        # return self.valobj

    @hashmap_trace
    def num_children(self, max=UINT32_MAX) -> int:
        if not self.check_valid(self.valobj):
            return 0
        return 2

    @hashmap_trace
    def has_children(self):
        if not self.check_valid(self.valobj):
            return False
        return True

    @hashmap_trace
    def get_summary(self, max_children=Opts.MAX_AMOUNT_OF_CHILDREN_IN_SUMMARY, max_str_len=Opts.SUMMARY_STRING_MAX_LENGTH) -> str:
        if not self.check_valid(self.valobj):
            return INVALID_SUMMARY
        value = self.get_value()
        if value is None:
            return INVALID_SUMMARY
        value_summary = GenericShortSummary(value, self.internal_dict, summary_length=max_str_len, no_children=True)
        if hasattr(self, "is_summary") and self.key_val_element_style:  # only show the value for the summary
            return value_summary
        key = self.get_key()
        if key is None:
            return INVALID_SUMMARY
        key_summary = GenericShortSummary(key, self.internal_dict, summary_length=max_str_len - len(value_summary), no_children=True)
        return "[{0}]: {1}".format(key_summary, value_summary)


class RBMapElement_SyntheticProvider(HashMapElement_SyntheticProvider):

    @print_trace_dec
    def get_data(self):
        return self.valobj.GetChildMemberWithName("_data")


class _ListOfChildren_SyntheticProvider(GodotSynthProvider):

    @print_trace_dec
    def __init__(self, valobj: SBValue, internal_dict, is_summary=False):
        self.type: SBType = valobj.GetType()
        self.typename: str = get_unqual_type_name(self.type)
        self.no_cache = NO_CACHE_MEMBERS
        self.cache_min = CACHE_MIN if not is_summary else Opts.MAX_AMOUNT_OF_CHILDREN_IN_SUMMARY
        self.cache_fetch_max = CACHE_FETCH_MAX
        self._cached_size = 0
        super().__init__(valobj, internal_dict, is_summary)
        self.update()

    def update(self) -> None:
        """
        Override this method to set any state that would normally be set in the constructor
        Note: This MUST update self.num_elements
        """
        raise Exception("Not implemented")

    def get_len(self, obj: SBValue) -> int:
        """
        Override this method to return the non-cached number of elements in this vector-like object
        """
        raise Exception("Not implemented")

    def get_ptr(self, obj: SBValue) -> SBValue:
        """
        Override this method to return the ptr to the first element; in arrays, this would just be the array pointer, in linked lists, this would be the head
        """
        raise Exception("Not implemented")

    def _create_child_at_element_index(self, index: int) -> Optional[SBValue]:
        """
        Override this method to return the synthetic child at the given index
        @param index: The index of the child to create
        """
        raise Exception("Not implemented")

    def _get_child_summary(self, real_index: int) -> str:
        """
        Override this method if you want to provide a custom summary for the child at the given index
        """
        element = self._create_child_at_element_index(real_index)
        if not not_null_check(element) or not element:
            return INVALID_SUMMARY
        return GenericShortSummary(element, self.internal_dict, 0, False, True)

    # def get_size_synthetic_child(self):
    #     return self.valobj.CreateValueFromData("[size]", SBData.CreateDataFromInt(self.num_elements), self.valobj.target.GetBasicType(eBasicTypeUnsignedInt))

    @property
    def num_elements(self) -> int:
        return self._cached_size

    @num_elements.setter
    def num_elements(self, value: int):
        self._cached_size = value

    @print_trace_dec
    def get_children_summary(self, max_children=Opts.MAX_AMOUNT_OF_CHILDREN_IN_SUMMARY, max_str_len=Opts.SUMMARY_STRING_MAX_LENGTH) -> str:
        if self.num_elements == 0:
            return ""
        max_children = min(Opts.MAX_AMOUNT_OF_CHILDREN_IN_SUMMARY, self.num_elements)
        i: int = 0
        summ_str = ""
        for i in range(max_children):
            summ_str += self._get_child_summary(i)
            if len(summ_str) > max_str_len:
                break
            if max_children != 1 and i < max_children - 1:
                summ_str += ", "
        if self.num_elements > i + 1:
            summ_str += ", ..."
        return summ_str

    @print_trace_dec
    def get_child_at_index(self, idx: int) -> SBValue:
        return self._create_child_at_element_index(idx) or SBValue()

    @print_trace_dec
    def num_children(self, max=UINT32_MAX) -> int:
        return self.num_elements

    @print_trace_dec
    def has_children(self) -> bool:
        return self.num_elements > 0

    @print_trace_dec
    def get_index_of_child(self, name: str) -> Optional[int]:
        try:
            return int(name.lstrip("[").rstrip("]"))
        except:
            return None

    @print_trace_dec
    def get_summary(self, max_children=Opts.MAX_AMOUNT_OF_CHILDREN_IN_SUMMARY, max_str_len=Opts.SUMMARY_STRING_MAX_LENGTH) -> str:
        if not self.check_valid(self.valobj):
            return INVALID_SUMMARY
        return LIST_FORMAT.format(
            type_name=self.typename,
            type_no_template=self.typename.split("<")[0],
            size=self.num_elements,
            children=self.get_children_summary(max_children, max_str_len),
        )


class PagedArray_SyntheticProvider(_ListOfChildren_SyntheticProvider):
    def __init__(self, valobj: SBValue, internal_dict, is_summary=False):
        self.item_type: Optional[SBType] = None
        self.item_size: int = 0
        self.ptr: Optional[SBValue] = None
        self.page_size_shift: int = 0
        self.page_size_mask: int = 0
        self.ptr_cast: Optional[SBValue] = None
        super().__init__(valobj, internal_dict, is_summary)

    def get_ptr(self, obj: SBValue) -> SBValue:
        return obj.GetChildMemberWithName("page_data")

    def get_len(self, obj: SBValue):
        return obj.GetChildMemberWithName("count").GetValueAsUnsigned(0)

    def check_valid(self, obj: SBValue) -> bool:
        page_data = self.get_ptr(obj)
        size = self.get_len(obj)

        if size == 0 and page_data and page_data.TypeIsPointerType():
            return True
        if not is_valid_pointer(page_data):
            return False
        page_pool = obj.GetChildMemberWithName("page_pool")
        if not is_valid_pointer(page_pool):
            return False
        pages_allocated = page_pool.GetChildMemberWithName("pages_allocated").GetValueAsUnsigned(0)
        pages_available = page_pool.GetChildMemberWithName("pages_available").GetValueAsUnsigned(0)
        if pages_allocated < pages_available:
            return False
        try:  # try getting the last element
            index = size - 1
            page_size_shift: int = obj.GetChildMemberWithName("page_size_shift").GetValueAsUnsigned(0)
            page_size_mask: int = obj.GetChildMemberWithName("page_size_mask").GetValueAsUnsigned(0)
            page_index = index >> page_size_shift
            offset = index & page_size_mask
            if page_index > UINT32_MAX or offset > UINT32_MAX:  # PagedArray can't be bigger than this
                return False
            if page_index > pages_allocated:
                return False
            array_type = page_data.GetType().GetPointeeType().GetArrayType(size).GetPointerType()
            ptr_cast = page_data.Cast(array_type)
            last_page = ptr_cast.GetChildAtIndex(page_index)
            if not last_page or not last_page.IsValid():
                return False
            last_val: SBValue = last_page.GetChildAtIndex(offset, eDynamicCanRunTarget, True)
            if not last_val or not last_val.IsValid():
                return False
        except Exception as e:
            print_verbose("EXCEPTION: " + str(e))
            return False
        return True

    def update(self):
        """
        Updates num_elements and ptr
        """
        self.num_elements = self.get_len(self.valobj)
        self.ptr = self.get_ptr(self.valobj)
        if not self.check_valid(self.valobj):
            self.num_elements = 0
            self.ptr = None
        else:
            self.item_type = self.ptr.GetType().GetPointeeType().GetPointeeType() if self.ptr else None
            self.item_size = self.item_type.GetByteSize() if self.item_type else 0
            self.page_size_shift = self.valobj.GetChildMemberWithName("page_size_shift").GetValueAsUnsigned(0)
            self.page_size_mask = self.valobj.GetChildMemberWithName("page_size_mask").GetValueAsUnsigned(0)
            pointer_to_array_type = self.ptr.GetType().GetPointeeType().GetArrayType(self.num_elements).GetPointerType()
            self.ptr_cast = self.ptr.Cast(pointer_to_array_type)

    def _create_child_at_element_index(self, index: int) -> Optional[SBValue]:
        name = "[" + str(index) + "]"
        return self.create_child_at_real_index(index, name)

    def create_child_at_real_index(self, index: int, name: str) -> Optional[SBValue]:
        if index < 0 or index >= self.num_elements or not self.ptr or not self.ptr_cast or not self.item_type:
            return None
        page_index = index >> self.page_size_shift
        offset = index & self.page_size_mask
        page_data: SBValue = self.ptr_cast.GetChildAtIndex(page_index)
        child = page_data.CreateChildAtOffset(name, offset * self.item_size, self.item_type)
        return child


class _ArrayLike_SyntheticProvider(_ListOfChildren_SyntheticProvider):

    @print_trace_dec
    def __init__(self, valobj: SBValue, internal_dict, is_summary=False):
        self.item_type: Optional[SBType] = None
        self.item_size: int = 0
        self.ptr: Optional[SBValue] = None
        super().__init__(valobj, internal_dict, is_summary)

    @print_trace_dec
    def check_valid(self, obj: SBValue):
        num_elements = self.get_len(obj)
        ptr = self.get_ptr(obj)
        if not ptr:
            return False
        item_type = ptr.GetType().GetPointeeType() if ptr else None
        item_size: int = item_type.GetByteSize() if item_type else 0
        if not ptr or not item_type:
            return False
        if num_elements == 0:
            return True
        if not is_valid_pointer(ptr):
            return False
        try:
            ptr_address = ptr.GetValueAsUnsigned()
            if ptr_address == 0:
                return False
            last_val = ptr.CreateValueFromAddress(
                "_tmp_tail", ptr_address + ((num_elements - 1) * item_size), item_type
            )
            if not last_val.IsValid():
                return False
        except Exception as e:
            print_verbose("EXCEPTION: " + str(e))
            return False
        return True

    @print_trace_dec
    def update(self):
        """
        Updates num_elements and ptr
        """
        self.num_elements = self.get_len(self.valobj)
        self.ptr = self.get_ptr(self.valobj)
        if not_null_check(self.ptr) and not (not self.ptr):
            self.item_type = self.ptr.GetType().GetPointeeType()
        self.item_size = self.item_type.GetByteSize() if self.item_type else 0
        if self.item_size == 0 or not self.check_valid(self.valobj):
            self.num_elements = 0
            self.ptr = None

    @print_trace_dec
    def _create_child_at_element_index(self, index: int) -> Optional[SBValue]:
        name = "[" + str(index) + "]"
        return self.create_child_at_real_index(index, name)

    # Helper function for proxy providers.
    @print_trace_dec
    def create_child_at_real_index(self, index: int, name: str) -> Optional[SBValue]:
        if index < 0 or index >= self.num_elements or not self.ptr or not self.item_type:
            return None
        try:
            ptr_address = self.ptr.GetValueAsUnsigned()
            if ptr_address == 0:
                return None
            return self.ptr.CreateValueFromAddress(name, ptr_address + (index * self.item_size), self.item_type)
        except:
            return None


class Vector_SyntheticProvider(_ArrayLike_SyntheticProvider):

    @print_trace_dec
    def __init__(self, valobj: SBValue, internal_dict, is_summary=False):
        super().__init__(valobj, internal_dict, is_summary)

    def get_ptr(self, obj: SBValue) -> SBValue:
        return obj.GetChildMemberWithName("_cowdata").GetChildMemberWithName("_ptr")

    def get_len(self, obj: SBValue):
        return get_cowdata_size(obj.GetChildMemberWithName("_cowdata"))


class LocalVector_SyntheticProvider(_ArrayLike_SyntheticProvider):
    def check_valid(self, obj: SBValue):
        if not super().check_valid(obj):
            return False
        length = self.get_len(obj)
        if length == 0:
            return True
        capacity = obj.GetChildMemberWithName("capacity").GetValueAsUnsigned(0)
        if capacity < length:
            return False
        return True

    def get_ptr(self, obj: SBValue) -> SBValue:
        return obj.GetChildMemberWithName("data")

    def get_len(self, obj: SBValue):
        return obj.GetChildMemberWithName("count").GetValueAsUnsigned(0)


class HashSet_SyntheticProvider(_ArrayLike_SyntheticProvider):
    OLD_HASH_SET_KEYS_NAME: str = "keys"
    OLD_HASH_SET_SIZE_NAME: str = "num_elements"
    hash_set_keys_name: str = "_keys"
    hash_set_size_name: str = "_size"
    
    
    def __init__(self, valobj: SBValue, internal_dict, is_summary=False):
        if valobj.GetChildMemberWithName(self.OLD_HASH_SET_SIZE_NAME).IsValid():
            self.hash_set_keys_name = self.OLD_HASH_SET_KEYS_NAME
            self.hash_set_size_name = self.OLD_HASH_SET_SIZE_NAME
        super().__init__(valobj, internal_dict, is_summary)

    def get_ptr(self, obj: SBValue) -> SBValue:
        return obj.GetChildMemberWithName(self.hash_set_keys_name)

    def get_len(self, obj: SBValue):
        return obj.GetChildMemberWithName(self.hash_set_size_name).GetValueAsUnsigned(0)


def _VMap_Pair_get_keypair_summaries(valobj: SBValue, internal_dict, is_VMap_Summary=False) -> tuple[str, str]:
    key: SBValue = valobj.GetChildMemberWithName("key")
    value: SBValue = valobj.GetChildMemberWithName("value")
    key_summary = GenericShortSummary(key, internal_dict, 0, False, is_VMap_Summary)
    value_summary = GenericShortSummary(value, internal_dict, 0, False, is_VMap_Summary)
    return key_summary, value_summary


def VMap_Pair_SummaryProvider(valobj: SBValue, internal_dict):
    fmt_str = "[{0}]: {1}"
    key: SBValue = valobj.GetChildMemberWithName("key")
    key_template_type = key.GetType() if key else None
    if should_use_key_val_style(key_template_type):
        value: SBValue = valobj.GetChildMemberWithName("value")
        return GenericShortSummary(value, internal_dict)
    return fmt_str.format(*_VMap_Pair_get_keypair_summaries(valobj, internal_dict))

# Pair<K, V>, not part of a map
def Pair_SummaryProvider(valobj: SBValue, internal_dict):
    fmt_str = "({0}, {1})"
    key: SBValue = valobj.GetChildMemberWithName("first")
    value: SBValue = valobj.GetChildMemberWithName("second")
    return fmt_str.format(GenericShortSummary(key, internal_dict), GenericShortSummary(value, internal_dict))


class VMap_SyntheticProvider(_ArrayLike_SyntheticProvider):
    key_val_element_style: bool = Opts.MAP_KEY_VAL_STYLE
    key_template_type: Optional[SBType] = None
    key_val_element_style: bool = False
    ptr_cast: Optional[SBValue] = None
    cached_key_summaries: list[str] = list[str]()
    cached_key_to_idx_map: dict[str, int] = dict[str, int]()
    cache_fetch_max: int = 100
    cache_min: int = 10
    no_cache: bool = False
    def __init__(self, valobj: SBValue, internal_dict, is_summary=False):
        super().__init__(valobj, internal_dict, is_summary)

    def update(self) -> None:
        super().update()
        if self.num_elements == 0:
            return
        self.key_template_type = self.valobj.GetType().GetTemplateArgumentType(0) if self.valobj else None
        self.key_val_element_style = should_use_key_val_style(self.key_template_type)
        pointer_to_array_type = self.ptr.GetType().GetPointeeType().GetArrayType(self.num_elements).GetPointerType() if self.ptr else None
        self.ptr_cast = self.ptr.Cast(pointer_to_array_type) if self.ptr and pointer_to_array_type else None
        self.cached_key_summaries = list[str]()
        self.cached_key_to_idx_map = dict[str, int]()
        self.cache_elements(self.cache_min)

    def get_len(self, obj: SBValue):
        return get_cowdata_size(obj.GetChildMemberWithName("_cowdata"))

    def get_ptr(self, obj: SBValue) -> SBValue:
        return obj.GetChildMemberWithName("_cowdata").GetChildMemberWithName("_ptr")

    def cache_elements(self, size: int):
        if size > self.num_elements:
            size = self.num_elements
        if len(self.cached_key_summaries) >= size or size == 0:
            return
        start = len(self.cached_key_summaries)
        for i in range(start, size):
            child = self.ptr_cast.GetChildAtIndex(i, eDynamicCanRunTarget, True) if self.ptr_cast else None
            if not child or not child.IsValid():
                continue
            # get the key summary
            key: SBValue = child.GetChildMemberWithName("key")
            key_summary = GenericShortSummary(key, self.internal_dict)
            self.cached_key_summaries.append(key_summary)
            self.cached_key_to_idx_map[key_summary] = i

    def _get_child_summary(self, real_index: int) -> str:
        if real_index < 0 or real_index >= self.num_elements or self.valobj.IsValid() == False:
            return INVALID_SUMMARY
        element = self._create_child_at_element_index(real_index)
        if not element:
            return INVALID_SUMMARY
        key, value = _VMap_Pair_get_keypair_summaries(element, self.internal_dict, True)
        if not element or not element.IsValid():
            return INVALID_SUMMARY
        return "[{0}]: {1}".format(key, value)

    def get_key_by_index(self, index: int) -> Optional[str]:
        if index < 0 or index >= self.num_elements:
            return None
        if self.no_cache:
            if not self.ptr_cast:
                return None
            child = self.ptr_cast.GetChildAtIndex(index, eDynamicCanRunTarget, True)
            key: SBValue = child.GetChildMemberWithName("key")
            key_summary = GenericShortSummary(key, self.internal_dict)
            return key_summary
        if index < len(self.cached_key_summaries):
            return self.cached_key_summaries[index]
        # otherwise, start caching
        while len(self.cached_key_summaries) < self.num_elements:
            new_length = len(self.cached_key_summaries) + self.cache_fetch_max
            if new_length > self.num_elements:
                new_length = self.num_elements
            self.cache_elements(new_length)
            if new_length >= index:
                break
        return self.cached_key_summaries[index]

    def _create_child_at_element_index(self, index: int) -> Optional[SBValue]:
        key = (
            self.get_key_by_index(index)
            if hasattr(self, "key_val_element_style") and self.key_val_element_style
            else str(index)
        )
        return self.create_child_at_real_index(index, f"[{key}]")

    def get_index_of_key(self, key: str) -> Optional[int]:
        if self.no_cache:
            for i in range(self.num_elements):
                if not self.ptr_cast:
                    continue
                child = self.ptr_cast.GetChildAtIndex(i, eDynamicCanRunTarget, True)
                key_summary = GenericShortSummary(child.GetChildMemberWithName("key"), self.internal_dict)
                if key_summary == key:
                    return i
            return None

        if key in self.cached_key_to_idx_map:
            return self.cached_key_to_idx_map[key]
        # start caching
        while len(self.cached_key_summaries) < self.num_elements:
            new_length = len(self.cached_key_summaries) + self.cache_fetch_max
            if new_length > self.num_elements:
                new_length = self.num_elements
            self.cache_elements(new_length)
            if key in self.cached_key_to_idx_map:
                return self.cached_key_to_idx_map[key]
        return None

    def get_index_of_child(self, name: str):
        if self.key_val_element_style:
            return self.get_index_of_key(name.lstrip("[").rstrip("]"))
        else:
            return int(name.lstrip("[").rstrip("]"))


class _LinkedListLike_SyntheticProvider(_ListOfChildren_SyntheticProvider):
    def __init__(self, valobj: SBValue, internal_dict, is_summary=False):
        self.cached_elements: list[SBValue] = list[SBValue]()
        super().__init__(valobj, internal_dict, is_summary)

    def _create_synthetic_child(self, element: SBValue, index) -> SBValue:
        raise Exception("Not implemented")

    def get_tail(self, obj: SBValue) -> SBValue:
        raise Exception("Not implemented")

    def get_list_element_next(self, element: SBValue) -> SBValue:
        raise Exception("Not implemented")

    def get_list_element_prev(self, element: SBValue) -> SBValue:
        raise Exception("Not implemented")

    def get_list_element_data(self, element: SBValue) -> SBValue:
        raise Exception("Not implemented")

    @hashmap_trace
    def _cache_elements(self, size: int):
        if self.num_elements == 0 or size == 0:
            return
        if size > self.num_elements:
            size = self.num_elements
        start = 0
        element: Optional[SBValue] = None
        if len(self.cached_elements) == 0:
            el = self.get_ptr(self.valobj)
            if not_null_check(el) and not (not el):
                element = el
                self.cached_elements.append(element)
        else:
            start = len(self.cached_elements) - 1
            if start > size:
                return
            element = self.cached_elements[start]
            
        for _ in range(start + 1, size):
            element = self.get_list_element_next(element) if element else None
            if not element:
                break
            if element.GetValueAsUnsigned() == 0:
                break
            self.cached_elements.append(element)

    @hashmap_trace
    def check_valid(self, obj: SBValue) -> bool:
        if not not_null_check(obj):
            print_trace("obj is not valid")
            return False
        size = self.get_len(obj)
        if size > 0:
            # check if head_element is valid
            head_element: SBValue = self.get_ptr(obj)
            if not is_valid_pointer(head_element):
                print_trace("head_element is not valid")
                return False
            # check if head_element->prev() is nullptr (it should be if the size is > 0)
            prev: SBValue = self.get_list_element_prev(head_element)
            if not pointer_exists_and_is_null(prev):
                print_trace("head_element->prev is not nullptr")
                return False
            # check if tail_element is valid
            tail_element: SBValue = self.get_tail(obj)
            if not is_valid_pointer(tail_element):
                print_trace("tail_element is not valid")
                return False
            # check if tail_element->next() is nullptr (it should be if the size is > 0)
            next: SBValue = self.get_list_element_next(tail_element)
            if not pointer_exists_and_is_null(next):
                print_trace("tail_element->next is not nullptr")
                return False
            if size >= 2:
                # check if head_element->next() is valid
                next = self.get_list_element_next(head_element)
                if not is_valid_pointer(next):
                    print_trace("head_element->next is not valid")
                    return False
                # check if tail_element->prev() is valid
                prev = self.get_list_element_prev(self.get_tail(obj))
                if not is_valid_pointer(prev):
                    print_trace("tail_element->prev is not valid")
                    return False
        return True

    @hashmap_trace
    def update(self):
        if self.cached_elements is None:
            self.cached_elements = list[SBValue]()
        self.num_elements = self.get_len(self.valobj)
        if self.check_valid(self.valobj) == False:
            self.num_elements = 0
        self.cached_elements.clear()
        if self.no_cache or self.num_elements == 0:
            return
        self._cache_elements(self.cache_min)

    @hashmap_trace
    def _get_uncached_element_at_index(self, index: int) -> Optional[SBValue]:
        if index < 0 or index >= self.num_elements or self.valobj.IsValid() == False:
            return None
        element = self.get_ptr(self.valobj)
        for _ in range(index):
            element = self.get_list_element_next(element) if element else None
            if not element:
                break
        return element

    @hashmap_trace
    def _create_child_at_element_index(self, index: int) -> Optional[SBValue]:
        if index < 0 or index >= self.num_elements or self.valobj.IsValid() == False:
            return None

        element: Optional[SBValue] = None
        if self.no_cache or index >= self.cache_fetch_max:
            element = self._get_uncached_element_at_index(index) if self.valobj else None
        else:
            if index >= len(self.cached_elements):
                self._cache_elements(len(self.cached_elements) + self.cache_fetch_max)
            element = self.cached_elements[index]
        if not element:
            return None
        return self._create_synthetic_child(element, index)


class List_SyntheticProvider(_LinkedListLike_SyntheticProvider):
    def __init__(self, valobj: SBValue, internal_dict, is_summary=False):
        super().__init__(valobj, internal_dict, is_summary)

    # overrides _VectorLike_SyntheticProvider
    def get_len(self, obj: SBValue):
        if not obj.IsValid():
            return 0
        _data: SBValue = obj.GetChildMemberWithName("_data")
        if not is_valid_pointer(_data):
            return 0
        size_cache: SBValue = _data.GetChildMemberWithName("size_cache")
        if not not_null_check(size_cache):
            return 0
        return size_cache.GetValueAsUnsigned()

    def get_ptr(self, obj: SBValue) -> SBValue:
        return obj.GetChildMemberWithName("_data").GetChildMemberWithName("first")

    def get_tail(self, obj: SBValue) -> SBValue:
        return obj.GetChildMemberWithName("_data").GetChildMemberWithName("last")

    def get_list_element_next(self, element: SBValue) -> SBValue:
        return element.GetChildMemberWithName("next_ptr")

    def get_list_element_prev(self, element: SBValue) -> SBValue:
        return element.GetChildMemberWithName("prev_ptr")

    def get_list_element_data(self, element: SBValue) -> SBValue:
        return element.GetChildMemberWithName("value")

    def _create_synthetic_child(self, element: SBValue, index):
        value: SBValue = element.GetChildMemberWithName("value")
        offset = get_offset_of_object_member(element, "value")
        if offset < 0:
            return SBValue()
        return element.CreateChildAtOffset("[{0}]".format(str(index)), offset, value.GetType())


class HashMap_SyntheticProvider(_LinkedListLike_SyntheticProvider):
    key_val_element_style: bool = Opts.MAP_KEY_VAL_STYLE
    cached_elements: list[SBValue] = list[SBValue]()
    cached_key_to_idx_map: dict[str, int] = dict[str, int]()
    cached_idx_to_key_map: dict[int, str] = dict[int, str]()
    key_template_type: Optional[SBType] = None
    num_elements: int = 0
    no_cache: bool = False
    cached_skip_length: int = -1
    
    OLD_HASH_MAP_SIZE_NAME: str = "num_elements"
    OLD_HASH_MAP_HEAD_ELEMENT_NAME: str = "head_element"
    OLD_HASH_MAP_TAIL_ELEMENT_NAME: str = "tail_element"
    hash_map_size_name: str = "_size"
    hash_map_head_element_name: str = "_head_element"
    hash_map_tail_element_name: str = "_tail_element"
    
    @hashmap_trace
    def __init__(self, valobj: SBValue, internal_dict, is_summary=False):
        if valobj.GetChildMemberWithName(self.OLD_HASH_MAP_SIZE_NAME).IsValid():
            self.hash_map_size_name = self.OLD_HASH_MAP_SIZE_NAME
            self.hash_map_head_element_name = self.OLD_HASH_MAP_HEAD_ELEMENT_NAME
            self.hash_map_tail_element_name = self.OLD_HASH_MAP_TAIL_ELEMENT_NAME
        super().__init__(valobj, internal_dict, is_summary)

    @hashmap_trace
    def update(self) -> None:
        self.num_elements = self.get_len(self.valobj)
        is_valid = self.check_valid(self.valobj)
        if not is_valid:
            self.num_elements = 0
        self.cached_elements = list[SBValue]()
        self.cached_key_to_idx_map = dict[str, int]()
        self.cached_idx_to_key_map = dict[int, str]()
        self.key_val_element_style = False
        self.key_template_type = None
        if self.num_elements != 0:
            self.key_template_type = self.valobj.GetType().GetTemplateArgumentType(0) if is_valid else None
            self.key_val_element_style = should_use_key_val_style(self.key_template_type)
        if not self.no_cache:
            self._cache_elements(self.cache_min)

    @hashmap_trace
    def get_len(self, obj: SBValue):
        return obj.GetChildMemberWithName(self.hash_map_size_name).GetValueAsUnsigned()

    @hashmap_trace
    def get_ptr(self, obj: SBValue) -> SBValue:
        return obj.GetChildMemberWithName(self.hash_map_head_element_name)

    @hashmap_trace
    def get_tail(self, obj: SBValue) -> SBValue:
        return obj.GetChildMemberWithName(self.hash_map_tail_element_name)

    @hashmap_trace
    def get_list_element_next(self, element: SBValue) -> SBValue:
        return element.GetChildMemberWithName("next")

    @hashmap_trace
    def get_list_element_prev(self, element: SBValue) -> SBValue:
        return element.GetChildMemberWithName("prev")

    @hashmap_trace
    def get_list_element_data(self, element: SBValue) -> SBValue:
        return element.GetChildMemberWithName("data")

    @hashmap_trace
    def get_list_element_key(self, element: SBValue) -> SBValue:
        return self.get_list_element_data(element).GetChildMemberWithName("key")

    @hashmap_trace
    def get_list_element_keyvalue(self, element: SBValue) -> SBValue:
        return self.get_list_element_data(element).GetChildMemberWithName("value")

    @hashmap_trace
    def get_index_of_child(self, name: str):
        if self.key_val_element_style:
            return self.get_index_of_key(name.lstrip("[").rstrip("]"))
        else:
            return int(name.lstrip("[").rstrip("]"))

    @hashmap_trace
    def get_index_of_key(self, key: str):
        if key in self.cached_key_to_idx_map and self.cached_key_to_idx_map[key] is not None:
            return self.cached_key_to_idx_map[key]
        while len(self.cached_elements) < self.num_elements:  # type: ignore
            new_length = len(self.cached_elements) + self.cache_fetch_max
            if new_length > self.num_elements:
                new_length = self.num_elements
            self._cache_elements(new_length)
            idx = self.cached_key_to_idx_map[key]
            if idx is not None:  # type: ignore
                return idx
        return None

    @hashmap_trace
    @wrap_in_try_except_ret_error_summary
    def _get_child_summary(self, real_index: int) -> str:
        if real_index < 0 or real_index >= self.num_elements or not self.valobj or self.valobj.IsValid() == False:
            return INVALID_SUMMARY
        keyval_synth_val = self._create_child_at_element_index(real_index)
        if not not_null_check(keyval_synth_val) or not keyval_synth_val:
            return INVALID_SUMMARY
        keyval_data = keyval_synth_val.GetNonSyntheticValue()
        # both RBMap and HashMap use KeyValue<K, V> for the data member of their elements
        key = keyval_data.GetChildMemberWithName("key")
        value = keyval_data.GetChildMemberWithName("value")
        key_summary = GenericShortSummary(key, self.internal_dict)
        value_summary = GenericShortSummary(value, self.internal_dict)
        return "[{0}]: {1}".format(key_summary, value_summary)
    
    def get_offset_of_element_data(self, element: SBValue) -> int:
        if self.cached_skip_length >= 0:
            return self.cached_skip_length
        data = self.get_list_element_data(element)
        next_addr = element.GetChildMemberWithName("next").GetAddress()
        data_addr = data.GetAddress()
        self.cached_skip_length = data_addr.GetOffset() - next_addr.GetOffset()
        return self.cached_skip_length

    @hashmap_trace
    def _cache_elements(self, size: int):
        if self.num_elements == 0 or size == 0:
            return
        if size > self.num_elements:
            size = self.num_elements
        start = 0
        element: SBValue
        if self.cached_elements is None:
            self.cached_elements = list[SBValue]()
        if len(self.cached_elements) == 0:
            element = self.get_ptr(self.valobj)
            if not not_null_check(element):
                return
            self.cached_elements.append(element)
        else:
            start = len(self.cached_elements) - 1
            if start > size:
                return
            element = self.cached_elements[start]
        if self.key_val_element_style:
            key = self.get_list_element_key(element)
            keySummary = GenericShortSummary(key, self.internal_dict, 0, False, False)
            self.cached_key_to_idx_map[keySummary] = start
            self.cached_idx_to_key_map[start] = keySummary
        for _ in range(start + 1, size):
            element = self.get_list_element_next(element)
            if not element or element.GetValueAsUnsigned() == 0:
                break
            self.cached_elements.append(element)
            if self.key_val_element_style:
                key = self.get_list_element_key(element)
                keySummary = GenericShortSummary(key, self.internal_dict, 0, False, False)
                self.cached_key_to_idx_map[keySummary] = len(self.cached_elements) - 1
                self.cached_idx_to_key_map[len(self.cached_elements) - 1] = keySummary

    @hashmap_trace
    def _create_synthetic_child(self, element: SBValue, index):
        if not element or not element.IsValid():
            print_trace("HashMap_SyntheticProvider._create_synthetic_child(): element is None or invalid")
            return SBValue()
        if self.key_val_element_style:
            keyname = ""
            if index in self.cached_idx_to_key_map:
                keyname = self.cached_idx_to_key_map[index]
            else:
                key = self.get_list_element_key(element)
                keyname = GenericShortSummary(key, self.internal_dict, 0, False, False)
        else:
            keyname = str(index)
        if keyname not in self.cached_key_to_idx_map:
            self.cached_key_to_idx_map[keyname] = index
        if index not in self.cached_idx_to_key_map:
            self.cached_idx_to_key_map[index] = keyname
        offset = self.get_offset_of_element_data(element)
        hme_data_type = self.get_list_element_data(element).GetType()
        value = element.CreateChildAtOffset("[{0}]".format(keyname), offset, hme_data_type)
        return value


class RBMap_SyntheticProvider(HashMap_SyntheticProvider):
    def get_len(self, obj: SBValue):
        return obj.GetChildMemberWithName("_data").GetChildMemberWithName("size_cache").GetValueAsUnsigned(0)

    def get_ptr(self, obj: SBValue) -> SBValue:
        return obj.EvaluateExpression("front()").GetNonSyntheticValue()

    def get_tail(self, obj: SBValue) -> SBValue:
        return obj.EvaluateExpression("back()").GetNonSyntheticValue()
    
    def get_offset_of_element_data(self, element: SBValue) -> int:
        if self.cached_skip_length >= 0:
            return self.cached_skip_length
        data = self.get_list_element_data(element)
        data_addr = data.GetAddress()
        right_addr = element.GetChildMemberWithName("color").GetAddress()
        self.cached_skip_length = data_addr.GetOffset() - right_addr.GetOffset()
        return self.cached_skip_length

    def get_list_element_next(self, element: SBValue) -> SBValue:
        return element.GetChildMemberWithName("_next")

    def get_list_element_prev(self, element: SBValue) -> SBValue:
        return element.GetChildMemberWithName("_prev")

    def get_list_element_data(self, element: SBValue) -> SBValue:
        return element.GetChildMemberWithName("_data")

    def check_valid(self, obj: SBValue) -> bool:
        size = self.get_len(obj)
        if size > 0:
            # check if head_element is valid
            head_element: SBValue = self.get_ptr(obj)
            if not is_valid_pointer(head_element):
                return False
            prev = self.get_list_element_prev(head_element)
            if not pointer_exists_and_is_null(prev):
                return False
            if size >= 2:
                # check if head_element->next() is valid
                next: SBValue = self.get_list_element_next(head_element)
                if not is_valid_pointer(next):
                    return False
        return True


class _Proxy_SyntheticProvider(GodotSynthProvider):
    def __init__(self, valobj, internal_dict, is_summary=False):
        super().__init__(valobj, internal_dict, is_summary)
        self.synth_proxy: Optional[_ListOfChildren_SyntheticProvider] = None
        self.update()

    def update(self) -> None:
        """
        set the self.synth_proxy value here
        """
        raise Exception("Not implemented")

    def check_valid(self, obj: SBValue) -> bool:
        if self.synth_proxy is None:
            return False
        ret = self.synth_proxy.check_valid(self.synth_proxy.valobj)
        return ret

    def get_summary(self, max_children=Opts.MAX_AMOUNT_OF_CHILDREN_IN_SUMMARY, max_str_len=Opts.SUMMARY_STRING_MAX_LENGTH):
        if self.synth_proxy is None:
            print_trace("synth_proxy is None")
            self.update()
        if self.synth_proxy is None:
            return INVALID_SUMMARY
        if not self.check_valid(self.valobj):
            return INVALID_SUMMARY
        size = self.synth_proxy.num_elements
        children_summary = self.synth_proxy.get_children_summary(max_children, max_str_len)
        type_name = get_unqual_type_name(self.valobj.GetType())
        return LIST_FORMAT.format(
            type_name=type_name,
            type_no_template=type_name.split("<")[0],
            size=size,
            children=children_summary,
        )
    def num_children(self, max=UINT32_MAX):
        if self.synth_proxy:
            return self.synth_proxy.num_children(max)
        return 0

    def has_children(self):
        if self.synth_proxy:
            return self.synth_proxy.has_children()
        return False

    def get_index_of_child(self, name: str):
        if self.synth_proxy:
            return self.synth_proxy.get_child_index(name)
        return None

    def get_child_at_index(self, idx: int) -> SBValue:
        if self.synth_proxy:
            return self.synth_proxy.get_child_at_index(idx)
        return SBValue()


# just a proxy for Vector_SyntheticProvider
class Array_SyntheticProvider(_Proxy_SyntheticProvider):
    def update(self):
        self.synth_proxy = None
        _p: SBValue = self.valobj.GetChildMemberWithName("_p")
        if is_valid_pointer(_p):
            self.synth_proxy = get_synth_provider_for_object(
                Vector_SyntheticProvider,
                _p.GetChildMemberWithName("array"),
                self.internal_dict,
                self.is_summary,
            )


class Dictionary_SyntheticProvider(_Proxy_SyntheticProvider):
    @wrap_in_try_except_ret_none
    def update(self):
        self.synth_proxy = None
        _p: SBValue = self.valobj.GetChildMemberWithName("_p")
        if is_valid_pointer(_p):
            self.synth_proxy = get_synth_provider_for_object(
                HashMap_SyntheticProvider,
                _p.GetChildMemberWithName("variant_map"),
                self.internal_dict,
                self.is_summary,
            )


class VSet_SyntheticProvider(_Proxy_SyntheticProvider):
    def update(self):
        self.synth_proxy = None
        _data: SBValue = self.valobj.GetChildMemberWithName("_data")
        if _data.IsValid():
            self.synth_proxy = get_synth_provider_for_object(
                Vector_SyntheticProvider, _data, self.internal_dict, self.is_summary
            )


class RingBuffer_SyntheticProvider(_Proxy_SyntheticProvider):
    read_pos: int = 0
    write_pos: int = 0
    size_mask: int = 0
    
    def update(self) -> None:
        self.synth_proxy: Optional[Vector_SyntheticProvider] = None
        self.read_pos = 0
        self.write_pos = 0
        self.size_mask = 0
        _data: SBValue = self.valobj.GetChildMemberWithName("data")
        if _data.IsValid():
            self.synth_proxy = get_synth_provider_for_object(
                Vector_SyntheticProvider, _data, self.internal_dict, self.is_summary
            )
            self.size_mask = self.valobj.GetChildMemberWithName("size_mask").GetValueAsSigned()
            self.read_pos = self.valobj.GetChildMemberWithName("read_pos").GetValueAsSigned() & self.size_mask
            self.write_pos = self.valobj.GetChildMemberWithName("write_pos").GetValueAsSigned() & self.size_mask

    def get_summary(self, max_children=Opts.MAX_AMOUNT_OF_CHILDREN_IN_SUMMARY, max_str_len=Opts.SUMMARY_STRING_MAX_LENGTH):
        if not self.check_valid(self.valobj):
            return INVALID_SUMMARY
        children_summary = ""
        size = 0
        if self.synth_proxy and self.synth_proxy.num_elements > 0:
            size = self.synth_proxy.num_elements
            read_pos_summary = "<read_pos:{0}>".format(self.read_pos)
            write_pos_summary = "<write_pos:{0}>".format(self.write_pos)
            proxy_children_sum = self.synth_proxy.get_children_summary(max_children, max_str_len)
            children_summary = f"{read_pos_summary} {write_pos_summary} {proxy_children_sum}"
        return LIST_FORMAT.format(
            type_name=get_unqual_type_name(self.valobj.GetType()),
            type_no_template="RingBuffer",
            size=size,
            children=children_summary,
        )

    def num_children(self, max=UINT32_MAX):
        if self.synth_proxy:
            return self.synth_proxy.num_children() + 2
        return 0

    def has_children(self):
        if self.synth_proxy:
            return self.synth_proxy.has_children()
        return False

    def get_index_of_child(self, name: str):
        if self.synth_proxy:
            if name.startswith("[read_pos"):
                return 0
            elif name.startswith("[write_pos"):
                return 1
            return self.synth_proxy.get_child_index(name)
        return None

    def get_child_at_index(self, idx: int) -> SBValue:
        value: Optional[SBValue] = None
        if self.synth_proxy:
            if idx == 0 or idx == 1:
                pos_name = "read_pos" if idx == 0 else "write_pos"
                pos_val = self.read_pos if idx == 0 else self.write_pos
                synth_name = f"[{pos_name} <{pos_val}>]"
                if pos_val < 0 or pos_val >= self.synth_proxy.num_elements:
                    return self.valobj.CreateValueFromData(
                        synth_name,
                        SBData.CreateDataFromInt(0),
                        self.valobj.target.GetBasicType(eBasicTypeNullPtr),
                    )
                value = self.synth_proxy.create_child_at_real_index(pos_val, synth_name)
            else:
                value = self.synth_proxy.get_child_at_index(idx - 2)
        else:
            print_trace("RingBuffer_SyntheticProvider.get_child_at_index(): synth_proxy is None")
            return SBValue()
        if not value:
            print_trace("RingBuffer_SyntheticProvider.get_child_at_index(): value is None")
            return SBValue()
        return value
