from importlib import reload

from godot_formatters.godot_gdext_providers import (
    GDExtBaseGDObjectSynthProvider,
    GDExtGenericSynthProvider,
    GDExtGenericSummaryProvider,
    GDExtOpaqueSummaryProvider,
    GDExtRIDSummaryProvider,
    GDExtGDObjectSynthProvider,
    RustChangeHashSummaryProvider,
    RustDocumentIdSummaryProvider,
    RustHistoryRefSummaryProvider,
    RustUuidSummaryProvider,
)

# opaque types with synthetic providers
GDEXT_VARIANT_PATTERN:str = f"^godot_core::builtin::variant::Variant$"
GDEXT_DICTIONARY_PATTERN:str = "^godot_core::builtin::collections::dictionary::Dictionary$"
GDEXT_ARRAY_PATTERN:str = "^godot_core::builtin::collections::array::Array<.*>$"
GDEXT_VECTOR_PATTERN:str = "^godot_core::builtin::collections::packed_array::Packed.+Array$"
# No Synthetic providers for these types, but they're opaque
GDEXT_STRING_PATTERN:str = "^godot_core::builtin::string::gstring::GString$"
GDEXT_STRING_NAME_PATTERN:str = "^godot_core::builtin::string::string_name::StringName$"
GDEXT_NODE_PATH_PATTERN:str = "^godot_core::builtin::string::node_path::NodePath$"
GDEXT_CALLABLE_PATTERN:str = "^godot_core::builtin::callable::Callable$"
GDEXT_SIGNAL_PATTERN:str = "^godot_core::builtin::signal::Signal$"


# Summary providers
# the rest of these are implemented natively, so we can just use the summary providers from godot_providers.py
GDEXT_VECTOR2_PATTERN:str = "^godot_core::builtin::vectors::vector2::Vector2$"
GDEXT_VECTOR2I_PATTERN:str = "^godot_core::builtin::vectors::vector2i::Vector2i$"
GDEXT_VECTOR3_PATTERN:str = "^godot_core::builtin::vectors::vector3::Vector3$"
GDEXT_VECTOR3I_PATTERN:str = "^godot_core::builtin::vectors::vector3i::Vector3i$"
GDEXT_VECTOR4_PATTERN:str = "^godot_core::builtin::vectors::vector4::Vector4$"
GDEXT_VECTOR4I_PATTERN:str = "^godot_core::builtin::vectors::vector4i::Vector4i$"
GDEXT_RID_PATTERN:str = "^godot_core::builtin::rid::Rid$"
GDEXT_OBJECT_ID_PATTERN:str = "^godot_core::builtin::object::ObjectID$"
GDEXT_RECT2_PATTERN:str = "^godot_core::builtin::rect2::Rect2$"
GDEXT_RECT2I_PATTERN:str = "^godot_core::builtin::rect2i::Rect2i$"
GDEXT_COLOR_PATTERN:str = "^godot_core::builtin::color::Color$"
GDEXT_PLANE_PATTERN:str = "^godot_core::builtin::plane::Plane$"
GDEXT_PROJECTION_PATTERN:str = "^godot_core::builtin::projection::Projection$"
GDEXT_QUATERNION_PATTERN:str = "^godot_core::builtin::quaternion::Quaternion$"
GDEXT_AABB_PATTERN:str = "^godot_core::builtin::aabb::Aabb$"
GDEXT_BASIS_PATTERN:str = "^godot_core::builtin::basis::Basis$"
GDEXT_TRANSFORM2D_PATTERN:str = "^godot_core::builtin::transform2d::Transform2D$"
GDEXT_TRANSFORM3D_PATTERN:str = "^godot_core::builtin::transform3d::Transform3D$"

GDEXT_BASE_PATTERN:str = "^godot_core::obj::base::Base<.+>$"
GDEXT_GD_PATTERN:str = "^godot_core::obj::gd::Gd<.+>$"
GDEXT_RAW_GD_PATTERN:str = "^godot_core::obj::raw_gd::RawGd<.+>$"

# Rust-specific summaries
RUST_HISTORY_REF_PATTERN: str = "^(::)?.*::HistoryRef$"
RUST_DOCUMENT_ID_PATTERN: str = "^(::)?.*::DocumentId$"
RUST_CHANGE_HASH_PATTERN: str = "^(::)?.*::ChangeHash$"
RUST_UUID_PATTERN: str = "^(::)?.*::Uuid$"
RUST_UUID_UPPER_PATTERN: str = "^(::)?.*::UUID$"


GDEXT_SYNTHETIC_PROVIDERS: dict[str,type] = {
    GDEXT_VARIANT_PATTERN: GDExtGenericSynthProvider,
    GDEXT_DICTIONARY_PATTERN: GDExtGenericSynthProvider,
    GDEXT_ARRAY_PATTERN: GDExtGenericSynthProvider,
    GDEXT_VECTOR_PATTERN: GDExtGenericSynthProvider,
    GDEXT_RAW_GD_PATTERN: GDExtGDObjectSynthProvider,
    GDEXT_GD_PATTERN: GDExtGDObjectSynthProvider,
    GDEXT_BASE_PATTERN: GDExtBaseGDObjectSynthProvider,
}

GDEXT_SUMMARY_PROVIDERS: dict[str, object] = {
    # opaque types
    GDEXT_STRING_PATTERN: GDExtOpaqueSummaryProvider,
    GDEXT_STRING_NAME_PATTERN: GDExtOpaqueSummaryProvider,
    GDEXT_NODE_PATH_PATTERN: GDExtOpaqueSummaryProvider,
    GDEXT_CALLABLE_PATTERN: GDExtOpaqueSummaryProvider,
    GDEXT_SIGNAL_PATTERN: GDExtOpaqueSummaryProvider,
    # real types
    GDEXT_VECTOR2_PATTERN: GDExtGenericSummaryProvider,
    GDEXT_VECTOR2I_PATTERN: GDExtGenericSummaryProvider,
    GDEXT_VECTOR3_PATTERN: GDExtGenericSummaryProvider,
    GDEXT_VECTOR3I_PATTERN: GDExtGenericSummaryProvider,
    GDEXT_VECTOR4_PATTERN: GDExtGenericSummaryProvider,
    GDEXT_VECTOR4I_PATTERN: GDExtGenericSummaryProvider,
    GDEXT_PLANE_PATTERN: GDExtGenericSummaryProvider,
    GDEXT_PROJECTION_PATTERN: GDExtGenericSummaryProvider,
    GDEXT_QUATERNION_PATTERN: GDExtGenericSummaryProvider,
    GDEXT_AABB_PATTERN: GDExtGenericSummaryProvider,
    GDEXT_BASIS_PATTERN: GDExtGenericSummaryProvider,
    GDEXT_TRANSFORM2D_PATTERN: GDExtGenericSummaryProvider,
    GDEXT_TRANSFORM3D_PATTERN: GDExtGenericSummaryProvider,
    GDEXT_RECT2_PATTERN: GDExtGenericSummaryProvider,
    GDEXT_RECT2I_PATTERN: GDExtGenericSummaryProvider,
    GDEXT_COLOR_PATTERN: GDExtGenericSummaryProvider,
    GDEXT_RID_PATTERN: GDExtRIDSummaryProvider,
    # rust types
    RUST_HISTORY_REF_PATTERN: RustHistoryRefSummaryProvider,
    RUST_DOCUMENT_ID_PATTERN: RustDocumentIdSummaryProvider,
    RUST_CHANGE_HASH_PATTERN: RustChangeHashSummaryProvider,
    RUST_UUID_PATTERN: RustUuidSummaryProvider,
    RUST_UUID_UPPER_PATTERN: RustUuidSummaryProvider,
}
