import json
import bpy
from bpy.types import Operator
from bpy.props import EnumProperty, IntProperty, StringProperty, BoolProperty

from . import state
from .keybinds import refresh_keymaps

class PIEBAKERY_OT_invoke_pie(Operator): 
    """Open a Pie Bakery menu"""
    bl_idname = "piebakery.invoke_pie"
    bl_label = "Invoke Pie Menu"

    menu_name: StringProperty()  # type: ignore
    is_submenu: BoolProperty(default=False)  # type: ignore

    def invoke(self, context, event):
        # Submenu calls always open regardless of mode
        if self.is_submenu:
            state.active_pie_name = self.menu_name
            bpy.ops.wm.call_menu_pie(name="PIEBAKERY_MT_pie")
            return {'FINISHED'}

        prefs = context.preferences.addons[__package__].preferences

        # Find the menu
        menu = None
        for m in prefs.menus:
            if m.name == self.menu_name:
                menu = m
                break

        if menu is None:
            return {'PASS_THROUGH'}

        current_mode = context.mode
        menu_modes = set(menu.modes)

        # Empty modes = all modes
        if menu_modes and current_mode not in menu_modes:
            return {'PASS_THROUGH'}

        # Check for hotkey+mode conflicts
        conflicts = []
        for m in prefs.menus:
            if m.name == menu.name:
                continue
            if (m.hotkey_type == menu.hotkey_type and
                    m.hotkey_ctrl == menu.hotkey_ctrl and
                    m.hotkey_shift == menu.hotkey_shift and
                    m.hotkey_alt == menu.hotkey_alt):
                m_modes = set(m.modes)
                if not m_modes or current_mode in m_modes:
                    conflicts.append(m.name)

        if conflicts:
            names = ", ".join([menu.name] + conflicts)
            self.report({'INFO'},
                        f"Multiple menus match this hotkey + mode: {names}")

        state.active_pie_name = self.menu_name
        bpy.ops.wm.call_menu_pie(name="PIEBAKERY_MT_pie")
        return {'FINISHED'}

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

class PIEBAKERY_OT_item_duplicate(Operator):
    """Duplicate the selected pie menu item"""
    bl_idname = "piebakery.item_duplicate"
    bl_label = "Duplicate Item"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        prefs = context.preferences.addons[__package__].preferences
        if prefs.active_menu_index >= len(prefs.menus):
            return {'CANCELLED'}
        menu = prefs.menus[prefs.active_menu_index]
        if menu.active_item_index >= len(menu.items):
            return {'CANCELLED'}
        if len(menu.items) >= 8:
            self.report({'WARNING'}, "Pie menus support up to 8 items")
            return {'CANCELLED'}
        src = menu.items[menu.active_item_index]
        new = menu.items.add()
        for prop_name in ('item_type', 'label', 'icon', 'operator_id',
                          'operator_props', 'command', 'data_path',
                          'submenu_name', 'palette_name', 'label_hidden',
                          'read_only', 'popout', 'columns'):
            setattr(new, prop_name, getattr(src, prop_name))
        for gi_src in src.group_items:
            gi_new = new.group_items.add()
            for gp in ('item_type', 'label', 'icon', 'operator_id',
                        'operator_props', 'command', 'data_path',
                        'submenu_name', 'palette_name', 'label_hidden',
                        'read_only'):
                setattr(gi_new, gp, getattr(gi_src, gp))
        menu.active_item_index = len(menu.items) - 1
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

def _get_active_item(context):
    """Return the active PieBakeryItem or None."""
    prefs = context.preferences.addons[__package__].preferences
    if prefs.active_menu_index >= len(prefs.menus):
        return None
    menu = prefs.menus[prefs.active_menu_index]
    if menu.active_item_index >= len(menu.items):
        return None
    return menu.items[menu.active_item_index]

class PIEBAKERY_OT_group_item_add(Operator):
    """Add a child item to the selected GROUP item"""
    bl_idname = "piebakery.group_item_add"
    bl_label = "Add Group Item"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        item = _get_active_item(context)
        if item is None or item.item_type != 'GROUP':
            return {'CANCELLED'}
        child = item.group_items.add()
        child.label = f"Child {len(item.group_items)}"
        item.active_group_item_index = len(item.group_items) - 1
        return {'FINISHED'}

class PIEBAKERY_OT_group_item_remove(Operator):
    """Remove the selected child from the GROUP item"""
    bl_idname = "piebakery.group_item_remove"
    bl_label = "Remove Group Item"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        item = _get_active_item(context)
        if item is None or item.item_type != 'GROUP':
            return {'CANCELLED'}
        idx = item.active_group_item_index
        if idx < len(item.group_items):
            item.group_items.remove(idx)
            item.active_group_item_index = min(idx, len(item.group_items) - 1)
        return {'FINISHED'}

class PIEBAKERY_OT_group_item_duplicate(Operator):
    """Duplicate the selected child in the GROUP item"""
    bl_idname = "piebakery.group_item_duplicate"
    bl_label = "Duplicate Group Item"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        item = _get_active_item(context)
        if item is None or item.item_type != 'GROUP':
            return {'CANCELLED'}
        if item.active_group_item_index >= len(item.group_items):
            return {'CANCELLED'}
        src = item.group_items[item.active_group_item_index]
        new = item.group_items.add()
        for prop_name in ('item_type', 'label', 'icon', 'operator_id',
                          'operator_props', 'command', 'data_path',
                          'submenu_name', 'palette_name', 'label_hidden',
                          'read_only'):
            setattr(new, prop_name, getattr(src, prop_name))
        item.active_group_item_index = len(item.group_items) - 1
        return {'FINISHED'}

class PIEBAKERY_OT_group_item_move(Operator):
    """Reorder a child item within the GROUP"""
    bl_idname = "piebakery.group_item_move"
    bl_label = "Move Group Item"
    bl_options = {'INTERNAL'}

    direction: EnumProperty(
        items=[('UP', "Up", ""), ('DOWN', "Down", "")],
    )  # type: ignore

    def execute(self, context):
        item = _get_active_item(context)
        if item is None or item.item_type != 'GROUP':
            return {'CANCELLED'}
        idx = item.active_group_item_index
        if self.direction == 'UP' and idx > 0:
            item.group_items.move(idx, idx - 1)
            item.active_group_item_index -= 1
        elif self.direction == 'DOWN' and idx < len(item.group_items) - 1:
            item.group_items.move(idx, idx + 1)
            item.active_group_item_index += 1
        return {'FINISHED'}

class PIEBAKERY_OT_group_popup(Operator):
    """Open a standalone popup with the items from a GROUP pie slot"""
    bl_idname = "piebakery.group_popup"
    bl_label = "Group Popup"
    bl_options = {'INTERNAL'}

    menu_name: StringProperty()   # type: ignore
    item_index: IntProperty()     # type: ignore

    def invoke(self, context, event):
        return context.window_manager.invoke_popup(self, width=250)

    def draw(self, context):
        layout = self.layout
        prefs = context.preferences.addons[__package__].preferences
        menu = None
        for m in prefs.menus:
            if m.name == self.menu_name:
                menu = m
                break
        if menu is None or self.item_index >= len(menu.items):
            layout.label(text="Group not found", icon='ERROR')
            return
        item = menu.items[self.item_index]
        layout.label(text=item.label,
                     icon=item.icon if item.icon else 'THREE_DOTS')
        col = layout.column(align=True)
        from .ui import _draw_item_content
        for child in item.group_items:
            _draw_item_content(col, child, context)

    def execute(self, context):
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

def _item_to_dict(it):
    d = {
        "item_type": it.item_type,
        "label": it.label,
        "icon": it.icon,
        "label_hidden": it.label_hidden,
        "read_only": it.read_only,
        "operator_id": it.operator_id,
        "operator_props": it.operator_props,
        "command": it.command,
        "data_path": it.data_path,
        "submenu_name": it.submenu_name,
        "palette_name": it.palette_name,
    }
    if it.item_type == 'GROUP':
        d["popout"] = it.popout
        d["columns"] = it.columns
        d["group_items"] = [
            {
                "item_type": gi.item_type,
                "label": gi.label,
                "icon": gi.icon,
                "label_hidden": gi.label_hidden,
                "read_only": gi.read_only,
                "operator_id": gi.operator_id,
                "operator_props": gi.operator_props,
                "command": gi.command,
                "data_path": gi.data_path,
                "submenu_name": gi.submenu_name,
                "palette_name": gi.palette_name,
            }
            for gi in it.group_items
        ]
    return d

def _menu_to_dict(menu):
    return {
        "name": menu.name,
        "hotkey_type": menu.hotkey_type,
        "hotkey_ctrl": menu.hotkey_ctrl,
        "hotkey_shift": menu.hotkey_shift,
        "hotkey_alt": menu.hotkey_alt,
        "modes": sorted(menu.modes),
        "items": [_item_to_dict(it) for it in menu.items],
    }

def _dict_to_menu(prefs, data):
    menu = prefs.menus.add()
    menu.name = data.get("name", "Imported Menu")
    menu.hotkey_type = data.get("hotkey_type", 'NONE')
    menu.hotkey_ctrl = data.get("hotkey_ctrl", False)
    menu.hotkey_shift = data.get("hotkey_shift", False)
    menu.hotkey_alt = data.get("hotkey_alt", False)
    modes = data.get("modes", [])
    if modes:
        menu.modes = set(modes)
    for item_data in data.get("items", []):
        it = menu.items.add()
        it.item_type = item_data.get("item_type", 'OPERATOR')
        it.label = item_data.get("label", "Item")
        it.icon = item_data.get("icon", "NONE")
        it.label_hidden = item_data.get("label_hidden", False)
        it.read_only = item_data.get("read_only", False)
        it.operator_id = item_data.get("operator_id", "")
        it.operator_props = item_data.get("operator_props", "")
        it.command = item_data.get("command", "")
        it.data_path = item_data.get("data_path", "")
        it.submenu_name = item_data.get("submenu_name", "")
        it.palette_name = item_data.get("palette_name", "")
        if it.item_type == 'GROUP':
            it.popout = item_data.get("popout", False)
            it.columns = item_data.get("columns", 1)
            for gi_data in item_data.get("group_items", []):
                gi = it.group_items.add()
                gi.item_type = gi_data.get("item_type", 'OPERATOR')
                gi.label = gi_data.get("label", "Item")
                gi.icon = gi_data.get("icon", "NONE")
                gi.label_hidden = gi_data.get("label_hidden", False)
                gi.read_only = gi_data.get("read_only", False)
                gi.operator_id = gi_data.get("operator_id", "")
                gi.operator_props = gi_data.get("operator_props", "")
                gi.command = gi_data.get("command", "")
                gi.data_path = gi_data.get("data_path", "")
                gi.submenu_name = gi_data.get("submenu_name", "")
                gi.palette_name = gi_data.get("palette_name", "")

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

class PIEBAKERY_OT_select_slot(Operator):
    """Select this pie slot for editing"""
    bl_idname = "piebakery.select_slot"
    bl_label = "Select Slot"
    bl_options = {'INTERNAL'}

    slot_index: IntProperty()  # type: ignore

    def execute(self, context):
        prefs = context.preferences.addons[__package__].preferences
        if prefs.active_menu_index >= len(prefs.menus):
            return {'CANCELLED'}
        menu = prefs.menus[prefs.active_menu_index]
        if self.slot_index < len(menu.items):
            menu.active_item_index = self.slot_index
        return {'FINISHED'}


class PIEBAKERY_OT_open_editor(Operator):
    """Open the Pie Bakery Menu Editor"""
    bl_idname = "piebakery.open_editor"
    bl_label = "Pie Bakery Menu Editor"
    bl_options = {'INTERNAL'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=980)

    def draw(self, context):
        from .ui import _draw_editor
        _draw_editor(self.layout, context)

    def execute(self, context):
        return {'FINISHED'}


classes = (
    PIEBAKERY_OT_select_slot,
    PIEBAKERY_OT_open_editor,
    PIEBAKERY_OT_menu_add,
    PIEBAKERY_OT_menu_remove,
    PIEBAKERY_OT_item_add,
    PIEBAKERY_OT_item_remove,
    PIEBAKERY_OT_item_duplicate,
    PIEBAKERY_OT_item_move,
    PIEBAKERY_OT_invoke_pie,
    PIEBAKERY_OT_palette_popup,
    PIEBAKERY_OT_run_command,
    PIEBAKERY_OT_refresh_keymaps,
    PIEBAKERY_OT_group_item_add,
    PIEBAKERY_OT_group_item_remove,
    PIEBAKERY_OT_group_item_duplicate,
    PIEBAKERY_OT_group_item_move,
    PIEBAKERY_OT_group_popup,
    PIEBAKERY_OT_parse_operator_text,
    PIEBAKERY_OT_export_menus,
    PIEBAKERY_OT_import_menus,
)
