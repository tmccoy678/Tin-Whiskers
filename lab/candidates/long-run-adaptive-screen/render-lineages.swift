#!/usr/bin/env swift

import AppKit
import AVFoundation
import CoreVideo
import Foundation

struct Frame: Decodable {
    let environment_index: Int
    let regime: String
    let contingency_kind: String
    let state_index: Int
    let action: String?
    let selection_mode: String?
    let contingency_active: Bool
    let conductance: [Double]
    let delivery: Double
    let service: Double
    let current_concentration_proxy: Double
    let heat_proxy: Double
    let material_used: Double
}

func fail(_ message: String) -> Never {
    FileHandle.standardError.write(Data("error: \(message)\n".utf8))
    exit(1)
}

guard CommandLine.arguments.count == 3 else {
    fail("usage: render-lineages.swift visual-states.jsonl output.mp4")
}

let inputURL = URL(fileURLWithPath: CommandLine.arguments[1])
let outputURL = URL(fileURLWithPath: CommandLine.arguments[2])
guard !FileManager.default.fileExists(atPath: outputURL.path) else {
    fail("output exists: \(outputURL.path)")
}

let decoder = JSONDecoder()
let lines = try String(contentsOf: inputURL, encoding: .utf8)
    .split(separator: "\n", omittingEmptySubsequences: true)
let frames = try lines.map { try decoder.decode(Frame.self, from: Data($0.utf8)) }
let groups = Dictionary(grouping: frames, by: \.environment_index)

let regimes = ["earth_pedot_exploratory", "space_cbram_screening"]
let contingencies = [
    "swap_channel_consequences",
    "degrade_upper_consequence",
    "upper_heat_coupling",
    "shift_reservoir_lower",
]

var selected: [[Frame]] = []
for regime in regimes {
    for contingency in contingencies {
        guard let match = groups.values
            .filter({ $0.first?.regime == regime && $0.first?.contingency_kind == contingency })
            .sorted(by: { $0[0].environment_index < $1[0].environment_index })
            .first else {
            fail("missing lineage for \(regime) / \(contingency)")
        }
        let ordered = match.sorted { $0.state_index < $1.state_index }
        guard ordered.count == 121,
              ordered.first?.state_index == 0,
              ordered.last?.state_index == 120,
              ordered.allSatisfy({ $0.conductance.count == 128 }) else {
            fail("invalid lineage state sequence")
        }
        selected.append(ordered)
    }
}

let width = 1_920
let height = 1_080
let fps: Int32 = 12
let developmentFrames = 121
let holdFrames = 24
let panelWidth = 460
let panelHeight = 430
let startX = 28
let startY = 138
let cell = 20
let gridWidth = 16 * cell
let gridHeight = 8 * cell
let conductanceMinimum = selected.flatMap { $0 }.flatMap(\.conductance).min()!
let conductanceMaximum = selected.flatMap { $0 }.flatMap(\.conductance).max()!

func color(_ red: CGFloat, _ green: CGFloat, _ blue: CGFloat, _ alpha: CGFloat = 1) -> CGColor {
    CGColor(red: red, green: green, blue: blue, alpha: alpha)
}

func conductorColor(_ value: Double) -> CGColor {
    let span = max(conductanceMaximum - conductanceMinimum, 1.0e-12)
    let t = min(max((value - conductanceMinimum) / span, 0), 1)
    let hue = CGFloat(0.60 - 0.48 * t)
    return NSColor(calibratedHue: hue,
                   saturation: CGFloat(0.72 + 0.22 * t),
                   brightness: CGFloat(0.14 + 0.86 * sqrt(t)),
                   alpha: 1).cgColor
}

func label(_ contingency: String) -> String {
    switch contingency {
    case "swap_channel_consequences": return "CONSEQUENCE SWAP"
    case "degrade_upper_consequence": return "UPPER DEGRADATION"
    case "upper_heat_coupling": return "UPPER HEAT COUPLING"
    case "shift_reservoir_lower": return "RESERVOIR SHIFT"
    default: return contingency.uppercased()
    }
}

func drawText(_ text: String, x: CGFloat, y: CGFloat, width: CGFloat,
              size: CGFloat, color: NSColor = .white,
              weight: NSFont.Weight = .regular) {
    let style = NSMutableParagraphStyle()
    style.lineBreakMode = .byTruncatingTail
    let attributes: [NSAttributedString.Key: Any] = [
        .font: NSFont.systemFont(ofSize: size, weight: weight),
        .foregroundColor: color,
        .paragraphStyle: style,
    ]
    NSAttributedString(string: text, attributes: attributes)
        .draw(in: CGRect(x: x, y: y, width: width, height: 60))
}

let writer = try AVAssetWriter(outputURL: outputURL, fileType: .mp4)
let settings: [String: Any] = [
    AVVideoCodecKey: AVVideoCodecType.h264,
    AVVideoWidthKey: width,
    AVVideoHeightKey: height,
    AVVideoCompressionPropertiesKey: [
        AVVideoAverageBitRateKey: 12_000_000,
        AVVideoProfileLevelKey: AVVideoProfileLevelH264HighAutoLevel,
        AVVideoMaxKeyFrameIntervalKey: Int(fps),
    ],
]
let input = AVAssetWriterInput(mediaType: .video, outputSettings: settings)
input.expectsMediaDataInRealTime = false
let attributes: [String: Any] = [
    kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA,
    kCVPixelBufferWidthKey as String: width,
    kCVPixelBufferHeightKey as String: height,
    kCVPixelBufferIOSurfacePropertiesKey as String: [:],
]
let adaptor = AVAssetWriterInputPixelBufferAdaptor(
    assetWriterInput: input,
    sourcePixelBufferAttributes: attributes
)
guard writer.canAdd(input) else { fail("cannot add writer input") }
writer.add(input)
guard writer.startWriting() else { fail(writer.error?.localizedDescription ?? "writer failed") }
writer.startSession(atSourceTime: .zero)

let colorSpace = CGColorSpaceCreateDeviceRGB()
let bitmapInfo = CGBitmapInfo.byteOrder32Little.union(
    CGBitmapInfo(rawValue: CGImageAlphaInfo.premultipliedFirst.rawValue)
)

for movieFrame in 0..<(developmentFrames + holdFrames) {
    let state = min(movieFrame, developmentFrames - 1)
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

    context.setFillColor(color(0.018, 0.026, 0.044))
    context.fill(CGRect(x: 0, y: 0, width: width, height: height))
    context.translateBy(x: 0, y: CGFloat(height))
    context.scaleBy(x: 1, y: -1)

    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.current = NSGraphicsContext(cgContext: context, flipped: true)

    drawText("SEED 571 · EIGHT EXACT ADAPTIVE LINEAGES", x: 30, y: 24,
             width: 1_400, size: 30, weight: .bold)
    drawText("16×8 conductance maps · one retained state per choice · nearest-neighbor cells",
             x: 30, y: 66, width: 1_500, size: 18,
             color: NSColor(calibratedWhite: 0.76, alpha: 1))
    drawText("CHOICE \(state) / 120", x: 1_570, y: 30, width: 320,
             size: 25, color: NSColor(calibratedRed: 0.30, green: 0.90, blue: 0.78, alpha: 1),
             weight: .bold)

    for panel in 0..<8 {
        let row = panel / 4
        let column = panel % 4
        let frame = selected[panel][state]
        let px = startX + column * panelWidth
        let py = startY + row * panelHeight
        let isEarth = row == 0

        context.setFillColor(isEarth ? color(0.035, 0.085, 0.065) : color(0.035, 0.055, 0.105))
        context.fill(CGRect(x: px, y: py, width: panelWidth - 12, height: panelHeight - 14))
        context.setStrokeColor(frame.contingency_active ? color(1.0, 0.63, 0.18) : color(0.22, 0.34, 0.44))
        context.setLineWidth(frame.contingency_active ? 4 : 2)
        context.stroke(CGRect(x: px + 1, y: py + 1, width: panelWidth - 14, height: panelHeight - 16))

        let material = isEarth
            ? "PEDOT:PSS · Au · aqueous EDOT/BQ/NaPSS"
            : "Ag filament · Ag:Ge₃₀Se₇₀ · Ni/Pt"
        drawText(isEarth ? "EARTH EXPLORATORY" : "SPACE SCREENING",
                 x: CGFloat(px + 16), y: CGFloat(py + 14), width: 410, size: 14,
                 color: isEarth
                    ? NSColor(calibratedRed: 0.42, green: 0.92, blue: 0.62, alpha: 1)
                    : NSColor(calibratedRed: 0.48, green: 0.70, blue: 1.0, alpha: 1),
                 weight: .bold)
        drawText(label(frame.contingency_kind), x: CGFloat(px + 16), y: CGFloat(py + 38),
                 width: 410, size: 18, weight: .bold)
        drawText(material, x: CGFloat(px + 16), y: CGFloat(py + 65), width: 420, size: 13,
                 color: NSColor(calibratedWhite: 0.72, alpha: 1))

        let gx = px + 64
        let gy = py + 106
        context.setFillColor(color(0.01, 0.014, 0.025))
        context.fill(CGRect(x: gx - 6, y: gy - 6, width: gridWidth + 12, height: gridHeight + 12))
        context.setFillColor(color(0.20, 0.88, 0.76))
        context.fill(CGRect(x: gx - 12, y: gy, width: 6, height: gridHeight))
        context.setFillColor(color(0.95, 0.40, 0.30))
        context.fill(CGRect(x: gx + gridWidth + 6, y: gy, width: 6, height: gridHeight))
        for y in 0..<8 {
            for x in 0..<16 {
                let value = frame.conductance[y * 16 + x]
                context.setFillColor(conductorColor(value))
                context.fill(CGRect(x: gx + x * cell, y: gy + y * cell,
                                    width: cell - 1, height: cell - 1))
            }
        }

        let action = (frame.action ?? "initial").replacingOccurrences(of: "_", with: " ").uppercased()
        let mode = (frame.selection_mode ?? "initial").replacingOccurrences(of: "_", with: " ").uppercased()
        drawText("ENV \(frame.environment_index) · \(action) · \(mode)",
                 x: CGFloat(px + 16), y: CGFloat(py + 286), width: 420, size: 13,
                 color: NSColor(calibratedWhite: 0.78, alpha: 1), weight: .semibold)
        drawText(String(format: "delivery %.5f   service %.5f", frame.delivery, frame.service),
                 x: CGFloat(px + 16), y: CGFloat(py + 314), width: 420, size: 14)
        drawText(String(format: "current %.3f   heat %.3f   material %.3f",
                        frame.current_concentration_proxy, frame.heat_proxy, frame.material_used),
                 x: CGFloat(px + 16), y: CGFloat(py + 340), width: 425, size: 14)
        if frame.contingency_active {
            drawText("CONCEALED CHANGE ACTIVE", x: CGFloat(px + 16), y: CGFloat(py + 374),
                     width: 420, size: 14,
                     color: NSColor(calibratedRed: 1.0, green: 0.66, blue: 0.22, alpha: 1),
                     weight: .bold)
        }
    }

    NSGraphicsContext.restoreGraphicsState()
    CVPixelBufferUnlockBaseAddress(buffer, [])
    guard adaptor.append(buffer, withPresentationTime: CMTime(value: CMTimeValue(movieFrame), timescale: fps)) else {
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
print(outputURL.path)
