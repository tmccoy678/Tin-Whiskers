#!/usr/bin/env swift

import AppKit
import Foundation

enum SurfaceStatus: String, Codable { case running = "RUNNING"; case complete = "COMPLETE"; case error = "ERROR" }
enum Mode: String, Codable { case fixed = "FIXED-RULE CONTROL"; case adaptive = "ADAPTIVE CONTROLLER" }
enum Stimulus: String, Codable { case active = "ACTIVE"; case inactive = "INACTIVE"; case off = "OFF"; case notApplicable = "N/A" }
enum Decision: String, Codable { case fixed = "FIXED"; case warmup = "WARMUP"; case explore = "EXPLORE"; case exploit = "EXPLOIT"; case initial = "INITIAL" }
struct ROI: Codable { let x: Int; let y: Int; let width: Int; let height: Int; let cell_scale: Int }
struct StatusInput: Codable {
    let schema_version: Int; let status: SurfaceStatus; let mode: Mode; let title: String
    let state: Int?; let state_count: Int?; let upper: Stimulus?; let lower: Stimulus?; let decision: Decision?
    let source_value: String?; let sink_value: String?; let frame: String?; let roi: ROI?; let message: String?
    let display_zero_based: Bool?
}

func fail(_ message: String) -> Never {
    FileHandle.standardError.write(Data("error: \(message)\n".utf8)); exit(1)
}

var inputURL: URL?
var rootURL: URL?
var outputURL: URL?
var index = 1
while index < CommandLine.arguments.count {
    switch CommandLine.arguments[index] {
    case "--input": inputURL = URL(fileURLWithPath: CommandLine.arguments[index + 1]); index += 2
    case "--candidate-root": rootURL = URL(fileURLWithPath: CommandLine.arguments[index + 1], isDirectory: true); index += 2
    case "--output": outputURL = URL(fileURLWithPath: CommandLine.arguments[index + 1]); index += 2
    default: fail("unknown argument")
    }
}
guard let inputURL, let rootURL, let outputURL else {
    fail("usage: intel_atomic_surface.swift --input STATUS.json --candidate-root DIR --output CURRENT.ansi")
}
let input: StatusInput
do { input = try JSONDecoder().decode(StatusInput.self, from: Data(contentsOf: inputURL)) }
catch { fail("cannot decode current status: \(error)") }

let clearAndHome = "\u{001B}[2J\u{001B}[H"
var lines: [String] = []
if input.status == .error {
    guard let message = input.message, !message.isEmpty, message.count <= 80, !message.contains("\n") else {
        fail("ERROR surface needs one concise message")
    }
    lines = [
        "\(input.mode.rawValue) | ERROR",
        input.title,
        message,
        "CURRENT STATUS ONLY · NO HISTORY",
    ]
} else {
    guard let state = input.state,
          let stateCount = input.state_count,
          let upper = input.upper,
          let lower = input.lower,
          let decision = input.decision,
          let sourceValue = input.source_value,
          let sinkValue = input.sink_value,
          let frame = input.frame,
          let roi = input.roi else {
        fail("current status is missing its exact frame/action")
    }
    let frameURL = rootURL.appendingPathComponent(frame)
    guard let data = try? Data(contentsOf: frameURL),
          let bitmap = NSBitmapImageRep(data: data),
          let pixels = bitmap.bitmapData,
          roi.x + roi.width <= bitmap.pixelsWide,
          roi.y + roi.height <= bitmap.pixelsHigh,
          roi.width % roi.cell_scale == 0,
          roi.height % roi.cell_scale == 0 else {
        fail("current frame or ROI is invalid")
    }
    let logicalWidth = roi.width / roi.cell_scale
    let logicalHeight = roi.height / roi.cell_scale
    guard logicalWidth % 2 == 0, logicalHeight % 4 == 0 else {
        fail("literal lattice must fit complete 2x4 braille cells")
    }
    var occupied = Array(repeating: false, count: logicalWidth * logicalHeight)
    for cellY in 0..<logicalHeight {
        for cellX in 0..<logicalWidth {
            var value: Bool?
            for dy in 0..<roi.cell_scale {
                let row = pixels.advanced(by: (roi.y + cellY * roi.cell_scale + dy) * bitmap.bytesPerRow)
                for dx in 0..<roi.cell_scale {
                    let p = row.advanced(by: (roi.x + cellX * roi.cell_scale + dx) * 4)
                    let isBlack = p[0] == 0 && p[1] == 0 && p[2] == 0
                    let isWhite = p[0] == 255 && p[1] == 255 && p[2] == 255
                    guard isBlack || isWhite else { fail("lattice contains a nonliteral color") }
                    let current = isWhite
                    if let value, value != current { fail("lattice cell block is not uniform") }
                    value = current
                }
            }
            occupied[cellY * logicalWidth + cellX] = value ?? false
        }
    }
    let zeroBased = input.display_zero_based ?? false
    lines.append(
        "\(input.mode.rawValue) | \(input.status.rawValue) | STATE "
            + "\(zeroBased ? state : state + 1) OF \(zeroBased ? stateCount - 1 : stateCount)"
    )
    lines.append(input.title)
    lines.append("SOURCE \(sourceValue) → SINK \(sinkValue)")
    lines.append("UPPER \(upper.rawValue) | LOWER \(lower.rawValue) | ACTION \(decision.rawValue)")
    let bitFor: [[Int]] = [[0, 3], [1, 4], [2, 5], [6, 7]]
    for blockY in stride(from: 0, to: logicalHeight, by: 4) {
        var row = ""
        for blockX in stride(from: 0, to: logicalWidth, by: 2) {
            var bits = 0
            for dy in 0..<4 {
                for dx in 0..<2 where occupied[(blockY + dy) * logicalWidth + blockX + dx] {
                    bits |= 1 << bitFor[dy][dx]
                }
            }
            row.unicodeScalars.append(UnicodeScalar(0x2800 + bits)!)
        }
        lines.append(row)
    }
    lines.append("CURRENT FRAME ONLY · OVERWRITE INPUT · NO HISTORY")
}

try? FileManager.default.createDirectory(at: outputURL.deletingLastPathComponent(), withIntermediateDirectories: true)
let surface = clearAndHome + lines.joined(separator: "\n") + "\n"
try Data(surface.utf8).write(to: outputURL, options: .atomic)
print("overwrote=\(outputURL.path)")
print("status=\(input.status.rawValue)")
print("lines=\(lines.count)")
