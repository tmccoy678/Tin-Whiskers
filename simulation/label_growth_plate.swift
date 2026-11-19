import AppKit

guard CommandLine.arguments.count == 8 else {
    fputs("usage: label_growth_plate INPUT OUTPUT TITLE CONDITION STATS TASK NOTE\n", stderr)
    exit(2)
}

let input = CommandLine.arguments[1]
let output = CommandLine.arguments[2]
let title = CommandLine.arguments[3]
let condition = CommandLine.arguments[4]
let stats = CommandLine.arguments[5]
let task = CommandLine.arguments[6]
let note = CommandLine.arguments[7]

guard let image = NSImage(contentsOfFile: input) else {
    fputs("could not read input image\n", stderr)
    exit(1)
}

let width = 1600
let height = 1100
let bitmap = NSBitmapImageRep(
    bitmapDataPlanes: nil,
    pixelsWide: width,
    pixelsHigh: height,
    bitsPerSample: 8,
    samplesPerPixel: 4,
    hasAlpha: true,
    isPlanar: false,
    colorSpaceName: .deviceRGB,
    bytesPerRow: 0,
    bitsPerPixel: 0
)!

NSGraphicsContext.saveGraphicsState()
NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: bitmap)
NSColor(calibratedRed: 0.02, green: 0.03, blue: 0.05, alpha: 1).setFill()
NSRect(x: 0, y: 0, width: width, height: height).fill()

let paragraph = NSMutableParagraphStyle()
paragraph.alignment = .center
func draw(_ text: String, y: CGFloat, size: CGFloat, color: NSColor, weight: NSFont.Weight = .regular) {
    let attributes: [NSAttributedString.Key: Any] = [
        .font: NSFont.systemFont(ofSize: size, weight: weight),
        .foregroundColor: color,
        .paragraphStyle: paragraph
    ]
    text.draw(in: NSRect(x: 60, y: y, width: 1480, height: size * 1.5), withAttributes: attributes)
}

draw(title, y: 1010, size: 42, color: .white, weight: .bold)
draw(condition, y: 956, size: 24, color: NSColor(calibratedRed: 0.72, green: 0.82, blue: 0.90, alpha: 1))

NSGraphicsContext.current?.imageInterpolation = .none
let targetHeight: CGFloat = 690
let targetWidth = targetHeight * image.size.width / image.size.height
let imageRect = NSRect(x: (CGFloat(width) - targetWidth) / 2, y: 225, width: targetWidth, height: targetHeight)
image.draw(in: imageRect)

let irColor = NSColor(calibratedRed: 225/255, green: 193/255, blue: 110/255, alpha: 1)
let nbColor = NSColor(calibratedRed: 121/255, green: 215/255, blue: 1, alpha: 1)
irColor.setFill()
NSBezierPath(ovalIn: NSRect(x: 540, y: 175, width: 22, height: 22)).fill()
nbColor.setFill()
NSBezierPath(ovalIn: NSRect(x: 920, y: 175, width: 22, height: 22)).fill()

let legendLeft = NSMutableParagraphStyle(); legendLeft.alignment = .left
let legendAttributes: [NSAttributedString.Key: Any] = [
    .font: NSFont.systemFont(ofSize: 22, weight: .semibold),
    .foregroundColor: NSColor.white,
    .paragraphStyle: legendLeft
]
"IRIDIUM lineage".draw(in: NSRect(x: 575, y: 169, width: 250, height: 35), withAttributes: legendAttributes)
"NIOBIUM lineage".draw(in: NSRect(x: 955, y: 169, width: 250, height: 35), withAttributes: legendAttributes)

draw(stats, y: 118, size: 20, color: .white, weight: .semibold)
draw(task, y: 78, size: 19, color: NSColor(calibratedRed: 0.66, green: 0.91, blue: 0.75, alpha: 1), weight: .semibold)
draw(note, y: 36, size: 16, color: NSColor(calibratedWhite: 0.67, alpha: 1))

NSGraphicsContext.restoreGraphicsState()
guard let data = bitmap.representation(using: .png, properties: [:]) else {
    fputs("could not encode output\n", stderr)
    exit(1)
}
try data.write(to: URL(fileURLWithPath: output))
