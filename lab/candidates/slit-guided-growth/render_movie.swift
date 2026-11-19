#!/usr/bin/env swift

import AppKit
import AVFoundation
import CoreVideo
import Foundation

func fail(_ message: String) -> Never {
    FileHandle.standardError.write(Data("error: \(message)\n".utf8))
    exit(1)
}

guard CommandLine.arguments.count == 3 else {
    fail("usage: render_movie.swift OUTPUT_DIR MOVIE.mp4")
}
let root = URL(fileURLWithPath: CommandLine.arguments[1], isDirectory: true)
let movie = URL(fileURLWithPath: CommandLine.arguments[2])
guard !FileManager.default.fileExists(atPath: movie.path) else { fail("movie exists") }

func pgm(_ url: URL) throws -> [UInt8] {
    let data = try Data(contentsOf: url)
    let marker = Data("\n255\n".utf8)
    guard let range = data.range(of: marker) else { fail("invalid PGM: \(url.path)") }
    let pixels = data[range.upperBound...]
    guard pixels.count == 192 * 128 else { fail("unexpected PGM dimensions") }
    return Array(pixels)
}

let coherentField = try pgm(root.appendingPathComponent("coherent-field.pgm"))
let taggedField = try pgm(root.appendingPathComponent("path-tagged-field.pgm"))
let conditions = ["coherent", "path-tagged", "coherent-to-tagged", "tagged-to-coherent"]
let stateValues = [0] + stride(from: 120, through: 12_000, by: 120)
var states: [String: [[UInt8]]] = [:]
for condition in conditions {
    states[condition] = try stateValues.map { value in
        try pgm(root.appendingPathComponent("frames/\(condition)/state-\(String(format: "%04d", value)).pgm"))
    }
}

struct Scene { let chapter: Int; let stateIndex: Int }
var scenes: [Scene] = []
for chapter in 0..<2 {
    scenes.append(contentsOf: Array(repeating: Scene(chapter: chapter, stateIndex: 0), count: 8))
    for stateIndex in stateValues.indices {
        scenes.append(contentsOf: Array(repeating: Scene(chapter: chapter, stateIndex: stateIndex), count: 3))
        if stateValues[stateIndex] == 6_000 {
            scenes.append(contentsOf: Array(repeating: Scene(chapter: chapter, stateIndex: stateIndex), count: 16))
        }
    }
    scenes.append(contentsOf: Array(repeating: Scene(chapter: chapter, stateIndex: stateValues.count - 1), count: 20))
}

let width = 1_920
let height = 1_080
let fps: Int32 = 12
let writer = try AVAssetWriter(outputURL: movie, fileType: .mp4)
let input = AVAssetWriterInput(mediaType: .video, outputSettings: [
    AVVideoCodecKey: AVVideoCodecType.h264,
    AVVideoWidthKey: width,
    AVVideoHeightKey: height,
    AVVideoCompressionPropertiesKey: [
        AVVideoAverageBitRateKey: 14_000_000,
        AVVideoProfileLevelKey: AVVideoProfileLevelH264HighAutoLevel,
        AVVideoMaxKeyFrameIntervalKey: Int(fps),
    ],
])
input.expectsMediaDataInRealTime = false
let adaptor = AVAssetWriterInputPixelBufferAdaptor(assetWriterInput: input, sourcePixelBufferAttributes: [
    kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA,
    kCVPixelBufferWidthKey as String: width,
    kCVPixelBufferHeightKey as String: height,
    kCVPixelBufferIOSurfacePropertiesKey as String: [:],
])
guard writer.canAdd(input) else { fail("cannot add input") }
writer.add(input)
guard writer.startWriting() else { fail(writer.error?.localizedDescription ?? "writer failed") }
writer.startSession(atSourceTime: .zero)

func text(_ value: String, x: CGFloat, y: CGFloat, width: CGFloat, size: CGFloat,
          color: NSColor = .white, weight: NSFont.Weight = .regular) {
    NSAttributedString(string: value, attributes: [
        .font: NSFont.systemFont(ofSize: size, weight: weight),
        .foregroundColor: color,
    ]).draw(in: CGRect(x: x, y: y, width: width, height: 70))
}

let colorSpace = CGColorSpaceCreateDeviceRGB()
let bitmapInfo = CGBitmapInfo.byteOrder32Little.union(CGBitmapInfo(rawValue: CGImageAlphaInfo.premultipliedFirst.rawValue))
let cell = 4
let gridWidth = 192 * cell
let gridHeight = 128 * cell

for (movieIndex, scene) in scenes.enumerated() {
    while !input.isReadyForMoreMediaData { usleep(1_000) }
    guard let pool = adaptor.pixelBufferPool else { fail("pixel pool unavailable") }
    var optional: CVPixelBuffer?
    guard CVPixelBufferPoolCreatePixelBuffer(nil, pool, &optional) == kCVReturnSuccess,
          let buffer = optional else { fail("pixel allocation failed") }
    CVPixelBufferLockBaseAddress(buffer, [])
    guard let base = CVPixelBufferGetBaseAddress(buffer), let context = CGContext(
        data: base, width: width, height: height, bitsPerComponent: 8,
        bytesPerRow: CVPixelBufferGetBytesPerRow(buffer), space: colorSpace,
        bitmapInfo: bitmapInfo.rawValue) else { fail("context failed") }
    context.setFillColor(CGColor(red: 0.015, green: 0.022, blue: 0.037, alpha: 1))
    context.fill(CGRect(x: 0, y: 0, width: width, height: height))
    context.translateBy(x: 0, y: CGFloat(height)); context.scaleBy(x: 1, y: -1)
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.current = NSGraphicsContext(cgContext: context, flipped: true)

    let step = stateValues[scene.stateIndex]
    let pair = scene.chapter == 0 ? ["coherent", "path-tagged"] : ["coherent-to-tagged", "tagged-to-coherent"]
    text("SLIT-GUIDED CONDUCTIVE GROWTH", x: 34, y: 24, width: 1_300, size: 30, weight: .bold)
    text("Two sparse optical apertures · exact 192×128 material · matched seeds and 12,000-cell budget",
         x: 34, y: 66, width: 1_520, size: 18, color: NSColor(calibratedWhite: 0.76, alpha: 1))
    text("STEP \(step) / 12,000", x: 1_570, y: 31, width: 320, size: 24,
         color: NSColor(calibratedRed: 0.30, green: 0.91, blue: 0.76, alpha: 1), weight: .bold)

    for (column, condition) in pair.enumerated() {
        let x0 = 45 + column * 950
        let y0 = 132
        let topology = states[condition]![scene.stateIndex]
        let coherentNow = condition == "coherent" || (condition == "coherent-to-tagged" && step < 6_000) || (condition == "tagged-to-coherent" && step >= 6_000)
        let field = coherentNow ? coherentField : taggedField
        context.setFillColor(CGColor(red: 0.025, green: 0.045, blue: 0.070, alpha: 1))
        context.fill(CGRect(x: x0 - 12, y: y0 - 12, width: gridWidth + 24, height: gridHeight + 24))
        for y in 0..<128 {
            for x in 0..<192 {
                let i = y * 192 + x
                let intensity = CGFloat(field[i]) / 255.0
                let occupied = topology[i] > 0
                let red = occupied ? 0.92 : 0.02 + 0.10 * intensity
                let green = occupied ? 0.96 : 0.035 + 0.46 * intensity
                let blue = occupied ? 1.00 : 0.08 + 0.72 * intensity
                context.setFillColor(CGColor(red: red, green: green, blue: blue, alpha: 1))
                context.fill(CGRect(x: x0 + x * cell, y: y0 + y * cell, width: cell, height: cell))
            }
        }
        context.setFillColor(CGColor(red: 0.65, green: 0.67, blue: 0.70, alpha: 1))
        for y in 0..<128 where !(44...52).contains(y) && !(76...84).contains(y) {
            context.fill(CGRect(x: x0 + 36 * cell, y: y0 + y * cell, width: cell, height: cell))
        }
        context.setFillColor(CGColor(red: 0.25, green: 0.92, blue: 0.75, alpha: 1))
        context.fill(CGRect(x: x0 - 10, y: y0, width: 6, height: gridHeight))
        context.setFillColor(CGColor(red: 0.98, green: 0.40, blue: 0.28, alpha: 1))
        context.fill(CGRect(x: x0 + gridWidth + 4, y: y0, width: 6, height: gridHeight))

        let title: String
        let ensemble: String
        let connected: Bool
        switch condition {
        case "coherent": title = "COHERENT TWO-SLIT"; ensemble = "26 / 32 connected · median 10,190.5"; connected = step >= 11_113
        case "path-tagged": title = "PATH-TAGGED TWO-SLIT"; ensemble = "0 / 32 connected within budget"; connected = false
        case "coherent-to-tagged": title = "COHERENT → PATH-TAGGED"; ensemble = "0 / 32 connected"; connected = false
        default: title = "PATH-TAGGED → COHERENT"; ensemble = "32 / 32 connected · median 10,958.5"; connected = step >= 11_151
        }
        text(title, x: CGFloat(x0), y: 680, width: 820, size: 25, weight: .bold)
        text(coherentNow ? "coherent field active" : "path-tagged field active", x: CGFloat(x0), y: 722, width: 820, size: 18,
             color: coherentNow ? NSColor(calibratedRed: 0.40, green: 0.82, blue: 1.0, alpha: 1) : NSColor(calibratedRed: 0.83, green: 0.68, blue: 1.0, alpha: 1))
        text(ensemble, x: CGFloat(x0), y: 758, width: 840, size: 18, color: NSColor(calibratedWhite: 0.78, alpha: 1))
        text(connected ? "SEED 319 CONNECTED" : "SEED 319 DEVELOPING", x: CGFloat(x0), y: 800, width: 820, size: 22,
             color: connected ? NSColor(calibratedRed: 0.32, green: 0.94, blue: 0.62, alpha: 1) : NSColor(calibratedRed: 1.0, green: 0.68, blue: 0.25, alpha: 1), weight: .bold)
        if step == 6_000 && (condition.contains("-to-")) {
            text("FIELD CONDITION SWITCH", x: CGFloat(x0), y: 845, width: 820, size: 24,
                 color: NSColor(calibratedRed: 1.0, green: 0.78, blue: 0.22, alpha: 1), weight: .bold)
        }
    }
    text("Blue field = present optical intensity · white = developed conductor · gray = barrier · openings = two sparse fibre apertures",
         x: 48, y: 1_016, width: 1_820, size: 17, color: NSColor(calibratedWhite: 0.72, alpha: 1))
    NSGraphicsContext.restoreGraphicsState()
    CVPixelBufferUnlockBaseAddress(buffer, [])
    guard adaptor.append(buffer, withPresentationTime: CMTime(value: CMTimeValue(movieIndex), timescale: fps)) else {
        fail(writer.error?.localizedDescription ?? "append failed")
    }
}

input.markAsFinished()
let semaphore = DispatchSemaphore(value: 0)
writer.finishWriting { semaphore.signal() }
semaphore.wait()
guard writer.status == .completed else { fail(writer.error?.localizedDescription ?? "writer incomplete") }
print(movie.path)
