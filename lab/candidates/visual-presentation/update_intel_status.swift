#!/usr/bin/env swift

import Foundation

enum SurfaceStatus: String, Codable { case running = "RUNNING"; case complete = "COMPLETE"; case error = "ERROR" }
enum Mode: String, Codable { case fixed = "FIXED-RULE CONTROL"; case adaptive = "ADAPTIVE CONTROLLER" }
enum Stimulus: String, Codable { case active = "ACTIVE"; case inactive = "INACTIVE"; case off = "OFF"; case notApplicable = "N/A" }
enum Decision: String, Codable { case fixed = "FIXED"; case warmup = "WARMUP"; case explore = "EXPLORE"; case exploit = "EXPLOIT"; case initial = "INITIAL" }
struct ROI: Codable { let x: Int; let y: Int; let width: Int; let height: Int; let cell_scale: Int }
struct StatusInput: Codable {
    let schema_version: Int
    let status: SurfaceStatus
    let mode: Mode
    let title: String
    let state: Int?
    let state_count: Int?
    let upper: Stimulus?
    let lower: Stimulus?
    let decision: Decision?
    let source_value: String?
    let sink_value: String?
    let frame: String?
    let roi: ROI?
    let message: String?
    let display_zero_based: Bool?
}

func fail(_ message: String) -> Never {
    FileHandle.standardError.write(Data("error: \(message)\n".utf8)); exit(1)
}
guard CommandLine.arguments.count == 3 else {
    fail("usage: update_intel_status.swift SOURCE.json CURRENT.json")
}
let source = URL(fileURLWithPath: CommandLine.arguments[1])
let target = URL(fileURLWithPath: CommandLine.arguments[2])
let input: StatusInput
do { input = try JSONDecoder().decode(StatusInput.self, from: Data(contentsOf: source)) }
catch { fail("invalid status input: \(error)") }
guard input.schema_version == 1, !input.title.isEmpty, !input.title.contains("\n") else {
    fail("invalid status schema or title")
}
switch input.status {
case .error:
    guard let message = input.message, !message.isEmpty, message.count <= 80, !message.contains("\n") else {
        fail("ERROR requires one concise message")
    }
case .running, .complete:
    guard let state = input.state,
          let stateCount = input.state_count,
          state >= 0,
          state < stateCount,
          input.upper != nil,
          input.lower != nil,
          input.decision != nil,
          input.source_value?.isEmpty == false,
          input.sink_value?.isEmpty == false,
          input.frame?.isEmpty == false,
          let roi = input.roi,
          roi.x >= 0,
          roi.y >= 0,
          roi.width > 0,
          roi.height > 0,
          roi.cell_scale > 0,
          roi.width % roi.cell_scale == 0,
          roi.height % roi.cell_scale == 0 else {
        fail("RUNNING/COMPLETE requires one exact frame and action state")
    }
}
try? FileManager.default.createDirectory(at: target.deletingLastPathComponent(), withIntermediateDirectories: true)
let encoder = JSONEncoder(); encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
let data = try encoder.encode(input)
try data.write(to: target, options: .atomic)
print("overwrote=\(target.path)")
print("status=\(input.status.rawValue)")
