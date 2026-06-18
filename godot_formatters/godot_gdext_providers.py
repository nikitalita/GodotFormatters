# fmt: off
from types import TracebackType
from typing import Callable, final, Optional

from lldb import SBValue  # pyright: ignore[reportMissingModuleSource]
# fmt: on
from enum import Enum
import weakref
from typing import TypeVar, Generic, List

from godot_formatters.options import Opts, INVALID_SUMMARY, NIL_SUMMARY
from godot_formatters.utils import GodotSummaryOptions, print_verbose
from godot_formatters.godot_providers import GenericShortSummary, get_synth_provider_for_object, GodotSynthProvider

UINT32_MAX = 4294967295
INT32_MAX = 2147483647

get_godot_synthetic_provider_for_type: Callable[[str], Optional[type]]
get_godot_summary_provider_for_type: Callable[[str], Optional[type]]

T = TypeVar("T", bound=GodotSynthProvider)

def get_godot_type_name(valobj: SBValue) -> str:
    rs_type_name = valobj.GetType().GetName()
    # check if it's a template type first
    if '<' in valobj.GetType().GetName():
        rs_type_name = rs_type_name.split("<", 1)[0]
    return get_godot_type_name_from_str(rs_type_name)

def get_godot_type_name_from_str(type_name: str) -> str:
    type_name = type_name.split(sep="::")[-1]
    if (type_name == "GString"):
        type_name = "String"
    elif (type_name == "Rid"):
        type_name = "RID"
    elif (type_name == "Aabb"):
        type_name = "AABB"
    elif type_name == "VarDictionary":
        type_name = "Dictionary"
    type_name = "::" + type_name
    return type_name

def get_real_valobj_from_opaque_member(valobj: SBValue) -> Optional[SBValue]:

    target = valobj.GetTarget()
    type_name = get_godot_type_name(valobj)
    variant_cpptype = target.FindFirstType(type_name)
    if not variant_cpptype or not variant_cpptype.IsValid():
        raise Exception(f"ERROR: Variant type is not valid for {type_name}")
    opaque = valobj.GetChildAtIndex(0)
    if not opaque or not opaque.IsValid():
        raise Exception("ERROR: Opaque is not valid")

    opaque_storage = opaque.GetChildMemberWithName("storage")
    if not opaque_storage or not opaque_storage.IsValid():
        raise Exception("ERROR: Opaque storage is not valid")

    real_valobj = opaque_storage.Cast(type=variant_cpptype)
    return real_valobj


class GDExtGenericSynthProvider(GodotSynthProvider):
    synth_provider: GodotSynthProvider

    def __init__(
        self,
        valobj: SBValue,
        internal_dict,
        is_summary=False
    ):
        super().__init__(valobj, internal_dict, is_summary)
        self.update()

    def update(self):
        self.type_name = get_godot_type_name(self.valobj)
        self.real_valobj = get_real_valobj_from_opaque_member(self.valobj)
        if self.real_valobj is None or not self.real_valobj.IsValid():
            print_verbose(f"Real valobj is not valid for {self.type_name}")
            return None

        self.synth_provider_type = get_godot_synthetic_provider_for_type(self.type_name)
        if self.synth_provider_type is None:
            print_verbose(f"Synth provider type is not valid for {self.type_name}")
            return None
        self.synth_provider = get_synth_provider_for_object(cls=self.synth_provider_type, valobj=self.real_valobj, internal_dict=self.internal_dict, is_summary=self.is_summary)

    def get_summary(self, _options: GodotSummaryOptions):
        return self.synth_provider.get_summary(_options)

    def num_children(self, max=UINT32_MAX):
        return self.synth_provider.num_children(max)

    def has_children(self):
        return self.synth_provider.has_children()

    def get_index_of_child(self, name: str):
        return self.synth_provider.get_index_of_child(name)

    def get_child_at_index(self, idx: int) -> SBValue:
        return self.synth_provider.get_child_at_index(idx)


def get_real_valobj_from_raw_gd(valobj: SBValue) -> SBValue:
    target = valobj.GetTarget()
    type_name = get_godot_type_name_from_str(valobj.GetType().GetTemplateArgumentType(0).GetName())
    variant_cpptype = target.FindFirstType(type_name)
    if not variant_cpptype or not variant_cpptype.IsValid():
        raise Exception(f"ERROR: Variant type is not valid for {type_name}")
    raw = valobj.GetChildAtIndex(0)
    if not raw or not raw.IsValid():
        raise Exception("ERROR: raw is not valid")

    obj = raw.GetChildAtIndex(0)
    if not obj or not obj.IsValid():
        raise Exception("ERROR: obj is not valid")
    
    obj_pointer = obj.GetChildAtIndex(0)
    if not obj_pointer or not obj_pointer.IsValid():
        raise Exception("ERROR: Obj pointer is not valid")
    val: int = obj_pointer.GetValueAsUnsigned()
    if val == 0:
        raise Exception("ERROR: Obj pointer is not valid")
    return obj_pointer.Cast(variant_cpptype)

class GDExtGDObjectSynthProvider(GodotSynthProvider):
    real_valobj: SBValue

    def __init__(
        self,
        valobj: SBValue,
        internal_dict,
        is_summary=False
    ):
        super().__init__(valobj, internal_dict, is_summary)
        self.update()

    def update(self):
        self.real_valobj = get_real_valobj_from_raw_gd(self.valobj)

    def get_summary(self, _options: GodotSummaryOptions):
        return GenericShortSummary(self.real_valobj, self.internal_dict, _options, False, False)

    def num_children(self, max=UINT32_MAX):
        return 1

    def has_children(self):
        return True

    def get_index_of_child(self, name: str):
        return 0

    def get_child_at_index(self, idx: int) -> SBValue:
        return self.real_valobj


class GDExtBaseGDObjectSynthProvider(GDExtGDObjectSynthProvider):
    # @override
    def update(self):
        obj = self.valobj.GetChildAtIndex(0)
        if not obj or not obj.IsValid():
            raise Exception("ERROR: raw is not valid")

        value = obj.GetChildAtIndex(0)
        if not value or not value.IsValid():
            raise Exception("ERROR: obj is not valid")
        self.real_valobj = get_real_valobj_from_raw_gd(value)


def GDExtRIDSummaryProvider(valobj: SBValue, internal_dict, _options: GodotSummaryOptions):
    # TODO: support non-clang enums
    child = valobj.GetChildAtIndex(0).GetChildAtIndex(0).GetChildAtIndex(0).GetChildAtIndex(0).GetChildAtIndex(0).GetChildAtIndex(0)
    value = 0
    if child and child.IsValid():
        value = child.GetValueAsUnsigned()
    if value == 0:
        return "<RID=INVALID>"
    return "<RID=" + str(value) + ">"

def GDExtGenericSummaryProvider(valobj: SBValue, internal_dict, _options: GodotSummaryOptions):
    type_name = get_godot_type_name(valobj)
    summary_provider = get_godot_summary_provider_for_type(type_name)
    if "RID" in type_name:
        return GDExtRIDSummaryProvider(valobj, internal_dict, _options)
    if summary_provider is None:
        raise Exception(f"ERROR: Summary provider for {valobj.GetType().GetName()} is not valid ({type_name})")
    return summary_provider(valobj, internal_dict, _options)

def GDExtOpaqueSummaryProvider(valobj: SBValue, internal_dict, _options: GodotSummaryOptions):
    real_valobj = get_real_valobj_from_opaque_member(valobj)
    if real_valobj is None or not real_valobj.IsValid():
        raise Exception(f"ERROR: opaque.container for {valobj.GetType().GetName()} is not valid ({get_godot_type_name(valobj)})")
    return GDExtGenericSummaryProvider(real_valobj, internal_dict, _options)
