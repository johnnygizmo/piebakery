# SPDX-License-Identifier: GPL-3.0-or-later

import bpy

from . import prop
from . import ui
from . import operators
from . import keybinds

_classes = prop.classes + operators.classes + ui.classes

def register():
    for cls in _classes:
        bpy.utils.register_class(cls)
    bpy.app.timers.register(keybinds.delayed_keymap_init, first_interval=0.5)

def unregister():
    keybinds.unregister_keymaps()
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
