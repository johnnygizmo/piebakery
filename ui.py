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
        if getattr(menu, "active_item_index", 0) >= len(menu.items):
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

classes = (
    PIEBAKERY_UL_menus,
    PIEBAKERY_UL_items,
    PIEBAKERY_MT_pie,
    PieBakeryPreferences,
)
