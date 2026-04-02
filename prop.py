import bpy
from bpy.types import PropertyGroup
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    EnumProperty,
    IntProperty,
    StringProperty,
)

_KEY_ITEMS = [
    ('NONE', "None", "No key assigned"),
    ('A', "A", ""), ('B', "B", ""), ('C', "C", ""), ('D', "D", ""),
    ('E', "E", ""), ('F', "F", ""), ('G', "G", ""), ('H', "H", ""),
    ('I', "I", ""), ('J', "J", ""), ('K', "K", ""), ('L', "L", ""),
    ('M', "M", ""), ('N', "N", ""), ('O', "O", ""), ('P', "P", ""),
    ('Q', "Q", ""), ('R', "R", ""), ('S', "S", ""), ('T', "T", ""),
    ('U', "U", ""), ('V', "V", ""), ('W', "W", ""), ('X', "X", ""),
    ('Y', "Y", ""), ('Z', "Z", ""),
    ('ZERO', "0", ""), ('ONE', "1", ""), ('TWO', "2", ""), ('THREE', "3", ""),
    ('FOUR', "4", ""), ('FIVE', "5", ""), ('SIX', "6", ""), ('SEVEN', "7", ""),
    ('EIGHT', "8", ""), ('NINE', "9", ""),
    ('F1', "F1", ""), ('F2', "F2", ""), ('F3', "F3", ""), ('F4', "F4", ""),
    ('F5', "F5", ""), ('F6', "F6", ""), ('F7', "F7", ""), ('F8', "F8", ""),
    ('F9', "F9", ""), ('F10', "F10", ""), ('F11', "F11", ""), ('F12', "F12", ""),
    ('SPACE', "Space", ""),
    ('TAB', "Tab", ""),
    ('RET', "Return", ""),
    ('ACCENT_GRAVE', "`", ""),
    ('COMMA', ",", ""),
    ('PERIOD', ".", ""),
    ('SEMI_COLON', ";", ""),
]

_MODE_ITEMS = [
    ('OBJECT',                "Object",           "Object Mode"),
    ('EDIT_MESH',             "Edit Mesh",        "Edit Mode (Mesh)"),
    ('EDIT_CURVE',            "Edit Curve",       "Edit Mode (Curve)"),
    ('EDIT_SURFACE',          "Edit Surface",     "Edit Mode (Surface)"),
    ('EDIT_TEXT',             "Edit Text",        "Edit Mode (Text)"),
    ('EDIT_ARMATURE',         "Edit Armature",    "Edit Mode (Armature)"),
    ('EDIT_METABALL',         "Edit Metaball",    "Edit Mode (Metaball)"),
    ('EDIT_LATTICE',          "Edit Lattice",     "Edit Mode (Lattice)"),
    ('EDIT_CURVES',           "Edit Curves",      "Edit Mode (Hair Curves)"),
    ('SCULPT',                "Sculpt",           "Sculpt Mode"),
    ('PAINT_VERTEX',          "Vertex Paint",     "Vertex Paint Mode"),
    ('PAINT_WEIGHT',          "Weight Paint",     "Weight Paint Mode"),
    ('PAINT_TEXTURE',         "Texture Paint",    "Texture Paint Mode"),
    ('PARTICLE',              "Particle Edit",    "Particle Edit Mode"),
    ('POSE',                  "Pose",             "Pose Mode"),
    ('PAINT_GREASE_PENCIL',   "Draw GP",          "Grease Pencil Draw Mode"),
    ('EDIT_GREASE_PENCIL',    "Edit GP",          "Grease Pencil Edit Mode"),
    ('SCULPT_GREASE_PENCIL',  "Sculpt GP",        "Grease Pencil Sculpt Mode"),
    ('WEIGHT_GREASE_PENCIL',  "Weight GP",        "Grease Pencil Weight Paint"),
    ('SCULPT_CURVES',         "Sculpt Curves",    "Sculpt Curves Mode"),
]

# Items allowed inside a GROUP (no nested groups)
_GROUP_CHILD_TYPES = [
    ('OPERATOR',    "Operator",    "Call a Blender operator"),
    ('COMMAND',     "Command",     "Run arbitrary Python code"),
    ('VALUE',       "Value",       "Set a property via data path"),
    ('SUBMENU',     "Sub-Menu",    "Open another pie menu"),
    ('PALETTE',     "Palette",     "Show a color palette popup"),
    ('PLACEHOLDER', "Placeholder", "Empty slot to hold position"),
]

class PieBakeryGroupItem(PropertyGroup):
    """An item that lives inside a GROUP pie slot."""
    item_type: EnumProperty(
        name="Type",
        items=_GROUP_CHILD_TYPES,
        default='OPERATOR',
    )  # type: ignore
    label: StringProperty(name="Label", default="New Item")  # type: ignore
    icon: StringProperty(name="Icon", default="NONE",
                         description="Blender icon name (e.g. MESH_CUBE)")  # type: ignore
    operator_id: StringProperty(name="Operator",
                                description="bl_idname of the operator")  # type: ignore
    operator_props: StringProperty(
        name="Properties",
        description='JSON dict of operator properties, e.g. {"size": 2.0}. '
                    'You can also paste a full bpy.ops call and it will be parsed',
    )  # type: ignore
    command: StringProperty(name="Command",
                            description="Python code to execute")  # type: ignore
    data_path: StringProperty(name="Data Path",
                              description="Full Python path to the property")  # type: ignore
    submenu_name: StringProperty(name="Sub-Menu",
                                 description="Name of the pie menu to open")  # type: ignore
    palette_name: StringProperty(name="Palette",
                                 description="Name of the palette in bpy.data.palettes")  # type: ignore
    label_hidden: BoolProperty(
        name="Hide Label",
        description="Do not render the label text for this item",
        default=False,
    )  # type: ignore
    read_only: BoolProperty(
        name="Read Only",
        description="Display value as a read-only label instead of an editable property",
        default=False,
    )  # type: ignore

class PieBakeryItem(PropertyGroup):
    item_type: EnumProperty(
        name="Type",
        items=[
            ('OPERATOR', "Operator", "Call a Blender operator"),
            ('COMMAND',  "Command",  "Run arbitrary Python code"),
            ('VALUE',    "Value",    "Set a property via data path"),
            ('SUBMENU',  "Sub-Menu", "Open another pie menu"),
            ('PALETTE',     "Palette",     "Show a color palette popup"),
            ('GROUP',        "Group",        "Group multiple items in one pie slice"),
            ('PLACEHOLDER',  "Placeholder",  "Empty slot to hold position"),
        ],
        default='OPERATOR',
    )  # type: ignore
    label: StringProperty(
        name="Label", default="New Item",
    )  # type: ignore
    icon: StringProperty(
        name="Icon", default="NONE",
        description="Blender icon name (e.g. MESH_CUBE)",
    )  # type: ignore
    operator_id: StringProperty(
        name="Operator",
        description="bl_idname of the operator (e.g. mesh.primitive_cube_add)",
    )  # type: ignore
    operator_props: StringProperty(
        name="Properties",
        description='JSON dict of operator properties, e.g. {"size": 2.0}. '
                    'You can also paste a full bpy.ops call and it will be parsed',
    )  # type: ignore
    command: StringProperty(
        name="Command",
        description="Python code to execute (use ; to separate statements)",
    )  # type: ignore
    data_path: StringProperty(
        name="Data Path",
        description="Full Python path to the property "
                    "(e.g. bpy.context.object.show_wire)",
    )  # type: ignore
    submenu_name: StringProperty(
        name="Sub-Menu",
        description="Name of the pie menu to open",
    )  # type: ignore
    palette_name: StringProperty(
        name="Palette",
        description="Name of the palette in bpy.data.palettes",
    )  # type: ignore
    group_items: CollectionProperty(type=PieBakeryGroupItem)  # type: ignore
    active_group_item_index: IntProperty()  # type: ignore
    label_hidden: BoolProperty(
        name="Hide Label",
        description="Do not render the label text for this item",
        default=False,
    )  # type: ignore
    read_only: BoolProperty(
        name="Read Only",
        description="Display value as a read-only label instead of an editable property",
        default=False,
    )  # type: ignore
    popout: BoolProperty(
        name="Pop Out",
        description="Add a button to open the group items in a standalone popup",
        default=False,
    )  # type: ignore
    columns: IntProperty(
        name="Columns",
        description="Number of columns to arrange group children in",
        default=1,
        min=1,
        max=8,
    )  # type: ignore

class PieBakeryMenu(PropertyGroup):
    # 'name' is inherited from PropertyGroup
    items: CollectionProperty(type=PieBakeryItem)  # type: ignore
    active_item_index: IntProperty()  # type: ignore
    hotkey_type: EnumProperty(
        name="Key", items=_KEY_ITEMS, default='NONE',
    )  # type: ignore
    hotkey_ctrl:  BoolProperty(name="Ctrl")   # type: ignore
    hotkey_shift: BoolProperty(name="Shift")  # type: ignore
    hotkey_alt:   BoolProperty(name="Alt")    # type: ignore
    modes: EnumProperty(
        name="Modes",
        description="Modes in which this menu is triggered by its hotkey "
                    "(empty = all modes)",
        items=_MODE_ITEMS,
        options={'ENUM_FLAG'},
    )  # type: ignore

classes = (
    PieBakeryGroupItem,
    PieBakeryItem,
    PieBakeryMenu,
)
