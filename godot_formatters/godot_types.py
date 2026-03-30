from importlib import reload
import godot_formatters.godot_providers

from godot_formatters.godot_providers import *

# The namespace for these types will either be global (if debugging engine code),
# or `godot` if we're debugging GDExtension C++ code

# fmt: off

HASHSET_PATTERN:str = "^((godot)?::)?HashSet<.+(,[^,]+)?(,[^,]+)?>$"
HASHMAP_PATTERN:str = "^((godot)?::)?HashMap<.+,.+(,[^,]+)?(,[^,]+)?(,[^,]+)?>$"
LIST_PATTERN:str = "^((godot)?::)?List<.+(,[^,]+)?>$"
ARRAY_PATTERN:str = "^((godot)?::)?Array$"
TYPEDARRAY_PATTERN:str = "^((godot)?::)?TypedArray<.+>$"
DICTIONARY_PATTERN:str = "^((godot)?::)?Dictionary$"
VECTOR_PATTERN:str = "^((godot)?::)?Vector<.+>$"
PACKED_ARRAY_PATTERN:str = "^((godot)?::)?Packed\\w+Array$"
HASH_MAP_ELEMENT_PATTERN:str = "^((godot)?::)?HashMapElement<.+,.+>$"
KEY_VALUE_PATTERN:str = "^((godot)?::)?KeyValue<.+,.+>$"
VMAP_PATTERN:str = "^((godot)?::)?VMap<.+,.+>$"
VMAP_PAIR_PATTERN:str = "^((godot)?::)?VMap<.+,.+>::Pair$"
VSET_PATTERN:str = "^((godot)?::)?VSet<.+>$"
RINGBUFFER_PATTERN:str = "^((godot)?::)?RingBuffer<.+>$"
LOCAL_VECTOR_PATTERN:str = "^((godot)?::)?LocalVector<.+(,[^,]+){0,3}>$"
PAGED_ARRAY_PATTERN:str = "^((godot)?::)?PagedArray<.+>$"
RBMAP_PATTERN:str = "^((godot)?::)?RBMap<.+,.+(,[^,]+){0,2}>$"
RBMAP_ELEMENT_PATTERN:str = "^((godot)?::)?RBMap<.+,.+(,[^,]+){0,2}>::Element$"


SYNTHETIC_PROVIDERS: dict[str,type] = {
    "^((godot)?::)?Variant$":          Variant_SyntheticProvider,
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
    "^((godot)?::)?String$":        String_SummaryProvider,
    "^((godot)?::)?CharString(T<.+>)?$":    CharString_SummaryProvider,
    "^((godot)?::)?Ref<.+>$":       Ref_SummaryProvider,
    "^((godot)?::)?Vector2$":       Vector2_SummaryProvider,
    "^((godot)?::)?Vector2i$":      Vector2i_SummaryProvider,
    "^((godot)?::)?Rect2$":         Rect2_SummaryProvider,
    "^((godot)?::)?Rect2i$":        Rect2i_SummaryProvider,
    "^((godot)?::)?Vector3$":       Vector3_SummaryProvider,
    "^((godot)?::)?Vector3i$":      Vector3i_SummaryProvider,
    "^((godot)?::)?Transform2D$":   Transform2D_SummaryProvider,
    "^((godot)?::)?Vector4$":       Vector4_SummaryProvider,
    "^((godot)?::)?Vector4i$":      Vector4i_SummaryProvider,
    "^((godot)?::)?Plane$":         Plane_SummaryProvider,
    "^((godot)?::)?Quaternion$":    Quaternion_SummaryProvider,
    "^((godot)?::)?AABB$":          AABB_SummaryProvider,
    "^((godot)?::)?Basis$":         Basis_SummaryProvider,
    "^((godot)?::)?Transform3D$":   Transform3D_SummaryProvider,
    "^((godot)?::)?Projection$":    Projection_SummaryProvider,
    "^((godot)?::)?Color$":         Color_SummaryProvider,
    "^((godot)?::)?StringName$":    StringName_SummaryProvider,
    "^((godot)?::)?NodePath$":      NodePath_SummaryProvider,
    "^((godot)?::)?RID$":           RID_SummaryProvider,
    "^((godot)?::)?Callable$":      Callable_SummaryProvider,
    "^((godot)?::)?Signal$":        Signal_SummaryProvider,
    "^((godot)?::)?ObjectID$":      ObjectID_SummaryProvider,
    KEY_VALUE_PATTERN:      KeyValue_SummaryProvider,
    HASH_MAP_ELEMENT_PATTERN: HashMapElement_SummaryProvider,
    RBMAP_ELEMENT_PATTERN:     RBMapElement_SummaryProvider,
    VMAP_PAIR_PATTERN:      VMap_Pair_SummaryProvider,
    "^((godot)?::)?Pair<.+,.+>$":    Pair_SummaryProvider,
}
