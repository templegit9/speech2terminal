// Renders menu-bar template glyphs + an app icon from SF Symbols (MeetingIntro-style).
// Run: swift packaging/make_icons.swift
import AppKit

let root = FileManager.default.currentDirectoryPath
let menuDir = "\(root)/src/speech2terminal/resources/icons"
let iconsetDir = "\(root)/packaging/AppIcon.iconset"
try? FileManager.default.createDirectory(atPath: menuDir, withIntermediateDirectories: true)
try? FileManager.default.createDirectory(atPath: iconsetDir, withIntermediateDirectories: true)

func symbolImage(_ name: String, pt: CGFloat, weight: NSFont.Weight = .regular) -> NSImage {
    let cfg = NSImage.SymbolConfiguration(pointSize: pt, weight: weight)
    return NSImage(systemSymbolName: name, accessibilityDescription: nil)!
        .withSymbolConfiguration(cfg)!
}

func tint(_ img: NSImage, _ color: NSColor) -> NSImage {
    let out = NSImage(size: img.size)
    out.lockFocus()
    color.set()
    let r = NSRect(origin: .zero, size: img.size)
    img.draw(in: r)
    r.fill(using: .sourceAtop)
    out.unlockFocus()
    return out
}

func writePNG(_ img: NSImage, _ path: String, px: Int) {
    let rep = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: px, pixelsHigh: px,
        bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true, isPlanar: false,
        colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: rep)
    let dst = NSRect(x: 0, y: 0, width: px, height: px)
    let s = img.size
    let scale = min(CGFloat(px) / s.width, CGFloat(px) / s.height)
    let w = s.width * scale, h = s.height * scale
    img.draw(in: NSRect(x: (CGFloat(px)-w)/2, y: (CGFloat(px)-h)/2, width: w, height: h))
    _ = dst
    NSGraphicsContext.restoreGraphicsState()
    try! rep.representation(using: .png, properties: [:])!.write(to: URL(fileURLWithPath: path))
}

// --- menu-bar template glyphs (black; rumps template=True adapts to light/dark) ---
let menuSymbols = [
    "idle": "mic.fill",
    "recording": "record.circle.fill",
    "busy": "waveform",
    "confirming": "questionmark.circle.fill",
]
for (state, sym) in menuSymbols {
    let img = tint(symbolImage(sym, pt: 16, weight: .medium), .black)
    writePNG(img, "\(menuDir)/\(state).png", px: 36)  // ~18pt @2x for the menu bar
}
print("menu glyphs -> \(menuDir)")

// --- app icon: white mic on a blue rounded-rect gradient ---
func appIcon(_ px: Int) -> NSImage {
    let out = NSImage(size: NSSize(width: px, height: px))
    out.lockFocus()
    let rect = NSRect(x: 0, y: 0, width: px, height: px)
    let radius = CGFloat(px) * 0.2237  // macOS icon corner ratio
    let path = NSBezierPath(roundedRect: rect, xRadius: radius, yRadius: radius)
    let grad = NSGradient(colors: [
        NSColor(calibratedRed: 0.30, green: 0.45, blue: 0.95, alpha: 1),
        NSColor(calibratedRed: 0.13, green: 0.20, blue: 0.55, alpha: 1),
    ])!
    grad.draw(in: path, angle: -90)
    let glyph = tint(symbolImage("mic.fill", pt: CGFloat(px) * 0.5, weight: .semibold), .white)
    let g = glyph.size
    let scale = (CGFloat(px) * 0.5) / max(g.width, g.height)
    let w = g.width * scale, h = g.height * scale
    glyph.draw(in: NSRect(x: (CGFloat(px)-w)/2, y: (CGFloat(px)-h)/2, width: w, height: h))
    out.unlockFocus()
    return out
}
for (px, name) in [(16,"16x16"),(32,"16x16@2x"),(32,"32x32"),(64,"32x32@2x"),
                   (128,"128x128"),(256,"128x128@2x"),(256,"256x256"),
                   (512,"256x256@2x"),(512,"512x512"),(1024,"512x512@2x")] {
    writePNG(appIcon(px), "\(iconsetDir)/icon_\(name).png", px: px)
}
print("app iconset -> \(iconsetDir)")

// --- glowing RGB mic frames (NON-template, colored) shown while voice is active ---
let frames = 12
let gpx = 44
for i in 0..<frames {
    let hue = CGFloat(i) / CGFloat(frames)
    let color = NSColor(calibratedHue: hue, saturation: 0.95, brightness: 1.0, alpha: 1)
    let out = NSImage(size: NSSize(width: gpx, height: gpx))
    out.lockFocus()
    let shadow = NSShadow()
    shadow.shadowColor = color.withAlphaComponent(0.95)
    shadow.shadowBlurRadius = CGFloat(gpx) * 0.24
    shadow.shadowOffset = .zero
    shadow.set()
    let glyph = tint(symbolImage("mic.fill", pt: CGFloat(gpx) * 0.5, weight: .bold), color)
    let g = glyph.size
    let scale = (CGFloat(gpx) * 0.52) / max(g.width, g.height)
    let w = g.width * scale, h = g.height * scale
    let r = NSRect(x: (CGFloat(gpx)-w)/2, y: (CGFloat(gpx)-h)/2, width: w, height: h)
    glyph.draw(in: r)
    glyph.draw(in: r)  // double-draw -> brighter glow
    out.unlockFocus()
    writePNG(out, "\(menuDir)/glow_\(String(format: "%02d", i)).png", px: gpx)
}
print("glow frames -> \(menuDir)")
