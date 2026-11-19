#!/usr/bin/env swift

import AppKit
import AVFoundation
import CoreVideo
import Foundation

struct Layout {
    static let sourceWidth = 1280
    static let sourceHeight = 860
    static let sourceX = 64
    static let sourceY = 54
    static let anatomyWidth = 1152
    static let anatomyHeight = 768

    static let width = 1440
    static let height = 960
    static let anatomyX = 144
    static let anatomyY = 124
    static let fps: Int32 = 4
    static let sourceStates = 37
    static let endpointHoldFrames = 4
}

enum StimulusStatus: String {
    case active = "ACTIVE"
    case inactive = "INACTIVE"
    case off = "OFF"
}

struct Arguments {
    let source: URL
    let output: URL
}

func fail(_ message: String) -> Never {
    FileHandle.standardError.write(Data("error: \(message)\n".utf8))
    exit(1)
}

func parseArguments() -> Arguments {
    var source: URL?
    var output: URL?
    var index = 1
    let args = CommandLine.arguments
    while index < args.count {
        switch args[index] {
        case "--source":
            guard index + 1 < args.count else { fail("--source needs a path") }
            source = URL(fileURLWithPath: args[index + 1], isDirectory: true)
            index += 2
        case "--output":
            guard index + 1 < args.count else { fail("--output needs a path") }
            output = URL(fileURLWithPath: args[index + 1], isDirectory: true)
            index += 2
        default:
            fail("unknown argument \(args[index])")
        }
    }
    guard let source, let output else {
        fail("usage: render_candidate.swift --source FRAME_DIR --output OUTPUT_DIR")
    }
    return Arguments(source: source, output: output)
}

func loadBitmap(_ url: URL) -> NSBitmapImageRep {
    guard let data = try? Data(contentsOf: url),
          let bitmap = NSBitmapImageRep(data: data) else {
        fail("cannot read \(url.path)")
    }
    return bitmap
}

func makeBitmap(width: Int, height: Int) -> NSBitmapImageRep {
    guard let bitmap = NSBitmapImageRep(
        bitmapDataPlanes: nil,
        pixelsWide: width,
        pixelsHigh: height,
        bitsPerSample: 8,
        samplesPerPixel: 3,
        hasAlpha: false,
        isPlanar: false,
        colorSpaceName: .calibratedRGB,
        bytesPerRow: width * 4,
        bitsPerPixel: 32
    ) else {
        fail("cannot allocate \(width)x\(height) bitmap")
    }
    return bitmap
}

func fillBackground(_ bitmap: NSBitmapImageRep) {
    guard let data = bitmap.bitmapData else { fail("bitmap has no writable data") }
    for y in 0..<bitmap.pixelsHigh {
        let row = data.advanced(by: y * bitmap.bytesPerRow)
        for x in 0..<bitmap.pixelsWide {
            let pixel = row.advanced(by: x * 4)
            pixel[0] = 5
            pixel[1] = 7
            pixel[2] = 11
            pixel[3] = 0
        }
    }
}

func rgb(_ bitmap: NSBitmapImageRep, x: Int, y: Int) -> (Int, Int, Int) {
    guard let color = bitmap.colorAt(x: x, y: y)?.usingColorSpace(.deviceRGB) else {
        fail("cannot sample stimulus at \(x),\(y)")
    }
    return (
        Int((color.redComponent * 255).rounded()),
        Int((color.greenComponent * 255).rounded()),
        Int((color.blueComponent * 255).rounded())
    )
}

func classifyStimulus(_ sample: (Int, Int, Int)) -> StimulusStatus {
    if sample.0 == 0 && sample.1 == 0 && sample.2 == 0 {
        return .off
    }
    return sample.1 >= 180 ? .active : .inactive
}

func appKitRect(x: CGFloat, top: CGFloat, width: CGFloat, height: CGFloat) -> NSRect {
    NSRect(x: x, y: CGFloat(Layout.height) - top - height, width: width, height: height)
}

func drawText(
    _ text: String,
    in rect: NSRect,
    font: NSFont,
    color: NSColor,
    alignment: NSTextAlignment = .left
) {
    let paragraph = NSMutableParagraphStyle()
    paragraph.alignment = alignment
    paragraph.lineBreakMode = .byClipping
    NSAttributedString(
        string: text,
        attributes: [
            .font: font,
            .foregroundColor: color,
            .paragraphStyle: paragraph,
        ]
    ).draw(in: rect)
}

func drawCircle(centerX: CGFloat, centerTopY: CGFloat, status: StimulusStatus, radius: CGFloat = 9) {
    let rect = NSRect(
        x: centerX - radius,
        y: CGFloat(Layout.height) - centerTopY - radius,
        width: radius * 2,
        height: radius * 2
    )
    let path = NSBezierPath(ovalIn: rect)
    switch status {
    case .active:
        NSColor(calibratedRed: 171 / 255, green: 234 / 255, blue: 204 / 255, alpha: 1).setFill()
        path.fill()
    case .inactive:
        NSColor(calibratedRed: 95 / 255, green: 133 / 255, blue: 115 / 255, alpha: 1).setFill()
        path.fill()
    case .off:
        NSColor.black.setFill()
        path.fill()
        NSColor(calibratedRed: 95 / 255, green: 133 / 255, blue: 115 / 255, alpha: 1).setStroke()
        path.lineWidth = 2
        path.stroke()
    }
}

func copyAnatomy(source: NSBitmapImageRep, destination: NSBitmapImageRep) {
    guard source.pixelsWide == Layout.sourceWidth,
          source.pixelsHigh == Layout.sourceHeight,
          source.bitsPerPixel == 32,
          destination.bitsPerPixel == 32,
          let sourceData = source.bitmapData,
          let destinationData = destination.bitmapData else {
        fail("unexpected bitmap layout while copying anatomy")
    }
    for row in 0..<Layout.anatomyHeight {
        let sourceRow = sourceData.advanced(
            by: (Layout.sourceY + row) * source.bytesPerRow + Layout.sourceX * 4
        )
        let destinationRow = destinationData.advanced(
            by: (Layout.anatomyY + row) * destination.bytesPerRow + Layout.anatomyX * 4
        )
        memcpy(destinationRow, sourceRow, Layout.anatomyWidth * 4)
    }
}

func renderFrame(source: NSBitmapImageRep, state: Int) -> NSBitmapImageRep {
    let bitmap = makeBitmap(width: Layout.width, height: Layout.height)
    fillBackground(bitmap)

    guard let graphics = NSGraphicsContext(bitmapImageRep: bitmap) else {
        fail("cannot create drawing context")
    }
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.current = graphics

    let white = NSColor.white
    let teal = NSColor(calibratedRed: 157 / 255, green: 231 / 255, blue: 193 / 255, alpha: 1)
    let muted = NSColor(calibratedRed: 160 / 255, green: 177 / 255, blue: 190 / 255, alpha: 1)
    let titleFont = NSFont(name: "Arial", size: 30) ?? .systemFont(ofSize: 30, weight: .medium)
    let subtitleFont = NSFont(name: "Arial Bold", size: 19) ?? .boldSystemFont(ofSize: 19)
    let labelFont = NSFont(name: "Arial Bold", size: 16) ?? .boldSystemFont(ofSize: 16)
    let smallFont = NSFont(name: "Arial", size: 14) ?? .systemFont(ofSize: 14)
    let stateFont = NSFont(name: "Arial", size: 20) ?? .monospacedDigitSystemFont(ofSize: 20, weight: .regular)

    drawText(
        "CURRENT-DRIVEN REMODELING · TWO-FIBER PROBE",
        in: appKitRect(x: 120, top: 12, width: 1200, height: 38),
        font: titleFont,
        color: white,
        alignment: .center
    )
    drawText(
        "FIXED-RULE CONTROL · LITERAL LATTICE",
        in: appKitRect(x: 220, top: 52, width: 1000, height: 28),
        font: subtitleFont,
        color: teal,
        alignment: .center
    )
    drawText(
        "SOURCE · 1 V →",
        in: appKitRect(x: 144, top: 92, width: 280, height: 24),
        font: labelFont,
        color: muted
    )
    drawText(
        "← SINK · 0 V",
        in: appKitRect(x: 1016, top: 92, width: 280, height: 24),
        font: labelFont,
        color: muted,
        alignment: .right
    )

    let upperStatus = classifyStimulus(rgb(source, x: 46, y: 396))
    let lowerStatus = classifyStimulus(rgb(source, x: 46, y: 516))
    let upperY = CGFloat(Layout.anatomyY + (396 - Layout.sourceY))
    let lowerY = CGFloat(Layout.anatomyY + (516 - Layout.sourceY))

    drawText(
        "UPPER\n\(upperStatus.rawValue)",
        in: appKitRect(x: 4, top: upperY - 19, width: 108, height: 42),
        font: smallFont,
        color: white,
        alignment: .right
    )
    drawCircle(centerX: 128, centerTopY: upperY, status: upperStatus)
    drawText(
        "LOWER\n\(lowerStatus.rawValue)",
        in: appKitRect(x: 4, top: lowerY - 19, width: 108, height: 42),
        font: smallFont,
        color: white,
        alignment: .right
    )
    drawCircle(centerX: 128, centerTopY: lowerY, status: lowerStatus)

    drawText(
        "WHITE = OCCUPIED LATTICE",
        in: appKitRect(x: 144, top: 910, width: 280, height: 24),
        font: labelFont,
        color: muted
    )
    drawCircle(centerX: 488, centerTopY: 921, status: .active, radius: 7)
    drawText("ACTIVE", in: appKitRect(x: 502, top: 910, width: 74, height: 24), font: smallFont, color: white)
    drawCircle(centerX: 600, centerTopY: 921, status: .inactive, radius: 7)
    drawText("INACTIVE", in: appKitRect(x: 614, top: 910, width: 86, height: 24), font: smallFont, color: white)
    drawCircle(centerX: 728, centerTopY: 921, status: .off, radius: 7)
    drawText("OFF", in: appKitRect(x: 742, top: 910, width: 48, height: 24), font: smallFont, color: white)
    drawText(
        String(format: "EPOCH %02d / 36", state),
        in: appKitRect(x: 1040, top: 906, width: 256, height: 32),
        font: stateFont,
        color: teal,
        alignment: .right
    )

    NSGraphicsContext.restoreGraphicsState()

    // Copy last so no label, antialiasing fringe, or guide can change anatomy pixels.
    copyAnatomy(source: source, destination: bitmap)
    return bitmap
}

func savePNG(_ bitmap: NSBitmapImageRep, to url: URL) {
    guard let data = bitmap.representation(using: .png, properties: [:]) else {
        fail("cannot encode \(url.lastPathComponent)")
    }
    do {
        try data.write(to: url, options: .atomic)
    } catch {
        fail("cannot write \(url.path): \(error)")
    }
}

func makeRGBPixelBuffer(_ bitmap: NSBitmapImageRep) -> CVPixelBuffer {
    var maybeBuffer: CVPixelBuffer?
    let attributes: [String: Any] = [
        kCVPixelBufferWidthKey as String: Layout.width,
        kCVPixelBufferHeightKey as String: Layout.height,
    ]
    let result = CVPixelBufferCreate(
        kCFAllocatorDefault,
        Layout.width,
        Layout.height,
        kCVPixelFormatType_24RGB,
        attributes as CFDictionary,
        &maybeBuffer
    )
    guard result == kCVReturnSuccess, let pixelBuffer = maybeBuffer else {
        fail("cannot allocate raw RGB movie frame")
    }
    guard let source = bitmap.bitmapData else { fail("frame bitmap has no data") }
    CVPixelBufferLockBaseAddress(pixelBuffer, [])
    guard let destination = CVPixelBufferGetBaseAddress(pixelBuffer) else {
        fail("pixel buffer has no data")
    }
    let destinationBytesPerRow = CVPixelBufferGetBytesPerRow(pixelBuffer)
    for y in 0..<Layout.height {
        let sourceRow = source.advanced(by: y * bitmap.bytesPerRow)
        let destinationRow = destination.advanced(by: y * destinationBytesPerRow).assumingMemoryBound(to: UInt8.self)
        for x in 0..<Layout.width {
            let input = sourceRow.advanced(by: x * 4)
            let output = destinationRow.advanced(by: x * 3)
            output[0] = input[0]
            output[1] = input[1]
            output[2] = input[2]
        }
    }
    CVPixelBufferUnlockBaseAddress(pixelBuffer, [])
    return pixelBuffer
}

func encodeLosslessMovie(frameURLs: [URL], output: URL) {
    try? FileManager.default.removeItem(at: output)
    let writer: AVAssetWriter
    do {
        writer = try AVAssetWriter(outputURL: output, fileType: .mov)
    } catch {
        fail("cannot create movie writer: \(error)")
    }

    guard let firstURL = frameURLs.first else { fail("movie has no frames") }
    let firstBuffer = makeRGBPixelBuffer(loadBitmap(firstURL))
    var formatDescription: CMVideoFormatDescription?
    let descriptionStatus = CMVideoFormatDescriptionCreateForImageBuffer(
        allocator: kCFAllocatorDefault,
        imageBuffer: firstBuffer,
        formatDescriptionOut: &formatDescription
    )
    guard descriptionStatus == noErr, let formatDescription else {
        fail("cannot describe raw RGB movie frames")
    }
    let input = AVAssetWriterInput(
        mediaType: .video,
        outputSettings: nil,
        sourceFormatHint: formatDescription
    )
    input.expectsMediaDataInRealTime = false
    guard writer.canAdd(input) else { fail("cannot add movie input") }
    writer.add(input)
    guard writer.startWriting() else { fail("cannot start movie writer: \(writer.error?.localizedDescription ?? "unknown")") }
    writer.startSession(atSourceTime: .zero)

    for (index, frameURL) in frameURLs.enumerated() {
        while !input.isReadyForMoreMediaData {
            Thread.sleep(forTimeInterval: 0.002)
        }
        let pixelBuffer = index == 0 ? firstBuffer : makeRGBPixelBuffer(loadBitmap(frameURL))
        var timing = CMSampleTimingInfo(
            duration: CMTime(value: 1, timescale: Layout.fps),
            presentationTimeStamp: CMTime(value: CMTimeValue(index), timescale: Layout.fps),
            decodeTimeStamp: .invalid
        )
        var maybeSample: CMSampleBuffer?
        let sampleStatus = CMSampleBufferCreateReadyWithImageBuffer(
            allocator: kCFAllocatorDefault,
            imageBuffer: pixelBuffer,
            formatDescription: formatDescription,
            sampleTiming: &timing,
            sampleBufferOut: &maybeSample
        )
        guard sampleStatus == noErr, let sample = maybeSample else {
            fail("cannot create movie sample \(index)")
        }
        guard input.append(sample) else {
            fail("cannot append movie frame \(index): \(writer.error?.localizedDescription ?? "unknown")")
        }
    }
    let end = CMTime(value: CMTimeValue(frameURLs.count), timescale: Layout.fps)
    writer.endSession(atSourceTime: end)
    input.markAsFinished()
    let finished = DispatchSemaphore(value: 0)
    writer.finishWriting { finished.signal() }
    finished.wait()
    guard writer.status == .completed else {
        fail("movie writer failed: \(writer.error?.localizedDescription ?? "unknown")")
    }
}

let arguments = parseArguments()
let fileManager = FileManager.default
let stateDirectory = arguments.output.appendingPathComponent("states", isDirectory: true)
do {
    try fileManager.createDirectory(at: stateDirectory, withIntermediateDirectories: true)
} catch {
    fail("cannot create output directory: \(error)")
}

var stateURLs: [URL] = []
for state in 0..<Layout.sourceStates {
    let sourceURL = arguments.source.appendingPathComponent(String(format: "frame.%04d.png", state))
    let source = loadBitmap(sourceURL)
    guard source.pixelsWide == Layout.sourceWidth, source.pixelsHigh == Layout.sourceHeight else {
        fail("unexpected source resolution at state \(state)")
    }
    let outputURL = stateDirectory.appendingPathComponent(String(format: "frame.%04d.png", state))
    savePNG(renderFrame(source: source, state: state), to: outputURL)
    stateURLs.append(outputURL)
}

let movieFrameURLs = Array(repeating: stateURLs[0], count: Layout.endpointHoldFrames)
    + Array(stateURLs[1...35])
    + Array(repeating: stateURLs[36], count: Layout.endpointHoldFrames)
let movieURL = arguments.output.appendingPathComponent("current-fiber-remodel-presentation-lossless-rgb.mov")
encodeLosslessMovie(frameURLs: movieFrameURLs, output: movieURL)

print("rendered_states=\(stateURLs.count)")
print("movie_frames=\(movieFrameURLs.count)")
print("movie_fps=\(Layout.fps)")
print("movie_duration_seconds=\(Double(movieFrameURLs.count) / Double(Layout.fps))")
print("movie_codec=uncompressed 24-bit RGB lossless all-intra")
print("movie=\(movieURL.path)")
