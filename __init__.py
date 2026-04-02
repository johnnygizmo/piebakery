# SPDX-License-Identifier: GPL-3.0-or-later

import json
import bpy
from bpy.types import (
    AddonPreferences,
    Menu,
    Operator,
    PropertyGroup,
    UIList,
)
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    EnumProperty,
    IntProperty,
    StringProperty,
)

# ---------------------------------------------------------------
# Key choices for hotkey assignment
# ---------------------------------------------------------------

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

# ---------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------

_active_pie_name: str = ""
_addon_keymaps: list = []


# ---------------------------------------------------------------
# Property groups
# ---------------------------------------------------------------

class PieBakeryItem(PropertyGroup):
    item_type: EnumProperty(
        name="Type",
        items=[
            ('OPERATOR', "Operator", "Call a Blender operator"),
            ('COMMAND',  "Command",  "Run arbitrary Python code"),
            ('VALUE',    "Value",    "Set a property via data path"),
            ('SUBMENU',  "Sub-Menu", "Open another pie menu"),
            ('PALETTE',  "Palette",  "Show a color palette popup"),
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


# ---------------------------------------------------------------
# UI Lists
# ---------------------------------------------------------------

class PIEBAKERY_UL_menus(UIList):
    bl_idname = "PIEBAKERY_UL_menus"

    def draw_item(self, _ctx, layout, _data, item, _icon,
                  _active_data, _active_prop, _index):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.prop(item, "name", text="", emboss=False,
                        icon='PIVOT_INDIVIDUAL')
        else:
            layout.alignment = 'CENTER'
            layout.label(text=item.name, icon='PIVOT_INDIVIDUAL')


class PIEBAKERY_UL_items(UIList):
    bl_idname = "PIEBAKERY_UL_items"

    _TYPE_ICONS = {
        'OPERATOR': 'PLAY',
        'COMMAND':  'CONSOLE',
        'VALUE':    'RNA',
        'SUBMENU':  'PIVOT_INDIVIDUAL',
        'PALETTE':  'COLOR',
    }

    def draw_item(self, _ctx, layout, _data, item, _icon,
                  _active_data, _active_prop, _index):
        ic = self._TYPE_ICONS.get(item.item_type, 'DOT')
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.prop(item, "label", text="", emboss=False, icon=ic)
        else:
            layout.alignment = 'CENTER'
            layout.label(text=item.label, icon=ic)


# ---------------------------------------------------------------
# Helper – draw one item into a pie layout
# ---------------------------------------------------------------

def _draw_pie_item(pie, item, context):
    icon = item.icon if item.icon else 'NONE'

    if item.item_type == 'OPERATOR':
        if item.operator_id:
            op = pie.operator(item.operator_id, text=item.label, icon=icon)
            if item.operator_props:
                try:
                    props = json.loads(item.operator_props)
                    for k, v in props.items():
                        setattr(op, k, v)
                except Exception:
                    pass
        else:
            pie.separator()

    elif item.item_type == 'COMMAND':
        op = pie.operator("piebakery.run_command",
                          text=item.label, icon=icon)
        op.command = item.command

    elif item.item_type == 'VALUE':
        try:
            namespace = {"bpy": bpy, "context": context,
                         "C": context, "D": bpy.data}
            head, attr = item.data_path.rsplit(".", 1)
            target = eval(head, namespace)
            pie.prop(target, attr, text=item.label, icon=icon)
        except Exception:
            pie.separator()

    elif item.item_type == 'SUBMENU':
        op = pie.operator("piebakery.invoke_pie",
                          text=item.label, icon=icon)
        op.menu_name = item.submenu_name

    elif item.item_type == 'PALETTE':
        op = pie.operator("piebakery.palette_popup",
                          text=item.label, icon=icon)
        op.palette_name = item.palette_name


# ---------------------------------------------------------------
# Pie Menu
# ---------------------------------------------------------------

class PIEBAKERY_MT_pie(Menu):
    bl_idname = "PIEBAKERY_MT_pie"
    bl_label = "Pie Bakery"

    def draw(self, context):
        pie = self.layout.menu_pie()
        prefs = context.preferences.addons[__package__].preferences
        for m in prefs.menus:
            if m.name == _active_pie_name:
                for item in m.items:
                    _draw_pie_item(pie, item, context)
                return


# ---------------------------------------------------------------
# Operators – pie invocation & runtime actions
# ---------------------------------------------------------------

class PIEBAKERY_OT_invoke_pie(Operator):
    """Open a Pie Bakery menu"""
    bl_idname = "piebakery.invoke_pie"
    bl_label = "Invoke Pie Menu"

    menu_name: StringProperty()  # type: ignore

    def execute(self, context):
        global _active_pie_name
        _active_pie_name = self.menu_name
        bpy.ops.wm.call_menu_pie(name="PIEBAKERY_MT_pie")
        return {'FINISHED'}


class PIEBAKERY_OT_palette_popup(Operator):
    """Show a palette popup with color swatches"""
    bl_idname = "piebakery.palette_popup"
    bl_label = "Palette Popup"
    bl_options = {'INTERNAL'}

    palette_name: StringProperty()  # type: ignore

    @staticmethod
    def _get_paint(context):
        obj = context.active_object
        if obj is None:
            return None
        ts = context.tool_settings
        mode = obj.mode
        if mode == 'TEXTURE_PAINT':
            return ts.image_paint
        elif mode == 'VERTEX_PAINT':
            return ts.vertex_paint
        elif mode == 'SCULPT':
            return ts.sculpt
        elif mode == 'PAINT_GPENCIL':
            return getattr(ts, "gpencil_paint", None)
        return None

    def invoke(self, context, event):
        # Assign the palette to the active paint so template_palette works
        palette = bpy.data.palettes.get(self.palette_name) if self.palette_name else None
        paint = self._get_paint(context)
        if palette and paint is not None:
            paint.palette = palette
        return context.window_manager.invoke_popup(self, width=200)

    def draw(self, context):
        layout = self.layout

        palette = bpy.data.palettes.get(self.palette_name) if self.palette_name else None

        if not palette:
            layout.label(text="Choose a Palette:", icon='COLOR')
            layout.prop_search(self, "palette_name",
                               bpy.data, "palettes", text="")
            return

        layout.label(text=self.palette_name, icon='COLOR')

        paint = self._get_paint(context)
        if paint is not None:
            layout.template_palette(paint, "palette", color=True)
        else:
            layout.label(text="Enter a paint mode first", icon='INFO')

    def execute(self, context):
        return {'FINISHED'}


class PIEBAKERY_OT_run_command(Operator):
    """Execute arbitrary Python code from a pie menu item"""
    bl_idname = "piebakery.run_command"
    bl_label = "Run Command"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    command: StringProperty()  # type: ignore

    def execute(self, context):
        namespace = {"bpy": bpy, "context": context,
                     "C": context, "D": bpy.data}
        try:
            exec(self.command, namespace)
        except Exception as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}
        return {'FINISHED'}


# ---------------------------------------------------------------
# Operators – preferences editing
# ---------------------------------------------------------------

class PIEBAKERY_OT_menu_add(Operator):
    """Add a new pie menu"""
    bl_idname = "piebakery.menu_add"
    bl_label = "Add Pie Menu"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        prefs = context.preferences.addons[__package__].preferences
        menu = prefs.menus.add()
        menu.name = f"Pie Menu {len(prefs.menus)}"
        prefs.active_menu_index = len(prefs.menus) - 1
        return {'FINISHED'}


class PIEBAKERY_OT_menu_remove(Operator):
    """Remove the selected pie menu"""
    bl_idname = "piebakery.menu_remove"
    bl_label = "Remove Pie Menu"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        prefs = context.preferences.addons[__package__].preferences
        idx = prefs.active_menu_index
        if idx < len(prefs.menus):
            prefs.menus.remove(idx)
            prefs.active_menu_index = min(idx, len(prefs.menus) - 1)
            _refresh_keymaps()
        return {'FINISHED'}


class PIEBAKERY_OT_item_add(Operator):
    """Add an item to the active pie menu (max 8)"""
    bl_idname = "piebakery.item_add"
    bl_label = "Add Item"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        prefs = context.preferences.addons[__package__].preferences
        if prefs.active_menu_index >= len(prefs.menus):
            return {'CANCELLED'}
        menu = prefs.menus[prefs.active_menu_index]
        if len(menu.items) >= 8:
            self.report({'WARNING'}, "Pie menus support up to 8 items")
            return {'CANCELLED'}
        item = menu.items.add()
        item.label = f"Item {len(menu.items)}"
        menu.active_item_index = len(menu.items) - 1
        return {'FINISHED'}


class PIEBAKERY_OT_item_remove(Operator):
    """Remove the selected item from the pie menu"""
    bl_idname = "piebakery.item_remove"
    bl_label = "Remove Item"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        prefs = context.preferences.addons[__package__].preferences
        if prefs.active_menu_index >= len(prefs.menus):
            return {'CANCELLED'}
        menu = prefs.menus[prefs.active_menu_index]
        idx = menu.active_item_index
        if idx < len(menu.items):
            menu.items.remove(idx)
            menu.active_item_index = min(idx, len(menu.items) - 1)
        return {'FINISHED'}


class PIEBAKERY_OT_item_move(Operator):
    """Reorder a pie menu item (changes its pie‑slot position)"""
    bl_idname = "piebakery.item_move"
    bl_label = "Move Item"
    bl_options = {'INTERNAL'}

    direction: EnumProperty(
        items=[('UP', "Up", ""), ('DOWN', "Down", "")],
    )  # type: ignore

    def execute(self, context):
        prefs = context.preferences.addons[__package__].preferences
        if prefs.active_menu_index >= len(prefs.menus):
            return {'CANCELLED'}
        menu = prefs.menus[prefs.active_menu_index]
        idx = menu.active_item_index
        if self.direction == 'UP' and idx > 0:
            menu.items.move(idx, idx - 1)
            menu.active_item_index -= 1
        elif self.direction == 'DOWN' and idx < len(menu.items) - 1:
            menu.items.move(idx, idx + 1)
            menu.active_item_index += 1
        return {'FINISHED'}


class PIEBAKERY_OT_refresh_keymaps(Operator):
    """Re‑register hotkeys for all defined pie menus"""
    bl_idname = "piebakery.refresh_keymaps"
    bl_label = "Apply Keymaps"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        _refresh_keymaps()
        self.report({'INFO'}, "Keymaps updated")
        return {'FINISHED'}


class PIEBAKERY_OT_parse_operator_text(Operator):
    """Parse a pasted bpy.ops call into operator id + properties"""
    bl_idname = "piebakery.parse_operator_text"
    bl_label = "Parse Operator Text"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        import ast
        prefs = context.preferences.addons[__package__].preferences
        if prefs.active_menu_index >= len(prefs.menus):
            return {'CANCELLED'}
        menu = prefs.menus[prefs.active_menu_index]
        if menu.active_item_index >= len(menu.items):
            return {'CANCELLED'}
        item = menu.items[menu.active_item_index]

        text = item.operator_props.strip()
        # Handle full bpy.ops.xxx(...) calls
        if text.startswith("bpy.ops."):
            try:
                paren = text.index("(")
                op_path = text[8:paren]  # strip "bpy.ops."
                args_str = text[paren:]  # "(key=val, ...)"
                # Parse as a function call to extract kwargs safely
                node = ast.parse(f"f{args_str}", mode='eval').body
                props = {}
                for kw in node.keywords:
                    props[kw.arg] = ast.literal_eval(kw.value)
                item.operator_id = op_path
                item.operator_props = json.dumps(props)
                self.report({'INFO'}, f"Parsed: {op_path}")
            except Exception as exc:
                self.report({'ERROR'}, f"Failed to parse: {exc}")
                return {'CANCELLED'}
        else:
            self.report({'WARNING'},
                        "Paste a full bpy.ops.xxx(...) call into Properties")
            return {'CANCELLED'}
        return {'FINISHED'}


# ---------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------

def _menu_to_dict(menu):
    return {
        "name": menu.name,
        "hotkey_type": menu.hotkey_type,
        "hotkey_ctrl": menu.hotkey_ctrl,
        "hotkey_shift": menu.hotkey_shift,
        "hotkey_alt": menu.hotkey_alt,
        "items": [
            {
                "item_type": it.item_type,
                "label": it.label,
                "icon": it.icon,
                "operator_id": it.operator_id,
                "operator_props": it.operator_props,
                "command": it.command,
                "data_path": it.data_path,
                "submenu_name": it.submenu_name,
                "palette_name": it.palette_name,
            }
            for it in menu.items
        ],
    }


def _dict_to_menu(prefs, data):
    menu = prefs.menus.add()
    menu.name = data.get("name", "Imported Menu")
    menu.hotkey_type = data.get("hotkey_type", 'NONE')
    menu.hotkey_ctrl = data.get("hotkey_ctrl", False)
    menu.hotkey_shift = data.get("hotkey_shift", False)
    menu.hotkey_alt = data.get("hotkey_alt", False)
    for item_data in data.get("items", []):
        it = menu.items.add()
        it.item_type = item_data.get("item_type", 'OPERATOR')
        it.label = item_data.get("label", "Item")
        it.icon = item_data.get("icon", "NONE")
        it.operator_id = item_data.get("operator_id", "")
        it.operator_props = item_data.get("operator_props", "")
        it.command = item_data.get("command", "")
        it.data_path = item_data.get("data_path", "")
        it.submenu_name = item_data.get("submenu_name", "")
        it.palette_name = item_data.get("palette_name", "")


class PIEBAKERY_OT_export_menus(Operator):
    """Export all pie menus to a JSON file"""
    bl_idname = "piebakery.export_menus"
    bl_label = "Export Menus"
    bl_options = {'INTERNAL'}

    filepath: StringProperty(subtype='FILE_PATH')  # type: ignore
    filter_glob: StringProperty(default="*.json", options={'HIDDEN'})  # type: ignore

    def invoke(self, context, event):
        self.filepath = "piebakery_menus.json"
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        prefs = context.preferences.addons[__package__].preferences
        data = [_menu_to_dict(m) for m in prefs.menus]
        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}
        self.report({'INFO'}, f"Exported {len(data)} menu(s)")
        return {'FINISHED'}


class PIEBAKERY_OT_import_menus(Operator):
    """Import pie menus from a JSON file"""
    bl_idname = "piebakery.import_menus"
    bl_label = "Import Menus"
    bl_options = {'INTERNAL'}

    filepath: StringProperty(subtype='FILE_PATH')  # type: ignore
    filter_glob: StringProperty(default="*.json", options={'HIDDEN'})  # type: ignore
    replace: BoolProperty(
        name="Replace Existing",
        description="Remove all existing menus before importing",
        default=False,
    )  # type: ignore

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        prefs = context.preferences.addons[__package__].preferences
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}
        if not isinstance(data, list):
            self.report({'ERROR'}, "Invalid file format")
            return {'CANCELLED'}
        if self.replace:
            prefs.menus.clear()
        for entry in data:
            if isinstance(entry, dict):
                _dict_to_menu(prefs, entry)
        prefs.active_menu_index = max(0, len(prefs.menus) - 1)
        _refresh_keymaps()
        self.report({'INFO'}, f"Imported {len(data)} menu(s)")
        return {'FINISHED'}


# ---------------------------------------------------------------
# Addon Preferences (UI)
# ---------------------------------------------------------------

class PieBakeryPreferences(AddonPreferences):
    bl_idname = __package__

    menus: CollectionProperty(type=PieBakeryMenu)  # type: ignore
    active_menu_index: IntProperty()  # type: ignore

    def draw(self, context):
        layout = self.layout

        # -- Pie‑menu list --
        row = layout.row()
        row.template_list(
            "PIEBAKERY_UL_menus", "", self, "menus",
            self, "active_menu_index", rows=4,
        )
        col = row.column(align=True)
        col.operator("piebakery.menu_add",    icon='ADD',    text="")
        col.operator("piebakery.menu_remove", icon='REMOVE', text="")

        row = layout.row(align=True)
        row.operator("piebakery.export_menus", icon='EXPORT', text="Save Menus")
        row.operator("piebakery.import_menus", icon='IMPORT', text="Load Menus")

        if self.active_menu_index >= len(self.menus):
            return

        menu = self.menus[self.active_menu_index]

        # -- Hotkey --
        box = layout.box()
        box.label(text="Hotkey", icon='KEYINGSET')
        row = box.row(align=True)
        row.prop(menu, "hotkey_type", text="")
        row.prop(menu, "hotkey_ctrl",  toggle=True)
        row.prop(menu, "hotkey_shift", toggle=True)
        row.prop(menu, "hotkey_alt",   toggle=True)
        box.operator("piebakery.refresh_keymaps",
                     text="Apply Keymaps", icon='FILE_REFRESH')

        # -- Items list --
        box = layout.box()
        box.label(text="Menu Items (max 8)", icon='COLLAPSEMENU')
        row = box.row()
        row.template_list(
            "PIEBAKERY_UL_items", "", menu, "items",
            menu, "active_item_index", rows=4,
        )
        col = row.column(align=True)
        col.operator("piebakery.item_add",    icon='ADD',    text="")
        col.operator("piebakery.item_remove", icon='REMOVE', text="")
        col.separator()
        col.operator("piebakery.item_move", icon='TRIA_UP',
                     text="").direction = 'UP'
        col.operator("piebakery.item_move", icon='TRIA_DOWN',
                     text="").direction = 'DOWN'

        # -- Selected item detail --
        if menu.active_item_index >= len(menu.items):
            return

        item = menu.items[menu.active_item_index]
        detail = box.box()
        detail.prop(item, "item_type")
        detail.prop(item, "label")
        detail.prop(item, "icon")

        if item.item_type == 'OPERATOR':
            detail.prop(item, "operator_id")
            detail.prop(item, "operator_props")
            if item.operator_props:
                detail.operator("piebakery.parse_operator_text",
                                text="Parse Operator Text", icon='FILE_REFRESH'
                                )
        elif item.item_type == 'COMMAND':
            detail.prop(item, "command")
        elif item.item_type == 'VALUE':
            detail.prop(item, "data_path")
        elif item.item_type == 'SUBMENU':
            detail.prop(item, "submenu_name")
        elif item.item_type == 'PALETTE':
            detail.prop_search(item, "palette_name",
                               bpy.data, "palettes")


# ---------------------------------------------------------------
# Keymap management
# ---------------------------------------------------------------

def _register_keymaps():
    addon = bpy.context.preferences.addons.get(__package__)
    if addon is None:
        return
    prefs = addon.preferences
    kc = bpy.context.window_manager.keyconfigs.addon
    if kc is None:
        return

    for menu in prefs.menus:
        if menu.hotkey_type == 'NONE':
            continue
        km = kc.keymaps.new(name="Window", space_type='EMPTY')
        kmi = km.keymap_items.new(
            "piebakery.invoke_pie",
            type=menu.hotkey_type,
            value='PRESS',
            ctrl=menu.hotkey_ctrl,
            shift=menu.hotkey_shift,
            alt=menu.hotkey_alt,
        )
        kmi.properties.menu_name = menu.name
        _addon_keymaps.append((km, kmi))


def _unregister_keymaps():
    for km, kmi in _addon_keymaps:
        km.keymap_items.remove(kmi)
    _addon_keymaps.clear()


def _refresh_keymaps():
    _unregister_keymaps()
    _register_keymaps()


def _delayed_keymap_init():
    """Called once via bpy.app.timers after registration."""
    _register_keymaps()
    return None


# ---------------------------------------------------------------
# Registration
# ---------------------------------------------------------------

_classes = (
    PieBakeryItem,
    PieBakeryMenu,
    PIEBAKERY_UL_menus,
    PIEBAKERY_UL_items,
    PIEBAKERY_OT_menu_add,
    PIEBAKERY_OT_menu_remove,
    PIEBAKERY_OT_item_add,
    PIEBAKERY_OT_item_remove,
    PIEBAKERY_OT_item_move,
    PIEBAKERY_OT_invoke_pie,
    PIEBAKERY_OT_palette_popup,
    PIEBAKERY_OT_run_command,
    PIEBAKERY_OT_refresh_keymaps,
    PIEBAKERY_OT_parse_operator_text,
    PIEBAKERY_OT_export_menus,
    PIEBAKERY_OT_import_menus,
    PIEBAKERY_MT_pie,
    PieBakeryPreferences,
)


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)
    bpy.app.timers.register(_delayed_keymap_init, first_interval=0.5)


def unregister():
    _unregister_keymaps()
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
