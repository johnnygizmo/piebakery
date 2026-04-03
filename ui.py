import json
import bpy
from bpy.types import UIList, Menu, AddonPreferences

from .prop import PieBakeryMenu
from . import state

# ── Shared icon/name maps used by UILists and the editor ──────────────────
_TYPE_ICONS = {
    'OPERATOR':    'PLAY',
    'COMMAND':     'CONSOLE',
    'VALUE':       'RNA',
    'SUBMENU':     'PIVOT_INDIVIDUAL',
    'PALETTE':     'COLOR',
    'GROUP':       'THREE_DOTS',
    'PLACEHOLDER': 'BLANK1',
}

# Human-readable position name for collection index 0-7.
# Layout in the visual grid:
#   [7:Top-L]  [0:Top]   [1:Top-R]
#   [6:Left]   [ pie ]   [2:Right]
#   [5:Bot-L]  [4:Bot]   [3:Bot-R]
_SLOT_NAMES = ["Top", "Top-R", "Right", "Bot-R", "Bot", "Bot-L", "Left", "Top-L"]

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

# ── Editor helpers ─────────────────────────────────────────────────────────

def _draw_slot_button(parent, menu, slot_idx):
    """Draw one pie slot as a selectable button, or a greyed label if empty."""
    name = _SLOT_NAMES[slot_idx]
    col = parent.column(align=True)
    col.scale_y = 2.5
    if slot_idx < len(menu.items):
        item = menu.items[slot_idx]
        ic = _TYPE_ICONS.get(item.item_type, 'DOT')
        label = item.label if item.label else f"({name})"
        is_active = slot_idx == menu.active_item_index
        op = col.operator("piebakery.select_slot",
                          text=label, icon=ic, depress=is_active)
        op.slot_index = slot_idx
    else:
        col.enabled = False
        col.label(text=f"({name})", icon='BLANK1')


def _draw_group_children(layout, item, context):
    """Draw the GROUP children list and the selected child's detail form."""
    grp_box = layout.box()
    grp_box.label(text="Group Children", icon='THREE_DOTS')
    row = grp_box.row()
    row.template_list(
        "PIEBAKERY_UL_group_items", "", item, "group_items",
        item, "active_group_item_index", rows=4,
    )
    btn_col = row.column(align=True)
    btn_col.operator("piebakery.group_item_add",       icon='ADD',       text="")
    btn_col.operator("piebakery.group_item_remove",    icon='REMOVE',    text="")
    btn_col.operator("piebakery.group_item_duplicate", icon='DUPLICATE', text="")
    btn_col.separator()
    btn_col.operator("piebakery.group_item_move",
                     icon='TRIA_UP',   text="").direction = 'UP'
    btn_col.operator("piebakery.group_item_move",
                     icon='TRIA_DOWN', text="").direction = 'DOWN'

    if item.active_group_item_index < len(item.group_items):
        child = item.group_items[item.active_group_item_index]
        child_box = grp_box.box()
        child_box.label(
            text=child.label or "Child Item",
            icon=_TYPE_ICONS.get(child.item_type, 'DOT'),
        )
        col = child_box.column(align=False)
        col.prop(child, "item_type")
        col.prop(child, "label")
        hrow = col.row(align=True)
        hrow.prop(child, "icon")
        hrow.prop(child, "label_hidden", text="Hide", toggle=True)
        col.separator(factor=0.5)
        if child.item_type == 'OPERATOR':
            col.prop(child, "operator_id")
            col.prop(child, "operator_props")
        elif child.item_type == 'COMMAND':
            cmd_row = col.row(align=True)
            cmd_row.prop(child, "command")
            op = cmd_row.operator("piebakery.copy_to_clipboard", text="", icon='COPYDOWN')
            op.text = child.command
        elif child.item_type == 'VALUE':
            col.prop(child, "data_path")
            col.prop(child, "read_only")
        elif child.item_type == 'SUBMENU':
            col.prop(child, "submenu_name")
        elif child.item_type == 'PALETTE':
            col.prop_search(child, "palette_name", bpy.data, "palettes")


def _draw_item_props(layout, item, context):
    """Draw the full property form for a PieBakeryItem."""
    box = layout.box()
    box.label(text="Item Properties", icon='PROPERTIES')
    col = box.column(align=False)
    col.prop(item, "item_type")
    col.separator(factor=0.5)
    col.prop(item, "label")
    hrow = col.row(align=True)
    hrow.prop(item, "icon")
    hrow.prop(item, "label_hidden", text="Hide", toggle=True)
    col.separator()

    if item.item_type == 'OPERATOR':
        col.prop(item, "operator_id")
        col.prop(item, "operator_props")
        if item.operator_props:
            col.operator("piebakery.parse_operator_text",
                         text="Parse Operator Text", icon='FILE_REFRESH')
    elif item.item_type == 'COMMAND':
        cmd_row = col.row(align=True)
        cmd_row.prop(item, "command")
        op = cmd_row.operator("piebakery.copy_to_clipboard", text="", icon='COPYDOWN')
        op.text = item.command
    elif item.item_type == 'VALUE':
        col.prop(item, "data_path")
        col.prop(item, "read_only")
    elif item.item_type == 'SUBMENU':
        col.prop(item, "submenu_name")
    elif item.item_type == 'PALETTE':
        col.prop_search(item, "palette_name", bpy.data, "palettes")
    elif item.item_type == 'GROUP':
        grow = col.row(align=True)
        grow.prop(item, "popout")
        grow.prop(item, "columns")
        col.separator()
        _draw_group_children(col, item, context)


def _draw_editor(layout, context):
    """Draw the full 3-column Pie Bakery editor (used by the editor operator)."""
    prefs = context.preferences.addons[__package__].preferences

    # Split into three columns: ~27 % | ~37 % | ~36 %
    outer = layout.split(factor=0.27)
    col_left = outer.column()
    inner = outer.split(factor=0.50)
    col_mid = inner.column()
    col_right = inner.column()

    # ── LEFT: menu list + hotkey + modes ──────────────────────────────────
    left_box = col_left.box()
    left_box.label(text="Menus", icon='PIVOT_INDIVIDUAL')
    lrow = left_box.row()
    lrow.template_list(
        "PIEBAKERY_UL_menus", "", prefs, "menus",
        prefs, "active_menu_index", rows=6,
    )
    lcol = lrow.column(align=True)
    lcol.operator("piebakery.menu_add",    icon='ADD',    text="")
    lcol.operator("piebakery.menu_remove", icon='REMOVE', text="")

    if prefs.active_menu_index < len(prefs.menus):
        menu = prefs.menus[prefs.active_menu_index]

        hk_box = left_box.box()
        hk_box.label(text="Hotkey", icon='KEYINGSET')
        hk_row = hk_box.row(align=True)
        hk_row.prop(menu, "hotkey_type", text="")
        hk_row.prop(menu, "hotkey_ctrl",  toggle=True)
        hk_row.prop(menu, "hotkey_shift", toggle=True)
        hk_row.prop(menu, "hotkey_alt",   toggle=True)
        hk_box.operator("piebakery.refresh_keymaps",
                        text="Apply Keymaps", icon='FILE_REFRESH')

        modes_box = left_box.box()
        modes_box.label(text="Active Modes  (empty = all)", icon='OBJECT_DATA')
        flow = modes_box.grid_flow(
            row_major=True, columns=2, even_columns=True,
            even_rows=False, align=True,
        )
        flow.prop(menu, "modes")

    left_box.separator(factor=0.5)
    io_row = left_box.row(align=True)
    io_row.operator("piebakery.export_menus", icon='EXPORT', text="Save")
    io_row.operator("piebakery.import_menus", icon='IMPORT', text="Load")

    # ── MID: visual pie grid + item list ──────────────────────────────────
    if prefs.active_menu_index >= len(prefs.menus):
        col_mid.box().label(text="Add or select a menu  →", icon='INFO')
    else:
        menu = prefs.menus[prefs.active_menu_index]

        pie_box = col_mid.box()
        pie_box.label(
            text=f"Pie Layout  ·  {len(menu.items)} / 8 slots filled",
            icon='COLLAPSEMENU',
        )

        # Row 1:  Top-L (7)   Top (0)   Top-R (1)
        r1 = pie_box.row(align=True)
        for s in [7, 0, 1]:
            _draw_slot_button(r1, menu, s)

        # Row 2:  Left (6)   [centre•]   Right (2)
        r2 = pie_box.row(align=True)
        _draw_slot_button(r2, menu, 6)
        ctr = r2.column()
        ctr.enabled = False
        ctr.scale_y = 2.5
        ctr.label(text="", icon='PIVOT_INDIVIDUAL')
        _draw_slot_button(r2, menu, 2)

        # Row 3:  Bot-L (5)   Bot (4)   Bot-R (3)
        r3 = pie_box.row(align=True)
        for s in [5, 4, 3]:
            _draw_slot_button(r3, menu, s)

        list_box = col_mid.box()
        list_box.label(text="Items  (list index = slot position)", icon='LINENUMBERS_ON')
        lr = list_box.row()
        lr.template_list(
            "PIEBAKERY_UL_items", "", menu, "items",
            menu, "active_item_index", rows=4,
        )
        lc = lr.column(align=True)
        lc.operator("piebakery.item_add",       icon='ADD',       text="")
        lc.operator("piebakery.item_remove",    icon='REMOVE',    text="")
        lc.operator("piebakery.item_duplicate", icon='DUPLICATE', text="")
        lc.separator()
        lc.operator("piebakery.item_move",
                    icon='TRIA_UP',   text="").direction = 'UP'
        lc.operator("piebakery.item_move",
                    icon='TRIA_DOWN', text="").direction = 'DOWN'

    # ── RIGHT: item detail ─────────────────────────────────────────────────
    if prefs.active_menu_index < len(prefs.menus):
        menu = prefs.menus[prefs.active_menu_index]
        if menu.active_item_index < len(menu.items):
            _draw_item_props(col_right, menu.items[menu.active_item_index], context)
        else:
            col_right.box().label(text="Select or add an item", icon='INFO')
    else:
        col_right.box().label(text="", icon='BLANK1')


class PieBakeryPreferences(AddonPreferences):
    bl_idname = __package__

    from bpy.props import CollectionProperty, IntProperty
    menus: CollectionProperty(type=PieBakeryMenu)  # type: ignore
    active_menu_index: IntProperty()  # type: ignore

    def draw(self, context):
        self.layout.operator(
            "piebakery.open_editor",
            text="Open Pie Bakery Editor",
            icon='COLLAPSEMENU',
        )

classes = (
    PIEBAKERY_UL_menus,
    PIEBAKERY_UL_items,
    PIEBAKERY_UL_group_items,
    PIEBAKERY_MT_pie,
    PieBakeryPreferences,
)
