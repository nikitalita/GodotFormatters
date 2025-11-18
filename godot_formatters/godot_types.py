from importlib import reload
import godot_formatters.godot_providers

from godot_formatters.godot_providers import *


# fmt: off

HASHSET_PATTERN:str = "^(::)?HashSet<.+(,[^,]+)?(,[^,]+)?>$"
HASHMAP_PATTERN:str = "^(::)?HashMap<.+,.+(,[^,]+)?(,[^,]+)?(,[^,]+)?>$"
LIST_PATTERN:str = "^(::)?List<.+(,[^,]+)?>$"
ARRAY_PATTERN:str = "^(::)?Array$"
TYPEDARRAY_PATTERN:str = "^(::)?TypedArray<.+>$"
DICTIONARY_PATTERN:str = "^(::)?Dictionary$"
VECTOR_PATTERN:str = "^(::)?Vector<.+>$"
PACKED_ARRAY_PATTERN:str = "^(::)?Packed\\w+Array$"
HASH_MAP_ELEMENT_PATTERN:str = "^(::)?HashMapElement<.+,.+>$"
KEY_VALUE_PATTERN:str = "^(::)?KeyValue<.+,.+>$"
VMAP_PATTERN:str = "^(::)?VMap<.+,.+>$"
VMAP_PAIR_PATTERN:str = "^(::)?VMap<.+,.+>::Pair$"
VSET_PATTERN:str = "^(::)?VSet<.+>$"
RINGBUFFER_PATTERN:str = "^(::)?RingBuffer<.+>$"
LOCAL_VECTOR_PATTERN:str = "^(::)?LocalVector<.+(,[^,]+){0,3}>$"
PAGED_ARRAY_PATTERN:str = "^(::)?PagedArray<.+>$"
RBMAP_PATTERN:str = "^(::)?RBMap<.+,.+(,[^,]+){0,2}>$"
RBMAP_ELEMENT_PATTERN:str = "^(::)?RBMap<.+,.+(,[^,]+){0,2}>::Element$"


SYNTHETIC_PROVIDERS: dict[str,type] = {
    "^(::)?Variant$":          Variant_SyntheticProvider,
    # HASH_MAP_ELEMENT_PATTERN:  HashMapElement_SyntheticProvider,
    VECTOR_PATTERN:            Vector_SyntheticProvider,
    PACKED_ARRAY_PATTERN:      Vector_SyntheticProvider,
    LIST_PATTERN:              List_SyntheticProvider,
    HASHSET_PATTERN:           HashSet_SyntheticProvider,
    ARRAY_PATTERN:             Array_SyntheticProvider,
    TYPEDARRAY_PATTERN:        Array_SyntheticProvider,
    HASHMAP_PATTERN:           HashMap_SyntheticProvider,
    DICTIONARY_PATTERN:        Dictionary_SyntheticProvider,
    VMAP_PATTERN:              VMap_SyntheticProvider,
    VSET_PATTERN:              VSet_SyntheticProvider,
    RINGBUFFER_PATTERN:        RingBuffer_SyntheticProvider,
    LOCAL_VECTOR_PATTERN:      LocalVector_SyntheticProvider,
    PAGED_ARRAY_PATTERN:       PagedArray_SyntheticProvider,
    RBMAP_PATTERN:             RBMap_SyntheticProvider,
    # RBMAP_ELEMENT_PATTERN:     RBMapElement_SyntheticProvider,
}

SUMMARY_PROVIDERS: dict[str,object] = {
    "^(::)?String$":        String_SummaryProvider,
    "^(::)?CharString(T<.+>)?$":    CharString_SummaryProvider,
    "^(::)?Ref<.+>$":       Ref_SummaryProvider,
    "^(::)?Vector2$":       Vector2_SummaryProvider,
    "^(::)?Vector2i$":      Vector2i_SummaryProvider,
    "^(::)?Rect2$":         Rect2_SummaryProvider,
    "^(::)?Rect2i$":        Rect2i_SummaryProvider,
    "^(::)?Vector3$":       Vector3_SummaryProvider,
    "^(::)?Vector3i$":      Vector3i_SummaryProvider,
    "^(::)?Transform2D$":   Transform2D_SummaryProvider,
    "^(::)?Vector4$":       Vector4_SummaryProvider,
    "^(::)?Vector4i$":      Vector4i_SummaryProvider,
    "^(::)?Plane$":         Plane_SummaryProvider,
    "^(::)?Quaternion$":    Quaternion_SummaryProvider,
    "^(::)?AABB$":          AABB_SummaryProvider,
    "^(::)?Basis$":         Basis_SummaryProvider,
    "^(::)?Transform3D$":   Transform3D_SummaryProvider,
    "^(::)?Projection$":    Projection_SummaryProvider,
    "^(::)?Color$":         Color_SummaryProvider,
    "^(::)?StringName$":    StringName_SummaryProvider,
    "^(::)?NodePath$":      NodePath_SummaryProvider,
    "^(::)?RID$":           RID_SummaryProvider,
    "^(::)?Callable$":      Callable_SummaryProvider,
    "^(::)?Signal$":        Signal_SummaryProvider,
    "^(::)?ObjectID$":      ObjectID_SummaryProvider,
    KEY_VALUE_PATTERN:      KeyValue_SummaryProvider,
    HASH_MAP_ELEMENT_PATTERN: HashMapElement_SummaryProvider,
    RBMAP_ELEMENT_PATTERN:     RBMapElement_SummaryProvider,
    VMAP_PAIR_PATTERN:      VMap_Pair_SummaryProvider,
    "^(::)?Pair<.+,.+>$":    Pair_SummaryProvider,
}
