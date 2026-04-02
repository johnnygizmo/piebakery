import json
import bpy
from bpy.types import Operator
from bpy.props import EnumProperty, StringProperty, BoolProperty

from . import state
from .keybinds import refresh_keymaps

class PIEBAKERY_OT_invoke_pie(Operator): 
    """Open a Pie Bakery menu"""
    bl_idname = "piebakery.invoke_pie"
    bl_label = "Invoke Pie Menu"

    menu_name: StringProperty()  # type: ignore

    def execute(self, context):
        state.active_pie_name = self.menu_name
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
            refresh_keymaps()
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
        refresh_keymaps()
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
        refresh_keymaps()
        self.report({'INFO'}, f"Imported {len(data)} menu(s)")
        return {'FINISHED'}

classes = (
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
)
