import json
import bpy
from bpy.types import UIList, Menu, AddonPreferences

from .prop import PieBakeryMenu
from . import state

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
        'OPERATOR':    'PLAY',
        'COMMAND':     'CONSOLE',
        'VALUE':       'RNA',
        'SUBMENU':     'PIVOT_INDIVIDUAL',
        'PALETTE':     'COLOR',
        'GROUP':       'THREE_DOTS',
        'PLACEHOLDER': 'BLANK1',
    }

    def draw_item(self, _ctx, layout, _data, item, _icon,
                  _active_data, _active_prop, _index):
        ic = self._TYPE_ICONS.get(item.item_type, 'DOT')
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.prop(item, "label", text="", emboss=False, icon=ic)
        else:
            layout.alignment = 'CENTER'
            layout.label(text=item.label, icon=ic)

class PIEBAKERY_UL_group_items(UIList):
    bl_idname = "PIEBAKERY_UL_group_items"

    _TYPE_ICONS = {
        'OPERATOR':    'PLAY',
        'COMMAND':     'CONSOLE',
        'VALUE':       'RNA',
        'SUBMENU':     'PIVOT_INDIVIDUAL',
        'PALETTE':     'COLOR',
        'PLACEHOLDER': 'BLANK1',
    }

    def draw_item(self, _ctx, layout, _data, item, _icon,
                  _active_data, _active_prop, _index):
        ic = self._TYPE_ICONS.get(item.item_type, 'DOT')
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.prop(item, "label", text="", emboss=False, icon=ic)
        else:
            layout.alignment = 'CENTER'
            layout.label(text=item.label, icon=ic)

def _draw_item_content(layout, item, context):
    """Draw a single item's content into the given layout (box, column, etc.)."""
    icon = item.icon if item.icon else 'NONE'
    text = "" if getattr(item, "label_hidden", False) else item.label

    if item.item_type == 'OPERATOR':
        if item.operator_id:
            op = layout.operator(item.operator_id, text=text, icon=icon)
            if item.operator_props:
                try:
                    props = json.loads(item.operator_props)
                    for k, v in props.items():
                        setattr(op, k, v)
                except Exception:
                    pass
        else:
            layout.separator()

    elif item.item_type == 'COMMAND':
        op = layout.operator("piebakery.run_command",
                             text=text, icon=icon)
        op.command = item.command

    elif item.item_type == 'VALUE':
        try:
            namespace = {"bpy": bpy, "context": context,
                         "C": context, "D": bpy.data}
            head, attr = item.data_path.rsplit(".", 1)
            target = eval(head, namespace)
            if getattr(item, "read_only", False):
                val = getattr(target, attr)
                if isinstance(val, str):
                    display = val
                else:
                    display = str(val)
                label_text = f"{text}:  {display}" if text else display
                layout.label(text=label_text, icon=icon)
            else:
                layout.prop(target, attr, text=text, icon=icon)
        except Exception:
            layout.separator()

    elif item.item_type == 'SUBMENU':
        op = layout.operator("piebakery.invoke_pie",
                             text=text, icon=icon)
        op.menu_name = item.submenu_name
        op.is_submenu = True

    elif item.item_type == 'PALETTE':
        op = layout.operator("piebakery.palette_popup",
                             text=text, icon=icon)
        op.palette_name = item.palette_name

    elif item.item_type == 'PLACEHOLDER':
        layout.separator()

def _draw_pie_item(pie, item, context):
    """Draw a top-level pie item (with box wrapper) into a pie slot."""
    if item.item_type == 'PLACEHOLDER':
        pie.separator()
        return

    if item.item_type == 'OPERATOR' and not item.operator_id:
        pie.separator()
        return

    box = pie.box()
    col = box.column(align=True)

    if item.item_type == 'GROUP':
        row = col.row(align=True)
        # Determine content area
        if item.columns <= 1:
            left = row.column(align=True)
            if not item.label_hidden:
                left.label(text=item.label,
                       icon=item.icon if item.icon else 'THREE_DOTS')
            for child in item.group_items:
                _draw_item_content(left, child, context)
        else:
            content = row.column(align=True)
            if not item.label_hidden:
                content.label(text=item.label,
                          icon=item.icon if item.icon else 'THREE_DOTS')
            flow = content.grid_flow(row_major=True,
                                     columns=item.columns,
                                     even_columns=True,
                                     even_rows=False,
                                     align=True)
            for child in item.group_items:
                _draw_item_content(flow, child, context)
        if item.popout:
            right = row.column(align=True)
            # Find the item index within its parent menu
            prefs = context.preferences.addons[__package__].preferences
            for m in prefs.menus:
                if m.name == state.active_pie_name:
                    for idx, mi in enumerate(m.items):
                        if mi == item:
                            op = right.operator("piebakery.group_popup",
                                                text="",
                                                icon='WINDOW')
                            op.menu_name = m.name
                            op.item_index = idx
                            break
                    break
    else:
        _draw_item_content(col, item, context)

class PIEBAKERY_MT_pie(Menu):
    bl_idname = "PIEBAKERY_MT_pie"
    bl_label = "Pie Bakery"

    def draw(self, context):
        pie = self.layout.menu_pie()
        prefs = context.preferences.addons[__package__].preferences
        for m in prefs.menus:
            if m.name == state.active_pie_name:
                items = list(m.items)
                # Pad to at least 8 to fill all pie menu slots statically
                items.extend([None] * max(0, 8 - len(items)))
                # Blender default pie positions: Left, Right, Bottom, Top, Top-Left, Top-Right, Bottom-Left, Bottom-Right
                # Clockwise indices starting from Top: 6(L), 2(R), 4(B), 0(T), 7(TL), 1(TR), 5(BL), 3(BR)
                for i in [6, 2, 4, 0, 7, 1, 5, 3]:
                    if i < len(items) and items[i]:
                        _draw_pie_item(pie, items[i], context)
                    else:
                        pie.separator()
                return

class PieBakeryPreferences(AddonPreferences):
    bl_idname = __package__

    from bpy.props import CollectionProperty, IntProperty
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

        if getattr(self, "active_menu_index", 0) >= len(self.menus):
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

        # -- Active Modes --
        box = layout.box()
        box.label(text="Active Modes (empty = all modes)", icon='OBJECT_DATA')
        flow = box.grid_flow(row_major=True, columns=4, even_columns=True,
                             even_rows=False, align=True)
        flow.prop(menu, "modes")

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
        col.operator("piebakery.item_duplicate", icon='DUPLICATE', text="")
        col.separator()
        col.operator("piebakery.item_move", icon='TRIA_UP',
                     text="").direction = 'UP'
        col.operator("piebakery.item_move", icon='TRIA_DOWN',
                     text="").direction = 'DOWN'

        # -- Selected item detail --
        if getattr(menu, "active_item_index", 0) >= len(menu.items):
            return

        item = menu.items[menu.active_item_index]
        detail = box.box()
        indent = detail.row()
        indent.separator(factor=2.0)
        col_detail = indent.column()
        col_detail.prop(item, "item_type")
        col_detail.prop(item, "label")
        col_detail.prop(item, "icon")
        col_detail.prop(item, "label_hidden")

        if item.item_type == 'OPERATOR':
            col_detail.prop(item, "operator_id")
            col_detail.prop(item, "operator_props")
            if item.operator_props:
                col_detail.operator("piebakery.parse_operator_text",
                                text="Parse Operator Text", icon='FILE_REFRESH'
                                )
        elif item.item_type == 'COMMAND':
            col_detail.prop(item, "command")
        elif item.item_type == 'VALUE':
            col_detail.prop(item, "data_path")
            col_detail.prop(item, "read_only")
        elif item.item_type == 'SUBMENU':
            col_detail.prop(item, "submenu_name")
        elif item.item_type == 'PALETTE':
            col_detail.prop_search(item, "palette_name",
                               bpy.data, "palettes")
        elif item.item_type == 'GROUP':
            row = col_detail.row(align=True)
            row.prop(item, "popout")
            row.prop(item, "columns")
            # -- Group children (tree) --
            grp_box = col_detail.box()
            grp_indent = grp_box.row()
            grp_indent.separator(factor=2.0)
            grp_col = grp_indent.column()
            grp_col.label(text="Group Children", icon='THREE_DOTS')
            row = grp_col.row()
            row.template_list(
                "PIEBAKERY_UL_group_items", "", item, "group_items",
                item, "active_group_item_index", rows=3,
            )
            col = row.column(align=True)
            col.operator("piebakery.group_item_add",    icon='ADD',    text="")
            col.operator("piebakery.group_item_remove", icon='REMOVE', text="")
            col.operator("piebakery.group_item_duplicate", icon='DUPLICATE', text="")
            col.separator()
            col.operator("piebakery.group_item_move", icon='TRIA_UP',
                         text="").direction = 'UP'
            col.operator("piebakery.group_item_move", icon='TRIA_DOWN',
                         text="").direction = 'DOWN'

            # -- Selected group child detail --
            if item.active_group_item_index < len(item.group_items):
                child = item.group_items[item.active_group_item_index]
                child_box = grp_col.box()
                child_indent = child_box.row()
                child_indent.separator(factor=2.0)
                child_col = child_indent.column()
                child_col.prop(child, "item_type")
                child_col.prop(child, "label")
                child_col.prop(child, "icon")
                child_col.prop(child, "label_hidden")
                if child.item_type == 'OPERATOR':
                    child_col.prop(child, "operator_id")
                    child_col.prop(child, "operator_props")
                elif child.item_type == 'COMMAND':
                    child_col.prop(child, "command")
                elif child.item_type == 'VALUE':
                    child_col.prop(child, "data_path")
                    child_col.prop(child, "read_only")
                elif child.item_type == 'SUBMENU':
                    child_col.prop(child, "submenu_name")
                elif child.item_type == 'PALETTE':
                    child_col.prop_search(child, "palette_name",
                                             bpy.data, "palettes")

classes = (
    PIEBAKERY_UL_menus,
    PIEBAKERY_UL_items,
    PIEBAKERY_UL_group_items,
    PIEBAKERY_MT_pie,
    PieBakeryPreferences,
)
