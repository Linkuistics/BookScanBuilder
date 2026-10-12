import AppKit
import CoreGraphics

// https://developer.apple.com/documentation/appkit/nsscreen/backingscalefactor
for screen in NSScreen.screens {
    let number = screen.deviceDescription[NSDeviceDescriptionKey("NSScreenNumber")] as? NSNumber
    let displayID = number?.uint32Value ?? 0
    print("screen=\(screen.localizedName) display_id=\(displayID) frame_points=\(screen.frame) backing_scale=\(screen.backingScaleFactor) framebuffer_pixels=\(CGDisplayPixelsWide(displayID))x\(CGDisplayPixelsHigh(displayID))")
}
// https://developer.apple.com/documentation/coregraphics/cgwindowlistcopywindowinfo(_:_:)
if let windows = CGWindowListCopyWindowInfo(.optionOnScreenOnly, kCGNullWindowID) as? [[String: Any]] {
    for window in windows where window[kCGWindowOwnerName as String] as? String == "Preview" {
        print(window)
    }
}
