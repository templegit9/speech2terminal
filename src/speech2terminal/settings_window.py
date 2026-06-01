"""Native AppKit Settings window: hotkey recorder + all options.

Built with PyObjC. Must be driven from the main thread (the rumps menu callback
already runs there). The hotkey recorder captures any modifier+key combo via a
local event monitor, and a lone right-side modifier (Right Option/Cmd/Ctrl) for
push-to-talk style binding.

Helper methods are marked @objc.python_method so PyObjC doesn't try to expose
them as Obj-C selectors; only the action methods (recordHotkey:/save:/cancel:)
and the designated initializer are selectors.
"""

from __future__ import annotations

from typing import Callable

import objc
from AppKit import (
    NSApplication, NSBackingStoreBuffered, NSButton, NSEvent,
    NSEventMaskFlagsChanged, NSEventMaskKeyDown, NSEventModifierFlagCommand,
    NSEventModifierFlagControl, NSEventModifierFlagOption, NSEventModifierFlagShift,
    NSMakeRect, NSPopUpButton, NSTextField, NSWindow,
    NSWindowStyleMaskClosable, NSWindowStyleMaskTitled,
)
from Foundation import NSObject

from . import hotkey as hk
from .config import Config

TRIGGER_MODES = ["push_to_talk", "long_press", "auto_silence", "toggle"]
CONFIRM_MODES = ["voice", "paste_only", "overlay"]
TARGETS = ["paste", "tmux"]

_FN = {122: "f1", 120: "f2", 99: "f3", 118: "f4", 96: "f5", 97: "f6",
       98: "f7", 100: "f8", 101: "f9", 109: "f10", 103: "f11", 111: "f12"}
_RIGHT_MOD = {61: "alt_r", 54: "cmd_r", 62: "ctrl_r", 60: "shift_r"}
_SYM = {"ctrl": "⌃", "alt": "⌥", "shift": "⇧", "cmd": "⌘"}


@objc.python_method
def _keycode_name(code: int, chars: str | None):
    if code == 49:
        return "space"
    if code in _FN:
        return _FN[code]
    if chars and len(chars) == 1 and chars.isalnum():
        return chars.lower()
    return None


@objc.python_method
def _pretty(spec: str) -> str:
    mods, _ = hk.parse_spec(spec)
    main = spec.split("+")[-1]
    order = ["ctrl", "alt", "shift", "cmd"]
    pre = "".join(_SYM[m] for m in order if m in mods)
    side = {"alt_r": "⌥ (R)", "cmd_r": "⌘ (R)", "ctrl_r": "⌃ (R)", "shift_r": "⇧ (R)"}
    label = side.get(main) or {"space": "Space"}.get(main, main.upper())
    return f"{pre}{label}" if pre else label


@objc.python_method
def _int(s, default: int) -> int:
    try:
        return int(str(s).strip())
    except (ValueError, TypeError):
        return default


class SettingsController(NSObject):
    def initWithConfig_onApply_(self, cfg, on_apply):
        self = objc.super(SettingsController, self).init()
        if self is None:
            return None
        self._cfg = cfg
        self._on_apply = on_apply
        self._window = None
        self._monitor = None
        self._captured = cfg.hotkey
        return self

    @objc.python_method
    def show(self):
        if self._window is None:
            self._build()
        self._populate()
        NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
        self._window.makeKeyAndOrderFront_(None)

    @objc.python_method
    def _row_y(self, i):
        return 400 - i * 38

    @objc.python_method
    def _label(self, text, y):
        f = NSTextField.alloc().initWithFrame_(NSMakeRect(20, y, 134, 22))
        f.setStringValue_(text)
        f.setBezeled_(False)
        f.setDrawsBackground_(False)
        f.setEditable_(False)
        f.setSelectable_(False)
        f.setAlignment_(2)  # right
        self._content.addSubview_(f)

    @objc.python_method
    def _field(self, y, w=250):
        tf = NSTextField.alloc().initWithFrame_(NSMakeRect(166, y, w, 24))
        self._content.addSubview_(tf)
        return tf

    @objc.python_method
    def _popup(self, y, items):
        p = NSPopUpButton.alloc().initWithFrame_pullsDown_(
            NSMakeRect(164, y - 2, 254, 26), False)
        p.addItemsWithTitles_(items)
        self._content.addSubview_(p)
        return p

    @objc.python_method
    def _build(self):
        rect = NSMakeRect(0, 0, 460, 470)
        style = NSWindowStyleMaskTitled | NSWindowStyleMaskClosable
        win = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            rect, style, NSBackingStoreBuffered, False)
        win.setTitle_("speech2terminal — Settings")
        win.setReleasedWhenClosed_(False)
        self._content = win.contentView()

        self._label("Hotkey", self._row_y(0))
        self._hkButton = NSButton.alloc().initWithFrame_(
            NSMakeRect(164, self._row_y(0) - 2, 254, 28))
        self._hkButton.setBezelStyle_(1)
        self._hkButton.setTarget_(self)
        self._hkButton.setAction_("recordHotkey:")
        self._content.addSubview_(self._hkButton)

        self._label("Activation", self._row_y(1))
        self._trigger = self._popup(self._row_y(1), TRIGGER_MODES)

        self._label("Long-press (ms)", self._row_y(2))
        self._longms = self._field(self._row_y(2), 100)

        self._label("Confirm", self._row_y(3))
        self._confirm = self._popup(self._row_y(3), CONFIRM_MODES)

        self._label("Target", self._row_y(4))
        self._target = self._popup(self._row_y(4), TARGETS)

        self._label("tmux target", self._row_y(5))
        self._tmux = self._field(self._row_y(5))

        self._label("Whisper model", self._row_y(6))
        self._model = self._field(self._row_y(6))

        self._label("Silence (ms)", self._row_y(7))
        self._silence = self._field(self._row_y(7), 100)

        self._label("Confirm listen (s)", self._row_y(8))
        self._listen = self._field(self._row_y(8), 100)

        save = NSButton.alloc().initWithFrame_(NSMakeRect(330, 18, 110, 32))
        save.setTitle_("Save")
        save.setBezelStyle_(1)
        save.setKeyEquivalent_("\r")
        save.setTarget_(self)
        save.setAction_("save:")
        self._content.addSubview_(save)

        cancel = NSButton.alloc().initWithFrame_(NSMakeRect(214, 18, 110, 32))
        cancel.setTitle_("Cancel")
        cancel.setBezelStyle_(1)
        cancel.setTarget_(self)
        cancel.setAction_("cancel:")
        self._content.addSubview_(cancel)

        win.center()
        self._window = win

    @objc.python_method
    def _populate(self):
        c = self._cfg
        self._captured = c.hotkey
        self._hkButton.setTitle_(_pretty(c.hotkey))
        self._trigger.selectItemWithTitle_(c.trigger_mode)
        self._confirm.selectItemWithTitle_(c.confirm_mode)
        self._target.selectItemWithTitle_(c.target)
        self._longms.setStringValue_(str(c.long_press_ms))
        self._tmux.setStringValue_(c.tmux_target)
        self._model.setStringValue_(c.model)
        self._silence.setStringValue_(str(c.silence_ms))
        self._listen.setStringValue_(str(c.confirm_listen_s))

    # ---- hotkey recorder (Obj-C action) ----
    def recordHotkey_(self, sender):
        if self._monitor is not None:
            return
        self._hkButton.setTitle_("Press keys…")
        mask = NSEventMaskKeyDown | NSEventMaskFlagsChanged
        self._monitor = NSEvent.addLocalMonitorForEventsMatchingMask_handler_(
            mask, self._handle_event)

    @objc.python_method
    def _handle_event(self, event):
        flags = event.modifierFlags()
        mods = set()
        if flags & NSEventModifierFlagControl:
            mods.add("ctrl")
        if flags & NSEventModifierFlagOption:
            mods.add("alt")
        if flags & NSEventModifierFlagShift:
            mods.add("shift")
        if flags & NSEventModifierFlagCommand:
            mods.add("cmd")

        spec = None
        if event.type() == 10:  # NSEventTypeKeyDown
            name = _keycode_name(event.keyCode(), event.charactersIgnoringModifiers())
            if name:
                spec = hk.format_spec(mods, name)
        else:  # flagsChanged — lone right-side modifier as push-to-talk
            side = _RIGHT_MOD.get(event.keyCode())
            if side and len(mods) == 1:
                spec = side

        if spec:
            self._captured = spec
            self._hkButton.setTitle_(_pretty(spec))
            if self._monitor is not None:
                NSEvent.removeMonitor_(self._monitor)
                self._monitor = None
            return None  # consume
        return event

    # ---- buttons (Obj-C actions) ----
    def save_(self, sender):
        c = self._cfg
        c.hotkey = self._captured
        c.trigger_mode = self._trigger.titleOfSelectedItem()
        c.confirm_mode = self._confirm.titleOfSelectedItem()
        c.target = self._target.titleOfSelectedItem()
        c.tmux_target = self._tmux.stringValue()
        c.model = self._model.stringValue().strip() or c.model
        c.long_press_ms = _int(self._longms.stringValue(), c.long_press_ms)
        c.silence_ms = _int(self._silence.stringValue(), c.silence_ms)
        c.confirm_listen_s = _int(self._listen.stringValue(), c.confirm_listen_s)
        c.save()
        self._close()
        self._on_apply()

    def cancel_(self, sender):
        self._close()

    @objc.python_method
    def _close(self):
        if self._monitor is not None:
            NSEvent.removeMonitor_(self._monitor)
            self._monitor = None
        if self._window is not None:
            self._window.orderOut_(None)
