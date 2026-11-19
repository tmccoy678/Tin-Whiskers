#!/usr/bin/env swift

import CryptoKit
import Foundation

func fail(_ message: String) -> Never {
    FileHandle.standardError.write(Data("error: \(message)\n".utf8)); exit(1)
}
var metricsURL: URL?
var framesURL: URL?
var outputURL: URL?
var solverURL: URL?
var index = 1
while index < CommandLine.arguments.count {
    switch CommandLine.arguments[index] {
    case "--metrics": metricsURL = URL(fileURLWithPath: CommandLine.arguments[index + 1]); index += 2
    case "--frames": framesURL = URL(fileURLWithPath: CommandLine.arguments[index + 1], isDirectory: true); index += 2
    case "--output": outputURL = URL(fileURLWithPath: CommandLine.arguments[index + 1], isDirectory: true); index += 2
    case "--solver-input": solverURL = URL(fileURLWithPath: CommandLine.arguments[index + 1]); index += 2
    default: fail("unknown argument")
    }
}
guard let metricsURL, let framesURL, let outputURL, let solverURL else {
    fail("usage: prepare_cut_repair.swift --metrics FILE --frames DIR --output DIR --solver-input FILE")
}
func data(_ url: URL) -> Data { guard let value = try? Data(contentsOf: url) else { fail("cannot read \(url.path)") }; return value }
func hash(_ url: URL) -> String { SHA256.hash(data: data(url)).map { String(format: "%02x", $0) }.joined() }
func writeJSON(_ value: Any, _ url: URL) {
    let encoded = try! JSONSerialization.data(withJSONObject: value, options: [.prettyPrinted, .sortedKeys])
    try! encoded.write(to: url, options: .atomic)
}

let lines = String(data: data(metricsURL), encoding: .utf8)!
    .replacingOccurrences(of: "\r\n", with: "\n")
    .split(separator: "\n", omittingEmptySubsequences: true)
guard lines.count == 38 else { fail("cut-repair metrics must contain header plus states 0 through 36") }
let header = lines[0].split(separator: "\t").map(String.init)
let required = ["epoch", "connected", "upper_probe", "lower_probe"]
guard required.allSatisfy(header.contains) else { fail("cut-repair metrics lack required columns") }
let column = Dictionary(uniqueKeysWithValues: header.enumerated().map { ($0.element, $0.offset) })

var actions: [[String: Any]] = []
var connectedStates: [Int] = []
for state in 0...36 {
    let fields = lines[state + 1].split(separator: "\t").map(String.init)
    guard Int(fields[column["epoch"]!]) == state,
          let connected = Int(fields[column["connected"]!]),
          let upper = Double(fields[column["upper_probe"]!]),
          let lower = Double(fields[column["lower_probe"]!]),
          abs(upper + lower - 1.0) < 1e-9 else {
        fail("invalid cut-repair row at state \(state)")
    }
    if connected == 1 { connectedStates.append(state) }
    let upperStatus = upper == 0 ? "OFF" : (upper > lower ? "ACTIVE" : "INACTIVE")
    let lowerStatus = lower == 0 ? "OFF" : (lower > upper ? "ACTIVE" : "INACTIVE")
    actions.append([
        "state": state,
        "upper": upperStatus,
        "lower": lowerStatus,
        "decision": "FIXED",
        "connection": connected == 1 ? "CONNECTED" : "DISCONNECTED",
        "upper_fraction": upper,
        "lower_fraction": lower,
    ])
}
guard connectedStates == Array(18...36) else {
    fail("connection history is not disconnected 0-17 and connected 18-36")
}

let frameNames = (0...36).map { String(format: "frame.%04d.png", $0) }
let actualFrames = ((try? FileManager.default.contentsOfDirectory(atPath: framesURL.path)) ?? [])
    .filter { $0.hasSuffix(".png") }.sorted()
guard actualFrames == frameNames else { fail("cut-repair frame set is not exact states 0 through 36") }

try? FileManager.default.createDirectory(at: outputURL, withIntermediateDirectories: true)
writeJSON(["schema_version": 1, "state_count": 37, "actions": actions], outputURL.appendingPathComponent("actions-presenter.json"))
writeJSON([
    "schema_version": 1,
    "title": "CUT AND REPAIR · TWO-FIBER PROBE",
    "mode": "FIXED-RULE CONTROL",
    "state_count": 37,
    "fps": 4,
    "source_value": "1 V",
    "sink_value": "0 V",
    "source_frames": framesURL.standardizedFileURL.path,
    "actions_file": "actions-presenter.json",
    "frame_prefix": "frame.",
    "action_label": "PROBE",
    "state_index_base": 0,
    "palette": "DARK_LITERAL",
    "write_movie": true,
    "lattice_roi": [
        "x": 64,
        "y": 54,
        "width": 1152,
        "height": 768,
        "cell_scale": 6,
        "display_scale": 1,
    ],
], outputURL.appendingPathComponent("presentation.json"))

var frameHashes: [String: String] = [:]
for name in frameNames { frameHashes[name] = hash(framesURL.appendingPathComponent(name)) }
writeJSON([
    "schema_version": 1,
    "evidence": "CUT AND REPAIR fixed-control candidate; separate from current-driven widening",
    "connection_history": [
        "disconnected_states": Array(0...17),
        "first_connected_state": 18,
        "connected_through_state": 36,
    ],
    "source_sha256": [
        "metrics.tsv": hash(metricsURL),
        "voltage_conduction.i": hash(solverURL),
        "frames": frameHashes,
    ],
], outputURL.appendingPathComponent("source-evidence.json"))

print("states=37")
print("first_connected_state=18")
print("connected_through_state=36")
print("input=\(outputURL.path)")
