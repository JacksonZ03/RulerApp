# 15 cm on-screen ruler (1 mm ticks) for macOS, no manual calibration.

import sys
import objc

from AppKit import NSMenu, NSMenuItem, NSApp

def install_app_menu(app_name: str):
    menubar = NSMenu.alloc().init()

    app_menu_item = NSMenuItem.alloc().init()
    menubar.addItem_(app_menu_item)

    app_menu = NSMenu.alloc().init()
    quit_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
        f"Quit {app_name}", "terminate:", "q"
    )
    app_menu.addItem_(quit_item)

    app_menu_item.setSubmenu_(app_menu)
    NSApp.setMainMenu_(menubar)

def _missing_pyobjc(msg: str) -> None:
    print(msg)
    print("\nInstall (pip):   python3 -m pip install pyobjc")
    print("Install (conda): conda install -c conda-forge pyobjc-framework-cocoa pyobjc-framework-quartz")
    sys.exit(0)

try:
    from Foundation import NSObject, NSString, NSNotificationCenter
    from AppKit import (
        NSApp, NSApplication, NSApplicationActivationPolicyRegular,
        NSBackingStoreBuffered,
        NSColor, NSBezierPath, NSFont,
        NSFontAttributeName, NSForegroundColorAttributeName,
        NSMakeRect, NSRectFill,
        NSScreen, NSView, NSWindow,
        NSWindowStyleMaskTitled, NSWindowStyleMaskClosable, NSWindowStyleMaskMiniaturizable,
        NSApplicationDidChangeScreenParametersNotification,
        NSWindowDidChangeScreenNotification,
    )
    from Quartz import (
        CGDisplayScreenSize,
        CGDisplayCopyDisplayMode,
        CGDisplayModeGetPixelWidth,
    )
    from PyObjCTools import AppHelper
except Exception as e:
    _missing_pyobjc(f"PyObjC not available in this Python environment ({e}).")

# Fallback constants for 16-inch MacBook Pro (Liquid Retina XDR) if physical mm size cannot be read.
FALLBACK_PPI = 254.0

MM_PER_INCH = 25.4

RULER_LENGTH_MM = 150  # 15 cm
MARGIN_PT = 20.0
CONTENT_H_PT = 90.0

BASELINE_Y_PT = 28.0
TICK_SMALL_PT = 10.0
TICK_MED_PT = 18.0
TICK_LARGE_PT = 28.0


class RulerView(NSView):
    def initWithFrame_(self, frame):
        # IMPORTANT: use objc.super for Cocoa subclasses.
        self = objc.super(RulerView, self).initWithFrame_(frame)
        if self is None:
            return None
        self._points_per_mm = 5.0
        self._error_text = None
        return self

    def isOpaque(self):
        return True

    def acceptsFirstResponder(self):
        return True

    def keyDown_(self, event):
        chars = event.charactersIgnoringModifiers()
        if chars == "\x1b":  # Esc
            win = self.window()
            if win is not None:
                win.performClose_(None)
        else:
            objc.super(RulerView, self).keyDown_(event)

    def viewDidMoveToWindow(self):
        objc.super(RulerView, self).viewDidMoveToWindow()
        self.recomputeAndResize()

    def _display_id_for_screen(self, screen):
        dd = screen.deviceDescription()
        did = dd.objectForKey_("NSScreenNumber")  # CGDirectDisplayID
        try:
            return int(did)
        except Exception:
            return None

    def recomputeAndResize(self):
        win = self.window()
        screen = win.screen() if (win is not None and win.screen() is not None) else NSScreen.mainScreen()
        display_id = self._display_id_for_screen(screen) if screen is not None else None

        pixels_per_mm = None
        self._error_text = None

        if display_id is not None:
            try:
                size_mm = CGDisplayScreenSize(display_id)  # mm
                mm_w = float(size_mm.width)
                mode = CGDisplayCopyDisplayMode(display_id)
                px_w = float(CGDisplayModeGetPixelWidth(mode))

                if mm_w > 0.0 and px_w > 0.0:
                    pixels_per_mm = px_w / mm_w
            except Exception:
                pixels_per_mm = None

        if pixels_per_mm is None:
            pixels_per_mm = FALLBACK_PPI / MM_PER_INCH
            self._error_text = "Note: Using fallback PPI (system didn’t report physical mm size)."

        # Convert points↔pixels using backing-store conversion (handles HiDPI/scaled modes).
        try:
            backing = self.convertRectToBacking_(NSMakeRect(0, 0, 200, 1))
            pixels_per_point = float(backing.size.width) / 200.0
            if pixels_per_point <= 0:
                raise ValueError("pixels_per_point <= 0")
        except Exception:
            pixels_per_point = 2.0
            self._error_text = (self._error_text or "") + " (Also fell back to pixels/point=2.0.)"

        self._points_per_mm = pixels_per_mm / pixels_per_point

        length_pt = RULER_LENGTH_MM * self._points_per_mm
        content_w = MARGIN_PT * 2.0 + length_pt

        if win is not None:
            win.setContentSize_((content_w, CONTENT_H_PT))
        self.setNeedsDisplay_(True)

    def drawRect_(self, dirtyRect):
        NSColor.whiteColor().set()
        NSRectFill(dirtyRect)

        length_pt = RULER_LENGTH_MM * self._points_per_mm
        x0 = MARGIN_PT
        x1 = x0 + length_pt
        y0 = BASELINE_Y_PT

        NSColor.blackColor().set()

        path = NSBezierPath.bezierPath()
        path.setLineWidth_(1.0)

        # Baseline
        path.moveToPoint_((x0, y0))
        path.lineToPoint_((x1, y0))

        # Ticks
        for mm in range(0, RULER_LENGTH_MM + 1):
            x = x0 + mm * self._points_per_mm
            if mm % 10 == 0:
                h = TICK_LARGE_PT
            elif mm % 5 == 0:
                h = TICK_MED_PT
            else:
                h = TICK_SMALL_PT
            path.moveToPoint_((x, y0))
            path.lineToPoint_((x, y0 + h))

        path.stroke()

        # Labels (cm)
        font = NSFont.systemFontOfSize_(12.0)
        attrs = {
            NSFontAttributeName: font,
            NSForegroundColorAttributeName: NSColor.blackColor(),
        }

        for cm in range(0, (RULER_LENGTH_MM // 10) + 1):
            x = x0 + (cm * 10) * self._points_per_mm
            s = NSString.stringWithString_(str(cm))
            size = s.sizeWithAttributes_(attrs)
            s.drawAtPoint_withAttributes_((x - size.width / 2.0, y0 - size.height - 4.0), attrs)

        # Optional warning
        if self._error_text:
            warn_font = NSFont.systemFontOfSize_(11.0)
            warn_attrs = {
                NSFontAttributeName: warn_font,
                NSForegroundColorAttributeName: NSColor.grayColor(),
            }
            w = NSString.stringWithString_(self._error_text)
            w.drawAtPoint_withAttributes_((MARGIN_PT, CONTENT_H_PT - 18.0), warn_attrs)


class AppDelegate(NSObject):
    def applicationDidFinishLaunching_(self, notification):
        style = NSWindowStyleMaskTitled | NSWindowStyleMaskClosable | NSWindowStyleMaskMiniaturizable

        frame = NSMakeRect(0, 0, 800, CONTENT_H_PT)
        self.window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            frame, style, NSBackingStoreBuffered, False
        )
        self.window.setTitle_("15 cm Ruler")
        self.window.setReleasedWhenClosed_(False)

        self.view = RulerView.alloc().initWithFrame_(NSMakeRect(0, 0, frame.size.width, frame.size.height))
        self.window.setContentView_(self.view)
        self.window.center()
        self.window.makeKeyAndOrderFront_(None)

        nc = NSNotificationCenter.defaultCenter()
        nc.addObserver_selector_name_object_(
            self, "screenParamsChanged:", NSApplicationDidChangeScreenParametersNotification, None
        )
        nc.addObserver_selector_name_object_(
            self, "windowDidChangeScreen:", NSWindowDidChangeScreenNotification, self.window
        )

        NSApp.activateIgnoringOtherApps_(True)

    def screenParamsChanged_(self, notification):
        self.view.recomputeAndResize()

    def windowDidChangeScreen_(self, notification):
        self.view.recomputeAndResize()

    def applicationShouldTerminateAfterLastWindowClosed_(self, application):
        return True

if __name__ == "__main__":
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyRegular)
    install_app_menu("Ruler")
    delegate = AppDelegate.alloc().init()
    app.setDelegate_(delegate)
    AppHelper.runEventLoop()
