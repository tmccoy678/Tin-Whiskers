#!/usr/bin/env swift

import AppKit
import AVFoundation
import CoreVideo
import CryptoKit
import Foundation

enum Mode: String, Codable {
    case fixed = "FIXED-RULE CONTROL"
    case adaptive = "ADAPTIVE CONTROLLER"
}

enum Stimulus: String, Codable {
    case active = "ACTIVE"
    case inactive = "INACTIVE"
    case off = "OFF"
    case notApplicable = "N/A"
}

enum Decision: String, Codable {
    case fixed = "FIXED"
    case warmup = "WARMUP"
    case explore = "EXPLORE"
    case exploit = "EXPLOIT"
    case initial = "INITIAL"
}

enum Palette: String, Codable {
    case darkLiteral = "DARK_LITERAL"
    case lightAnatomy = "LIGHT_ANATOMY"
}

struct LatticeROI: Codable {
    let x: Int
    let y: Int
    let width: Int
    let height: Int
    let cell_scale: Int
    let display_scale: Int?
}

struct PresentationManifest: Codable {
    let schema_version: Int
    let title: String
    let mode: Mode
    let state_count: Int
    let fps: Int32
    let source_value: String
    let sink_value: String
    let source_frames: String
    let actions_file: String
    let lattice_roi: LatticeROI
    let frame_prefix: String?
    let action_label: String?
    let palette: Palette?
    let write_movie: Bool?
    let state_index_base: Int?
}

struct Action: Codable {
    let state: Int
    let upper: Stimulus
    let lower: Stimulus
    let decision: Decision
    let connection: String?
}

struct ActionsManifest: Codable {
    let schema_version: Int
    let state_count: Int
    let actions: [Action]
}

struct Layout {
    let width: Int
    let height: Int
    let anatomyX = 144
    let anatomyY = 124
    let anatomyWidth: Int
    let anatomyHeight: Int

    init(roi: LatticeROI) {
        let scale = roi.display_scale ?? 1
        anatomyWidth = roi.width * scale
        anatomyHeight = roi.height * scale
        width = anatomyWidth + 288
        height = anatomyHeight + 192
    }
}

struct Arguments {
    let manifest: URL
    let output: URL
}

func fail(_ message: String) -> Never {
    FileHandle.standardError.write(Data("error: \(message)\n".utf8))
    exit(1)
}

func parseArguments() -> Arguments {
    var manifest: URL?
    var output: URL?
    var index = 1
    let args = CommandLine.arguments
    while index < args.count {
        switch args[index] {
        case "--manifest":
            guard index + 1 < args.count else { fail("--manifest needs a path") }
            manifest = URL(fileURLWithPath: args[index + 1])
            index += 2
        case "--output":
            guard index + 1 < args.count else { fail("--output needs a path") }
            output = URL(fileURLWithPath: args[index + 1], isDirectory: true)
            index += 2
        default:
            fail("unknown argument \(args[index])")
        }
    }
    guard let manifest, let output else {
        fail("usage: evidence_presenter.swift --manifest PRESENTATION.json --output OUTPUT_DIR")
    }
    return Arguments(manifest: manifest, output: output)
}

func decodeJSON<T: Decodable>(_ type: T.Type, from url: URL) -> T {
    do {
        return try JSONDecoder().decode(type, from: Data(contentsOf: url))
    } catch {
        fail("cannot decode \(url.path): \(error)")
    }
}

func sha256(_ url: URL) -> String {
    guard let data = try? Data(contentsOf: url) else { fail("cannot hash \(url.path)") }
    return SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined()
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

func fillBackground(_ bitmap: NSBitmapImageRep, palette: Palette) {
    guard let data = bitmap.bitmapData else { fail("bitmap has no writable data") }
    let background: (UInt8, UInt8, UInt8) = palette == .lightAnatomy ? (247, 244, 236) : (5, 7, 11)
    for y in 0..<bitmap.pixelsHigh {
        let row = data.advanced(by: y * bitmap.bytesPerRow)
        for x in 0..<bitmap.pixelsWide {
            let pixel = row.advanced(by: x * 4)
            pixel[0] = background.0
            pixel[1] = background.1
            pixel[2] = background.2
            pixel[3] = 0
        }
    }
}

func topRect(layout: Layout, x: CGFloat, top: CGFloat, width: CGFloat, height: CGFloat) -> NSRect {
    NSRect(x: x, y: CGFloat(layout.height) - top - height, width: width, height: height)
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
        attributes: [.font: font, .foregroundColor: color, .paragraphStyle: paragraph]
    ).draw(in: rect)
}

func drawCircle(
    layout: Layout,
    centerX: CGFloat,
    centerTopY: CGFloat,
    status: Stimulus,
    palette: Palette,
    radius: CGFloat = 8
) {
    let rect = NSRect(
        x: centerX - radius,
        y: CGFloat(layout.height) - centerTopY - radius,
        width: radius * 2,
        height: radius * 2
    )
    let path = NSBezierPath(ovalIn: rect)
    switch status {
    case .active:
        (palette == .lightAnatomy
            ? NSColor(calibratedRed: 18 / 255, green: 112 / 255, blue: 77 / 255, alpha: 1)
            : NSColor(calibratedRed: 171 / 255, green: 234 / 255, blue: 204 / 255, alpha: 1)).setFill()
        path.fill()
    case .inactive:
        (palette == .lightAnatomy
            ? NSColor(calibratedRed: 95 / 255, green: 119 / 255, blue: 106 / 255, alpha: 1)
            : NSColor(calibratedRed: 95 / 255, green: 133 / 255, blue: 115 / 255, alpha: 1)).setFill()
        path.fill()
    case .off:
        (palette == .lightAnatomy ? NSColor(calibratedWhite: 0.97, alpha: 1) : NSColor.black).setFill()
        path.fill()
        NSColor(calibratedRed: 95 / 255, green: 133 / 255, blue: 115 / 255, alpha: 1).setStroke()
        path.lineWidth = 2
        path.stroke()
    case .notApplicable:
        (palette == .lightAnatomy ? NSColor(calibratedWhite: 0.82, alpha: 1) : NSColor(calibratedWhite: 0.25, alpha: 1)).setFill()
        path.fill()
        NSColor(calibratedWhite: 0.48, alpha: 1).setStroke()
        path.lineWidth = 2
        path.stroke()
    }
}

func copyAnatomy(
    source: NSBitmapImageRep,
    destination: NSBitmapImageRep,
    roi: LatticeROI,
    layout: Layout,
    palette: Palette
) {
    let scale = roi.display_scale ?? 1
    guard source.bitsPerPixel == 32,
          destination.bitsPerPixel == 32,
          roi.x >= 0,
          roi.y >= 0,
          roi.x + roi.width <= source.pixelsWide,
          roi.y + roi.height <= source.pixelsHigh,
          let sourceData = source.bitmapData,
          let destinationData = destination.bitmapData else {
        fail("invalid lattice ROI or bitmap layout")
    }
    for row in 0..<roi.height {
        let sourceRow = sourceData.advanced(by: (roi.y + row) * source.bytesPerRow)
        for column in 0..<roi.width {
            let input = sourceRow.advanced(by: (roi.x + column) * 4)
            let outputColor: (UInt8, UInt8, UInt8)
            if palette == .lightAnatomy {
                let black = input[0] == 0 && input[1] == 0 && input[2] == 0
                let white = input[0] == 255 && input[1] == 255 && input[2] == 255
                guard black || white else { fail("LIGHT_ANATOMY requires a literal black/white source") }
                outputColor = white ? (20, 28, 24) : (247, 244, 236)
            } else {
                outputColor = (input[0], input[1], input[2])
            }
            for dy in 0..<scale {
                let destinationRow = destinationData.advanced(
                    by: (layout.anatomyY + row * scale + dy) * destination.bytesPerRow
                )
                for dx in 0..<scale {
                    let output = destinationRow.advanced(
                        by: (layout.anatomyX + column * scale + dx) * 4
                    )
                    output[0] = outputColor.0
                    output[1] = outputColor.1
                    output[2] = outputColor.2
                    output[3] = 0
                }
            }
        }
    }
}

func renderFrame(
    source: NSBitmapImageRep,
    manifest: PresentationManifest,
    action: Action,
    layout: Layout
) -> NSBitmapImageRep {
    let palette = manifest.palette ?? .darkLiteral
    let bitmap = makeBitmap(width: layout.width, height: layout.height)
    fillBackground(bitmap, palette: palette)
    guard let graphics = NSGraphicsContext(bitmapImageRep: bitmap) else {
        fail("cannot create drawing context")
    }
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.current = graphics

    let white = palette == .lightAnatomy ? NSColor(calibratedWhite: 0.08, alpha: 1) : NSColor.white
    let teal = palette == .lightAnatomy
        ? NSColor(calibratedRed: 18 / 255, green: 105 / 255, blue: 73 / 255, alpha: 1)
        : NSColor(calibratedRed: 157 / 255, green: 231 / 255, blue: 193 / 255, alpha: 1)
    let muted = palette == .lightAnatomy
        ? NSColor(calibratedRed: 65 / 255, green: 82 / 255, blue: 90 / 255, alpha: 1)
        : NSColor(calibratedRed: 160 / 255, green: 177 / 255, blue: 190 / 255, alpha: 1)
    let titleSize = min(30.0, max(20.0, Double(layout.width) / 42.0))
    let titleFont = NSFont(name: "Arial", size: titleSize) ?? .systemFont(ofSize: titleSize)
    let subtitleFont = NSFont(name: "Arial Bold", size: 18) ?? .boldSystemFont(ofSize: 18)
    let labelFont = NSFont(name: "Arial Bold", size: 15) ?? .boldSystemFont(ofSize: 15)
    let smallFont = NSFont(name: "Arial", size: 13) ?? .systemFont(ofSize: 13)
    let stateFont = NSFont(name: "Arial", size: 18) ?? .monospacedDigitSystemFont(ofSize: 18, weight: .regular)

    drawText(
        manifest.title,
        in: topRect(layout: layout, x: 40, top: 12, width: CGFloat(layout.width - 80), height: 36),
        font: titleFont,
        color: white,
        alignment: .center
    )
    drawText(
        palette == .lightAnatomy
            ? "\(manifest.mode.rawValue) · LIGHT ANATOMY · NO CURRENT/HEAT"
            : "\(manifest.mode.rawValue) · LITERAL LATTICE",
        in: topRect(layout: layout, x: 60, top: 52, width: CGFloat(layout.width - 120), height: 26),
        font: subtitleFont,
        color: teal,
        alignment: .center
    )
    drawText(
        "SOURCE · \(manifest.source_value) →",
        in: topRect(layout: layout, x: 144, top: 92, width: CGFloat(min(280, layout.anatomyWidth / 2)), height: 24),
        font: labelFont,
        color: muted
    )
    drawText(
        "← SINK · \(manifest.sink_value)",
        in: topRect(
            layout: layout,
            x: CGFloat(layout.width - 144 - min(280, layout.anatomyWidth / 2)),
            top: 92,
            width: CGFloat(min(280, layout.anatomyWidth / 2)),
            height: 24
        ),
        font: labelFont,
        color: muted,
        alignment: .right
    )

    let upperY = CGFloat(layout.anatomyY) + CGFloat(layout.anatomyHeight) * 0.42
    let lowerY = CGFloat(layout.anatomyY) + CGFloat(layout.anatomyHeight) * 0.62
    drawText(
        "UPPER\n\(action.upper.rawValue)",
        in: topRect(layout: layout, x: 4, top: upperY - 19, width: 108, height: 42),
        font: smallFont,
        color: white,
        alignment: .right
    )
    drawCircle(layout: layout, centerX: 128, centerTopY: upperY, status: action.upper, palette: palette)
    drawText(
        "LOWER\n\(action.lower.rawValue)",
        in: topRect(layout: layout, x: 4, top: lowerY - 19, width: 108, height: 42),
        font: smallFont,
        color: white,
        alignment: .right
    )
    drawCircle(layout: layout, centerX: 128, centerTopY: lowerY, status: action.lower, palette: palette)

    let bottom = CGFloat(layout.anatomyY + layout.anatomyHeight + 14)
    drawText(
        palette == .lightAnatomy ? "DARK = OCCUPIED" : "WHITE = LATTICE",
        in: topRect(layout: layout, x: 144, top: bottom, width: 170, height: 22),
        font: labelFont,
        color: muted
    )
    let actionWidth = layout.width >= 1200 ? 420 : 200
    drawText(
        [manifest.action_label ?? "ACTION", action.decision.rawValue, action.connection]
            .compactMap { $0 }.joined(separator: " · "),
        in: topRect(
            layout: layout,
            x: CGFloat((layout.width - actionWidth) / 2),
            top: bottom,
            width: CGFloat(actionWidth),
            height: 22
        ),
        font: labelFont,
        color: white,
        alignment: .center
    )
    let stateBase = manifest.state_index_base ?? 1
    drawText(
        String(
            format: "STATE %03d OF %03d",
            action.state + stateBase,
            manifest.state_count - 1 + stateBase
        ),
        in: topRect(layout: layout, x: CGFloat(layout.width - 344), top: bottom - 2, width: 200, height: 26),
        font: stateFont,
        color: teal,
        alignment: .right
    )

    let legendTop = bottom + 28
    drawCircle(layout: layout, centerX: CGFloat(layout.width / 2 - 150), centerTopY: legendTop + 8, status: .active, palette: palette, radius: 6)
    drawText("ACTIVE", in: topRect(layout: layout, x: CGFloat(layout.width / 2 - 140), top: legendTop, width: 60, height: 20), font: smallFont, color: white)
    drawCircle(layout: layout, centerX: CGFloat(layout.width / 2 - 65), centerTopY: legendTop + 8, status: .inactive, palette: palette, radius: 6)
    drawText("INACTIVE", in: topRect(layout: layout, x: CGFloat(layout.width / 2 - 55), top: legendTop, width: 72, height: 20), font: smallFont, color: white)
    drawCircle(layout: layout, centerX: CGFloat(layout.width / 2 + 37), centerTopY: legendTop + 8, status: .off, palette: palette, radius: 6)
    drawText("OFF", in: topRect(layout: layout, x: CGFloat(layout.width / 2 + 47), top: legendTop, width: 36, height: 20), font: smallFont, color: white)
    drawCircle(layout: layout, centerX: CGFloat(layout.width / 2 + 103), centerTopY: legendTop + 8, status: .notApplicable, palette: palette, radius: 6)
    drawText("N/A", in: topRect(layout: layout, x: CGFloat(layout.width / 2 + 113), top: legendTop, width: 36, height: 20), font: smallFont, color: white)

    NSGraphicsContext.restoreGraphicsState()
    copyAnatomy(
        source: source,
        destination: bitmap,
        roi: manifest.lattice_roi,
        layout: layout,
        palette: palette
    )
    return bitmap
}

func savePNG(_ bitmap: NSBitmapImageRep, to url: URL) {
    guard let data = bitmap.representation(using: .png, properties: [:]) else {
        fail("cannot encode \(url.lastPathComponent)")
    }
    do { try data.write(to: url, options: .atomic) }
    catch { fail("cannot write \(url.path): \(error)") }
}

func makeRGBPixelBuffer(_ bitmap: NSBitmapImageRep, layout: Layout) -> CVPixelBuffer {
    var maybeBuffer: CVPixelBuffer?
    let result = CVPixelBufferCreate(
        kCFAllocatorDefault,
        layout.width,
        layout.height,
        kCVPixelFormatType_24RGB,
        nil,
        &maybeBuffer
    )
    guard result == kCVReturnSuccess, let pixelBuffer = maybeBuffer,
          let source = bitmap.bitmapData else {
        fail("cannot allocate raw RGB movie frame")
    }
    CVPixelBufferLockBaseAddress(pixelBuffer, [])
    guard let destination = CVPixelBufferGetBaseAddress(pixelBuffer) else {
        fail("movie pixel buffer has no data")
    }
    let destinationBytesPerRow = CVPixelBufferGetBytesPerRow(pixelBuffer)
    for y in 0..<layout.height {
        let sourceRow = source.advanced(by: y * bitmap.bytesPerRow)
        let destinationRow = destination.advanced(by: y * destinationBytesPerRow).assumingMemoryBound(to: UInt8.self)
        for x in 0..<layout.width {
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

func encodeLosslessMovie(frameURLs: [URL], fps: Int32, layout: Layout, output: URL) {
    try? FileManager.default.removeItem(at: output)
    let writer: AVAssetWriter
    do { writer = try AVAssetWriter(outputURL: output, fileType: .mov) }
    catch { fail("cannot create movie writer: \(error)") }
    guard let firstURL = frameURLs.first else { fail("movie has no frames") }
    let firstBuffer = makeRGBPixelBuffer(loadBitmap(firstURL), layout: layout)
    var formatDescription: CMVideoFormatDescription?
    guard CMVideoFormatDescriptionCreateForImageBuffer(
        allocator: kCFAllocatorDefault,
        imageBuffer: firstBuffer,
        formatDescriptionOut: &formatDescription
    ) == noErr, let formatDescription else {
        fail("cannot describe raw RGB movie frames")
    }
    let input = AVAssetWriterInput(mediaType: .video, outputSettings: nil, sourceFormatHint: formatDescription)
    input.expectsMediaDataInRealTime = false
    guard writer.canAdd(input) else { fail("cannot add movie input") }
    writer.add(input)
    guard writer.startWriting() else { fail("cannot start movie writer") }
    writer.startSession(atSourceTime: .zero)
    for (index, frameURL) in frameURLs.enumerated() {
        while !input.isReadyForMoreMediaData { Thread.sleep(forTimeInterval: 0.002) }
        let buffer = index == 0 ? firstBuffer : makeRGBPixelBuffer(loadBitmap(frameURL), layout: layout)
        var timing = CMSampleTimingInfo(
            duration: CMTime(value: 1, timescale: fps),
            presentationTimeStamp: CMTime(value: CMTimeValue(index), timescale: fps),
            decodeTimeStamp: .invalid
        )
        var maybeSample: CMSampleBuffer?
        guard CMSampleBufferCreateReadyWithImageBuffer(
            allocator: kCFAllocatorDefault,
            imageBuffer: buffer,
            formatDescription: formatDescription,
            sampleTiming: &timing,
            sampleBufferOut: &maybeSample
        ) == noErr, let sample = maybeSample else {
            fail("cannot create movie sample \(index)")
        }
        guard input.append(sample) else { fail("cannot append movie frame \(index)") }
    }
    writer.endSession(atSourceTime: CMTime(value: CMTimeValue(frameURLs.count), timescale: fps))
    input.markAsFinished()
    let finished = DispatchSemaphore(value: 0)
    writer.finishWriting { finished.signal() }
    finished.wait()
    guard writer.status == .completed else {
        fail("movie writer failed: \(writer.error?.localizedDescription ?? "unknown")")
    }
}

let arguments = parseArguments()
let manifest = decodeJSON(PresentationManifest.self, from: arguments.manifest)
guard manifest.schema_version == 1,
      manifest.state_count >= 2,
      manifest.fps > 0,
      !manifest.title.contains("\n"),
      !manifest.source_value.isEmpty,
      !manifest.sink_value.isEmpty,
      manifest.lattice_roi.width > 0,
      manifest.lattice_roi.height > 0,
      manifest.lattice_roi.cell_scale > 0,
      (manifest.lattice_roi.display_scale ?? 1) > 0,
      manifest.lattice_roi.width % manifest.lattice_roi.cell_scale == 0,
      manifest.lattice_roi.height % manifest.lattice_roi.cell_scale == 0 else {
    fail("invalid presentation manifest")
}

let base = arguments.manifest.deletingLastPathComponent()
let actionsURL = base.appendingPathComponent(manifest.actions_file)
let sourceDirectory = manifest.source_frames.hasPrefix("/")
    ? URL(fileURLWithPath: manifest.source_frames, isDirectory: true)
    : base.appendingPathComponent(manifest.source_frames, isDirectory: true)
let actions = decodeJSON(ActionsManifest.self, from: actionsURL)
guard actions.schema_version == 1,
      actions.state_count == manifest.state_count,
      actions.actions.count == manifest.state_count else {
    fail("action manifest state count does not match presentation")
}
for (index, action) in actions.actions.enumerated() {
    guard action.state == index else { fail("action states must be exact and contiguous") }
    switch manifest.mode {
    case .fixed where action.decision != .fixed:
        fail("fixed control contains non-fixed action at state \(index)")
    case .adaptive where action.decision == .fixed:
        fail("adaptive controller contains fixed action at state \(index)")
    default:
        break
    }
}

let framePrefix = manifest.frame_prefix ?? "frame."
let expectedNames = (0..<manifest.state_count).map { String(format: "%@%04d.png", framePrefix, $0) }
let actualNames = ((try? FileManager.default.contentsOfDirectory(atPath: sourceDirectory.path)) ?? [])
    .filter { $0.hasSuffix(".png") }.sorted()
guard actualNames == expectedNames else {
    fail("source frame set does not exactly match state_count")
}

let layout = Layout(roi: manifest.lattice_roi)
let stateDirectory = arguments.output.appendingPathComponent("states", isDirectory: true)
try? FileManager.default.createDirectory(at: stateDirectory, withIntermediateDirectories: true)
var stateURLs: [URL] = []
var sourceHashes: [String: String] = [:]
for state in 0..<manifest.state_count {
    let sourceURL = sourceDirectory.appendingPathComponent(expectedNames[state])
    let source = loadBitmap(sourceURL)
    guard manifest.lattice_roi.x + manifest.lattice_roi.width <= source.pixelsWide,
          manifest.lattice_roi.y + manifest.lattice_roi.height <= source.pixelsHigh else {
        fail("lattice ROI exceeds source state \(state)")
    }
    let outputURL = stateDirectory.appendingPathComponent(expectedNames[state])
    savePNG(renderFrame(source: source, manifest: manifest, action: actions.actions[state], layout: layout), to: outputURL)
    stateURLs.append(outputURL)
    sourceHashes[expectedNames[state]] = sha256(sourceURL)
}

let writeMovie = manifest.write_movie ?? true
var movieFrames: [URL] = []
var movieURL: URL?
if writeMovie {
    let hold = Int(manifest.fps)
    let middle = manifest.state_count > 2 ? Array(stateURLs[1..<(manifest.state_count - 1)]) : []
    movieFrames = Array(repeating: stateURLs[0], count: hold)
        + middle
        + Array(repeating: stateURLs[manifest.state_count - 1], count: hold)
    let url = arguments.output.appendingPathComponent("presentation-lossless-rgb.mov")
    encodeLosslessMovie(frameURLs: movieFrames, fps: manifest.fps, layout: layout, output: url)
    movieURL = url
}

let metadata: [String: Any] = [
    "schema_version": 1,
    "mode": manifest.mode.rawValue,
    "title": manifest.title,
    "state_count": manifest.state_count,
    "fps": manifest.fps,
    "movie_frame_count": movieFrames.count,
    "movie_duration_seconds": Double(movieFrames.count) / Double(manifest.fps),
    "source_value": manifest.source_value,
    "sink_value": manifest.sink_value,
    "palette": (manifest.palette ?? .darkLiteral).rawValue,
    "write_movie": writeMovie,
    "state_index_base": manifest.state_index_base ?? 1,
    "lattice_roi_source": [
        "x": manifest.lattice_roi.x,
        "y": manifest.lattice_roi.y,
        "width": manifest.lattice_roi.width,
        "height": manifest.lattice_roi.height,
        "cell_scale": manifest.lattice_roi.cell_scale,
        "display_scale": manifest.lattice_roi.display_scale ?? 1,
    ],
    "lattice_roi_output": [
        "x": layout.anatomyX,
        "y": layout.anatomyY,
        "width": layout.anatomyWidth,
        "height": layout.anatomyHeight,
    ],
    "output_resolution": [layout.width, layout.height],
    "presentation_manifest_sha256": sha256(arguments.manifest),
    "actions_manifest_sha256": sha256(actionsURL),
    "source_frame_sha256": sourceHashes,
]
let metadataData = try JSONSerialization.data(withJSONObject: metadata, options: [.prettyPrinted, .sortedKeys])
try metadataData.write(to: arguments.output.appendingPathComponent("render-metadata.json"), options: .atomic)

print("mode=\(manifest.mode.rawValue)")
print("states=\(manifest.state_count)")
print("movie_frames=\(movieFrames.count)")
print("fps=\(manifest.fps)")
print("duration_seconds=\(Double(movieFrames.count) / Double(manifest.fps))")
print("resolution=\(layout.width)x\(layout.height)")
print("codec=uncompressed 24-bit RGB lossless all-intra")
print("movie=\(movieURL?.path ?? "not-written")")
