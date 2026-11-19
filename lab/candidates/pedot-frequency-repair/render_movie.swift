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
    fail("usage: frequency_repair_movie.swift RESULTS_DIR OUTPUT.mp4")
}

let results = URL(fileURLWithPath: CommandLine.arguments[1], isDirectory: true)
let output = URL(fileURLWithPath: CommandLine.arguments[2])
guard !FileManager.default.fileExists(atPath: output.path) else {
    fail("output exists: \(output.path)")
}

let frequencies = [10, 80, 320, 950]
var images: [Int: [CGImage]] = [:]
for frequency in frequencies {
    let directory = results.appendingPathComponent("pedot_frequency_repair_\(frequency)Hz_frames")
    var sequence: [CGImage] = []
    for epoch in 0...36 {
        let url = directory.appendingPathComponent(String(format: "frame.%04d.png", epoch))
        guard let representation = NSBitmapImageRep(data: try Data(contentsOf: url)),
              let image = representation.cgImage else {
            fail("could not read \(url.path)")
        }
        sequence.append(image)
    }
    images[frequency] = sequence
}

struct Scene { let chapter: Int; let epoch: Int }
var scenes: [Scene] = []
for chapter in 0..<2 {
    scenes.append(contentsOf: Array(repeating: Scene(chapter: chapter, epoch: 0), count: 8))
    for epoch in 0...36 {
        scenes.append(contentsOf: Array(repeating: Scene(chapter: chapter, epoch: epoch), count: 3))
        if chapter == 0 && (epoch == 5 || epoch == 18) {
            scenes.append(contentsOf: Array(repeating: Scene(chapter: chapter, epoch: epoch), count: 12))
        }
    }
    scenes.append(contentsOf: Array(repeating: Scene(chapter: chapter, epoch: 36), count: 20))
}

let width = 1_920
let height = 1_080
let fps: Int32 = 12
let writer = try AVAssetWriter(outputURL: output, fileType: .mp4)
let settings: [String: Any] = [
    AVVideoCodecKey: AVVideoCodecType.h264,
    AVVideoWidthKey: width,
    AVVideoHeightKey: height,
    AVVideoCompressionPropertiesKey: [
        AVVideoAverageBitRateKey: 14_000_000,
        AVVideoProfileLevelKey: AVVideoProfileLevelH264HighAutoLevel,
        AVVideoMaxKeyFrameIntervalKey: Int(fps),
    ],
]
let input = AVAssetWriterInput(mediaType: .video, outputSettings: settings)
input.expectsMediaDataInRealTime = false
let adaptor = AVAssetWriterInputPixelBufferAdaptor(
    assetWriterInput: input,
    sourcePixelBufferAttributes: [
        kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA,
        kCVPixelBufferWidthKey as String: width,
        kCVPixelBufferHeightKey as String: height,
        kCVPixelBufferIOSurfacePropertiesKey as String: [:],
    ]
)
guard writer.canAdd(input) else { fail("cannot add video input") }
writer.add(input)
guard writer.startWriting() else { fail(writer.error?.localizedDescription ?? "writer failed") }
writer.startSession(atSourceTime: .zero)

func drawText(_ text: String, x: CGFloat, y: CGFloat, width: CGFloat,
              size: CGFloat, color: NSColor = .white,
              weight: NSFont.Weight = .regular) {
    let attributes: [NSAttributedString.Key: Any] = [
        .font: NSFont.systemFont(ofSize: size, weight: weight),
        .foregroundColor: color,
    ]
    NSAttributedString(string: text, attributes: attributes)
        .draw(in: CGRect(x: x, y: y, width: width, height: 60))
}

let colorSpace = CGColorSpaceCreateDeviceRGB()
let bitmapInfo = CGBitmapInfo.byteOrder32Little.union(
    CGBitmapInfo(rawValue: CGImageAlphaInfo.premultipliedFirst.rawValue)
)

for (frameIndex, scene) in scenes.enumerated() {
    while !input.isReadyForMoreMediaData { usleep(1_000) }
    guard let pool = adaptor.pixelBufferPool else { fail("pixel-buffer pool unavailable") }
    var optionalBuffer: CVPixelBuffer?
    guard CVPixelBufferPoolCreatePixelBuffer(nil, pool, &optionalBuffer) == kCVReturnSuccess,
          let buffer = optionalBuffer else { fail("pixel-buffer allocation failed") }
    CVPixelBufferLockBaseAddress(buffer, [])
    guard let base = CVPixelBufferGetBaseAddress(buffer),
          let context = CGContext(
            data: base,
            width: width,
            height: height,
            bitsPerComponent: 8,
            bytesPerRow: CVPixelBufferGetBytesPerRow(buffer),
            space: colorSpace,
            bitmapInfo: bitmapInfo.rawValue
          ) else { fail("drawing context failed") }

    context.setFillColor(CGColor(red: 0.018, green: 0.025, blue: 0.040, alpha: 1))
    context.fill(CGRect(x: 0, y: 0, width: width, height: height))
    context.translateBy(x: 0, y: CGFloat(height))
    context.scaleBy(x: 1, y: -1)
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.current = NSGraphicsContext(cgContext: context, flipped: true)

    let pair = scene.chapter == 0 ? [10, 80] : [320, 950]
    drawText("PEDOT FREQUENCY-INFORMED CUT / REPAIR", x: 38, y: 25,
             width: 1_300, size: 30, weight: .bold)
    drawText("Exact 192×128 occupied-cell anatomy · matched cut, voltage, duty and optical probes",
             x: 38, y: 67, width: 1_500, size: 18,
             color: NSColor(calibratedWhite: 0.76, alpha: 1))
    drawText("EPOCH \(scene.epoch) / 36", x: 1_570, y: 32, width: 300, size: 25,
             color: NSColor(calibratedRed: 0.30, green: 0.90, blue: 0.76, alpha: 1),
             weight: .bold)

    for (column, frequency) in pair.enumerated() {
        let image = images[frequency]![scene.epoch]
        let x = CGFloat(30 + column * 945)
        let panel = CGRect(x: x, y: 122, width: 915, height: 845)
        context.setFillColor(CGColor(red: 0.035, green: 0.050, blue: 0.070, alpha: 1))
        context.fill(panel)
        let target = CGRect(x: x + 18, y: 138, width: 879, height: 590)
        NSImage(cgImage: image, size: NSSize(width: image.width, height: image.height))
            .draw(in: target, from: .zero, operation: .copy, fraction: 1,
                  respectFlipped: true, hints: [.interpolation: NSImageInterpolation.none])

        let connection = (frequency == 10 && scene.epoch >= 5)
            || (frequency == 80 && scene.epoch >= 18)
        let status = connection ? "CONNECTED" : "DEVELOPING CONNECTION"
        let statusColor = connection
            ? NSColor(calibratedRed: 0.30, green: 0.92, blue: 0.62, alpha: 1)
            : NSColor(calibratedRed: 1.0, green: 0.67, blue: 0.24, alpha: 1)
        drawText("\(frequency) Hz · \(status)", x: x + 26, y: 750,
                 width: 860, size: 24, color: statusColor, weight: .bold)
        let description: String
        switch frequency {
        case 10: description = "broad dendritic recruitment · reconnects at epoch 5"
        case 80: description = "reference-frequency morphology · reconnects at epoch 18"
        case 320: description = "oriented developing route · 2.39× final flux"
        default: description = "cable-like developing route · 1.31× final flux"
        }
        drawText(description, x: x + 26, y: 790, width: 860, size: 18,
                 color: NSColor(calibratedWhite: 0.79, alpha: 1))
        if scene.chapter == 0 && scene.epoch == 5 && frequency == 10 {
            drawText("FIRST RECONNECTION", x: x + 26, y: 842, width: 860, size: 23,
                     color: statusColor, weight: .bold)
        }
        if scene.chapter == 0 && scene.epoch == 18 && frequency == 80 {
            drawText("FIRST RECONNECTION", x: x + 26, y: 842, width: 860, size: 23,
                     color: statusColor, weight: .bold)
        }
    }

    drawText("Literature-informed screening translation: projected area ∝ waveform period; increasing frequency shifts diffuse dendrites toward oriented cable-like growth.",
             x: 40, y: 1_010, width: 1_830, size: 16,
             color: NSColor(calibratedWhite: 0.68, alpha: 1))
    NSGraphicsContext.restoreGraphicsState()
    CVPixelBufferUnlockBaseAddress(buffer, [])

    let time = CMTime(value: CMTimeValue(frameIndex), timescale: fps)
    guard adaptor.append(buffer, withPresentationTime: time) else {
        fail(writer.error?.localizedDescription ?? "frame append failed")
    }
}

input.markAsFinished()
let semaphore = DispatchSemaphore(value: 0)
writer.finishWriting { semaphore.signal() }
semaphore.wait()
guard writer.status == .completed else {
    fail(writer.error?.localizedDescription ?? "writer did not complete")
}
print(output.path)
