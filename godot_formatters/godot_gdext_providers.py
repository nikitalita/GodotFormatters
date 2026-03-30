# fmt: off
from types import TracebackType
from typing import Callable, Generator, final, Optional

from lldb import (SBError, SBValue, SBTarget, SBType)
# fmt: on
from enum import Enum
import hashlib
import weakref
from typing import TypeVar, Generic, List

from godot_formatters.options import Opts, INVALID_SUMMARY, NIL_SUMMARY
from godot_formatters.utils import print_verbose
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

    def get_summary(self, max_children=UINT32_MAX, max_str_len=Opts.SUMMARY_STRING_MAX_LENGTH):
        return self.synth_provider.get_summary(max_children, max_str_len)

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
        raise Exception("ERROR: Obj pointer is not valid (valobj: " + str(valobj) + ")")
    val: int = obj_pointer.GetValueAsUnsigned()
    if val == 0:
        raise Exception(
            "ERROR: Obj pointer value is not valid (valobj: " + str(valobj) + ")"
        )
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

    def get_summary(self, max_children=UINT32_MAX, max_str_len=Opts.SUMMARY_STRING_MAX_LENGTH):
        return GenericShortSummary(self.real_valobj, self.internal_dict, max_str_len, False, False)

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


def GDExtRIDSummaryProvider(valobj: SBValue, internal_dict):
    # TODO: support non-clang enums
    child = valobj.GetChildAtIndex(0).GetChildAtIndex(0).GetChildAtIndex(0).GetChildAtIndex(0).GetChildAtIndex(0).GetChildAtIndex(0)
    return "<RID=" + str(child.GetValueAsUnsigned()) + ">"

def GDExtGenericSummaryProvider(valobj: SBValue, internal_dict):
    type_name = get_godot_type_name(valobj)
    summary_provider = get_godot_summary_provider_for_type(type_name)
    if "RID" in type_name:
        return GDExtRIDSummaryProvider(valobj, internal_dict)
    if summary_provider is None:
        raise Exception(f"ERROR: Summary provider for {valobj.GetType().GetName()} is not valid ({type_name})")
    return summary_provider(valobj, internal_dict)

def GDExtOpaqueSummaryProvider(valobj: SBValue, internal_dict):
    real_valobj = get_real_valobj_from_opaque_member(valobj)
    if real_valobj is None or not real_valobj.IsValid():
        raise Exception(f"ERROR: opaque.container for {valobj.GetType().GetName()} is not valid ({get_godot_type_name(valobj)})")
    return GDExtGenericSummaryProvider(real_valobj, internal_dict)


_BASE58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"

def _to_byte_list(valobj: Optional[SBValue]) -> Optional[List[int]]:
    if valobj is None or not valobj.IsValid():
        return None
    data = valobj.GetData()
    if not data or data.size == 0:
        return None
    result: List[int] = []
    error = SBError()
    for i in range(data.size):
        result.append(data.GetUnsignedInt8(error, i))
        if error.Fail():
            return None
    return result


def _get_newtype_first_field(valobj: Optional[SBValue]) -> Optional[SBValue]:
    if valobj is None or not valobj.IsValid():
        return None

    for name in ("0", "__0", "value", "inner"):
        child = valobj.GetChildMemberWithName(name)
        if child and child.IsValid():
            return child

    for i in range(valobj.GetNumChildren()):
        child = valobj.GetChildAtIndex(i)
        if child and child.IsValid():
            return child
    return None


def _extract_fixed_bytes(valobj: Optional[SBValue], expected_size: int) -> Optional[List[int]]:
    if valobj is None or not valobj.IsValid():
        return None

    # try progressively unwrapping tuple/newtype wrappers.
    candidate = valobj
    best_prefix: Optional[List[int]] = None
    for _ in range(5):
        byte_list = _to_byte_list(candidate)
        if byte_list is not None:
            if len(byte_list) == expected_size:
                return byte_list
            if len(byte_list) > expected_size and best_prefix is None:
                best_prefix = byte_list[:expected_size]
        candidate = _get_newtype_first_field(candidate)
        if candidate is None:
            break
    return best_prefix


def _base58_encode(payload: bytes) -> str:
    if len(payload) == 0:
        return ""

    zeros = 0
    for b in payload:
        if b == 0:
            zeros += 1
        else:
            break

    num = int.from_bytes(payload, byteorder="big", signed=False)
    encoded = ""
    while num > 0:
        num, remainder = divmod(num, 58)
        encoded = _BASE58_ALPHABET[remainder] + encoded
    return ("1" * zeros) + encoded


def _base58check_encode(payload: bytes) -> str:
    checksum = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
    return _base58_encode(payload + checksum)


def _normalize_summary(
    valobj: Optional[SBValue],
    internal_dict,
    fallback_provider: Optional[Callable[[SBValue, object], str]] = None,
) -> str:
    if valobj is None or not valobj.IsValid():
        return INVALID_SUMMARY
    summary = valobj.GetSummary()
    if summary is not None and summary != "":
        return summary
    if fallback_provider is not None:
        return fallback_provider(valobj, internal_dict)
    return INVALID_SUMMARY


def _extract_vec_children(valobj: Optional[SBValue]) -> List[SBValue]:
    if valobj is None or not valobj.IsValid():
        return []
    # if not synthetic, instantiate a StdVecSyntheticProvider and get the children from that
    if not valobj.IsSynthetic():
        std_vec_provider = StdVecSyntheticProvider(valobj, {})
        count = std_vec_provider.num_children()
        if count == 0:
            print("NO CHILDREN for history ref")
            return []
        children: List[SBValue] = []
        for i in range(count):
            child = std_vec_provider.get_child_at_index(i)
            children.append(child)
        return children

    count = valobj.GetNumChildren()
    if count == 0:
        print("NO CHILDREN for history ref")
        return []

    children: List[SBValue] = []
    indexed_children: List[SBValue] = []
    # print(f"COUNT: {count} for history ref")
    for i in range(count):
        child = valobj.GetChildAtIndex(i)
        # print(f"CHILD: {child}")
        if child is None or not child.IsValid():
            print(f"INVALID CHILD FOR HISTORY REF AT INDEX {i}")
            continue
        children.append(child)
        child_name = child.GetName() or ""
        # Rust synthetic Vec children are usually indexed entries, while
        # non-synthetic children are internals like "buf"/"len"/"cap".
        if (child_name.startswith("[") and child_name.endswith("]")) or child_name.isdigit():
            indexed_children.append(child)
    if len(indexed_children) > 0:
        return indexed_children
    if len(children) > 0:
        print("NO children at all!!!!!")
        return []
    return children


def RustDocumentIdSummaryProvider(valobj: SBValue, internal_dict):
    raw_bytes = _extract_fixed_bytes(valobj, 16)
    if raw_bytes is None or len(raw_bytes) != 16:
        return INVALID_SUMMARY
    return _base58check_encode(bytes(raw_bytes))


def RustChangeHashSummaryProvider(valobj: SBValue, internal_dict):
    raw_bytes = _extract_fixed_bytes(valobj, 32)
    if raw_bytes is None or len(raw_bytes) != 32:
        return INVALID_SUMMARY
    return bytes(raw_bytes).hex()


def RustHistoryRefSummaryProvider(valobj: SBValue, internal_dict):
    if valobj is None or not valobj.IsValid():
        print("INVALID HISTORY REF, NOT A VALID OBJECT")
        return INVALID_SUMMARY

    branch = valobj.GetChildMemberWithName("branch")
    heads = valobj.GetChildMemberWithName("heads")
    if branch is None or not branch.IsValid() or heads is None or not heads.IsValid():
        print("INVALID HISTORY REF, BRANCH OR HEADS ARE NOT VALID")
        return INVALID_SUMMARY

    branch_summary = _normalize_summary(branch, internal_dict, RustDocumentIdSummaryProvider)
    if branch_summary == INVALID_SUMMARY:
        print("INVALID HISTORY REF, BRANCH SUMMARY IS INVALID")
        return INVALID_SUMMARY

    head_children = _extract_vec_children(heads)
    if len(head_children) == 0:
        print("INVALID HISTORY REF, NO HEADS")
        # HistoryRef::Display returns fmt::Error when heads are empty.
        return INVALID_SUMMARY

    head_summaries: List[str] = []
    for i, head in enumerate(head_children):
        head_summary = _normalize_summary(head, internal_dict, RustChangeHashSummaryProvider)
        if head_summary == INVALID_SUMMARY:
            print(f"INVALID HISTORY REF, HEAD SUMMARY IS INVALID FOR HEAD {i}")
            return INVALID_SUMMARY
        head_summaries.append(head_summary)

    return f"{branch_summary}+{'.'.join(head_summaries)}"


def RustUuidSummaryProvider(valobj: SBValue, internal_dict):
    # uuid::Uuid Display delegates to LowerHex over the hyphenated form.
    raw_bytes = _extract_fixed_bytes(valobj, 16)
    if raw_bytes is None or len(raw_bytes) != 16:
        return INVALID_SUMMARY
    hex_str = bytes(raw_bytes).hex()
    return f"{hex_str[0:8]}-{hex_str[8:12]}-{hex_str[12:16]}-{hex_str[16:20]}-{hex_str[20:32]}"

# Copied from Rust providers; used by HistoryRefSummaryProvider if these aren't already available


def get_template_args(type_name: str) -> Generator[str, None, None]:
    """
    Takes a type name `T<A, tuple$<B, C>, D>` and returns a list of its generic args
    `["A", "tuple$<B, C>", "D"]`.

    String-based replacement for LLDB's `SBType.template_args`, as LLDB is currently unable to
    populate this field for targets with PDB debug info. Also useful for manually altering the type
    name of generics (e.g. `Vec<ref$<str$> >` -> `Vec<&str>`).

    Each element of the returned list can be looked up for its `SBType` value via
    `SBTarget.FindFirstType()`
    """
    level = 0
    start = 0
    for i, c in enumerate(type_name):
        if c == "<":
            level += 1
            if level == 1:
                start = i + 1
        elif c == ">":
            level -= 1
            if level == 0:
                yield type_name[start:i].strip()
        elif c == "," and level == 1:
            yield type_name[start:i].strip()
            start = i + 1


def unwrap_unique_or_non_null(unique_or_nonnull: SBValue) -> SBValue:
    # BACKCOMPAT: rust 1.32
    # https://github.com/rust-lang/rust/commit/7a0911528058e87d22ea305695f4047572c5e067
    # BACKCOMPAT: rust 1.60
    # https://github.com/rust-lang/rust/commit/2a91eeac1a2d27dd3de1bf55515d765da20fd86f
    ptr = unique_or_nonnull.GetChildMemberWithName("pointer")
    return ptr if ptr.TypeIsPointerType() else ptr.GetChildAtIndex(0)


MSVC_PTR_PREFIX: List[str] = ["ref$<", "ref_mut$<", "ptr_const$<", "ptr_mut$<"]


def resolve_msvc_template_arg(arg_name: str, target: SBTarget) -> SBType:
    """
    RECURSIVE when arrays or references are nested (e.g. `ref$<ref$<u8> >`, `array$<ref$<u8> >`)

    Takes the template arg's name (likely from `get_template_args`) and finds/creates its
    corresponding SBType.

    For non-reference/pointer/array types this is identical to calling
    `target.FindFirstType(arg_name)`

    LLDB internally interprets refs, pointers, and arrays C-style (`&u8` -> `u8 *`,
    `*const u8` -> `u8 *`, `[u8; 5]` -> `u8 [5]`). Looking up these names still doesn't work in the
    current version of LLDB, so instead the types are generated via `base_type.GetPointerType()` and
    `base_type.GetArrayType()`, which bypass the PDB file and ask clang directly for the type node.
    """
    result = target.FindFirstType(arg_name)

    if result.IsValid():
        return result

    for prefix in MSVC_PTR_PREFIX:
        if arg_name.startswith(prefix):
            arg_name = arg_name[len(prefix) : -1].strip()

            result = resolve_msvc_template_arg(arg_name, target)
            return result.GetPointerType()

    if arg_name.startswith("array$<"):
        arg_name = arg_name[7:-1].strip()

        template_args = get_template_args(arg_name)

        element_name = next(template_args)
        length = next(template_args)

        result = resolve_msvc_template_arg(element_name, target)

        return result.GetArrayType(int(length))

    return result


class StdVecSyntheticProvider:
    """Pretty-printer for alloc::vec::Vec<T>

    struct Vec<T> { buf: RawVec<T>, len: usize }
    rust 1.75: struct RawVec<T> { ptr: Unique<T>, cap: usize, ... }
    rust 1.76: struct RawVec<T> { ptr: Unique<T>, cap: Cap(usize), ... }
    rust 1.31.1: struct Unique<T: ?Sized> { pointer: NonZero<*const T>, ... }
    rust 1.33.0: struct Unique<T: ?Sized> { pointer: *const T, ... }
    rust 1.62.0: struct Unique<T: ?Sized> { pointer: NonNull<T>, ... }
    struct NonZero<T>(T)
    struct NonNull<T> { pointer: *const T }
    """

    def __init__(self, valobj: SBValue, _dict):
        # logger = Logger.Logger()
        # logger >> "[StdVecSyntheticProvider] for " + str(valobj.GetName())
        self.valobj = valobj
        self.element_type = None
        self.update()

    def num_children(self) -> int:
        return self.length

    def get_child_index(self, name: str) -> int:
        index = name.lstrip("[").rstrip("]")
        if index.isdigit():
            return int(index)
        else:
            return -1

    def get_child_at_index(self, index: int) -> SBValue:
        start = self.data_ptr.GetValueAsUnsigned()
        address = start + index * self.element_type_size
        element = self.data_ptr.CreateValueFromAddress("[%s]" % index, address, self.element_type)
        return element

    def update(self):
        self.length = self.valobj.GetChildMemberWithName("len").GetValueAsUnsigned()
        self.buf = self.valobj.GetChildMemberWithName("buf").GetChildMemberWithName("inner")

        self.data_ptr = unwrap_unique_or_non_null(self.buf.GetChildMemberWithName("ptr"))

        self.element_type = self.valobj.GetType().GetTemplateArgumentType(0)

        if not self.element_type.IsValid():
            arg_name = next(get_template_args(self.valobj.GetTypeName()))

            self.element_type = resolve_msvc_template_arg(arg_name, self.valobj.target)

        self.element_type_size = self.element_type.GetByteSize()

    def has_children(self) -> bool:
        return True
