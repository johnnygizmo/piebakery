import bpy

_addon_keymaps = []

def register_keymaps():
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

def unregister_keymaps():
    for km, kmi in _addon_keymaps:
        km.keymap_items.remove(kmi)
    _addon_keymaps.clear()

def refresh_keymaps():
    unregister_keymaps()
    register_keymaps()

def delayed_keymap_init():
    """Called once via bpy.app.timers after registration."""
    register_keymaps()
    return None
