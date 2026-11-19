#!/usr/bin/env swift

import CryptoKit
import Foundation

func fail(_ message: String) -> Never {
    FileHandle.standardError.write(Data("error: \(message)\n".utf8)); exit(1)
}

var pilotURL: URL?
var outputURL: URL?
var repoURL: URL?
var index = 1
while index < CommandLine.arguments.count {
    switch CommandLine.arguments[index] {
    case "--pilot": pilotURL = URL(fileURLWithPath: CommandLine.arguments[index + 1], isDirectory: true); index += 2
    case "--output": outputURL = URL(fileURLWithPath: CommandLine.arguments[index + 1], isDirectory: true); index += 2
    case "--repo-root": repoURL = URL(fileURLWithPath: CommandLine.arguments[index + 1], isDirectory: true); index += 2
    default: fail("unknown argument")
    }
}
guard let pilotURL, let outputURL, let repoURL else {
    fail("usage: prepare_real_adaptive.swift --pilot PILOT_DIR --output INPUT_DIR --repo-root REPO")
}

let armName = "adaptive-seed-319"
let armURL = pilotURL.appendingPathComponent(armName, isDirectory: true)
let actionsURL = armURL.appendingPathComponent("actions.json")
let auditURL = armURL.appendingPathComponent("audit.jsonl")
let metricsURL = armURL.appendingPathComponent("metrics.tsv")
let summaryURL = pilotURL.appendingPathComponent("pilot-summary.json")
let solverInputURL = repoURL.appendingPathComponent("simulation/voltage-routing/voltage_conduction.i")

func data(_ url: URL) -> Data {
    guard let value = try? Data(contentsOf: url) else { fail("cannot read \(url.path)") }
    return value
}
func hash(_ url: URL) -> String {
    SHA256.hash(data: data(url)).map { String(format: "%02x", $0) }.joined()
}
func jsonObject(_ url: URL) -> Any {
    do { return try JSONSerialization.jsonObject(with: data(url)) }
    catch { fail("invalid JSON at \(url.path): \(error)") }
}
func relativePath(from base: URL, to target: URL) -> String {
    let a = base.standardizedFileURL.pathComponents
    let b = target.standardizedFileURL.pathComponents
    var common = 0
    while common < min(a.count, b.count), a[common] == b[common] { common += 1 }
    return Array(repeating: "..", count: a.count - common).joined(separator: "/")
        + (a.count == common ? "" : "/")
        + b[common...].joined(separator: "/")
}
func writeJSON(_ value: Any, to url: URL) {
    let encoded = try! JSONSerialization.data(withJSONObject: value, options: [.prettyPrinted, .sortedKeys])
    try! encoded.write(to: url, options: .atomic)
}

guard let sourceActions = jsonObject(actionsURL) as? [[String: Any]], sourceActions.count == 120 else {
    fail("adaptive seed 319 does not contain exactly 120 actions")
}
let auditLines = String(data: data(auditURL), encoding: .utf8)!
    .split(separator: "\n", omittingEmptySubsequences: true)
guard auditLines.count == 120 else { fail("audit does not contain exactly 120 records") }
for (epoch, line) in auditLines.enumerated() {
    let record = try! JSONSerialization.jsonObject(with: Data(line.utf8)) as! [String: Any]
    guard record["epoch"] as? Int == epoch,
          record["run_id"] as? String == armName,
          record["fail_reason"] is NSNull,
          let action = record["action"] as? [String: Any],
          action["id"] as? String == sourceActions[epoch]["id"] as? String,
          action["selection_mode"] as? String == sourceActions[epoch]["selection_mode"] as? String,
          action["observation_sha256"] as? String == sourceActions[epoch]["observation_sha256"] as? String else {
        fail("audit/action mismatch at epoch \(epoch)")
    }
}

let metricLines = String(data: data(metricsURL), encoding: .utf8)!
    .replacingOccurrences(of: "\r\n", with: "\n")
    .split(separator: "\n", omittingEmptySubsequences: true)
let metricEpochs = metricLines.dropFirst().compactMap { line in
    Int(line.split(separator: "\t").first?.trimmingCharacters(in: .whitespacesAndNewlines) ?? "")
}
guard metricLines.count == 122,
      metricEpochs == Array(0...120) else {
    fail("metrics do not contain exact states 0 through 120: lines=\(metricLines.count) epochs=\(metricEpochs.count) first=\(metricEpochs.first ?? -1) last=\(metricEpochs.last ?? -1)")
}

guard let summary = jsonObject(summaryURL) as? [String: Any],
      let summaries = summary["summaries"] as? [[String: Any]],
      summaries.contains(where: { $0["arm"] as? String == armName }) else {
    fail("pilot summary does not contain adaptive seed 319")
}

let topologyNames = (0...120).map { String(format: "topology-%04d.png", $0) }
let actualTopologies = ((try? FileManager.default.contentsOfDirectory(atPath: armURL.path)) ?? [])
    .filter { $0.hasPrefix("topology-") && $0.hasSuffix(".png") }.sorted()
guard actualTopologies == topologyNames else { fail("topology set is not exact states 0 through 120") }

let solver = String(data: data(solverInputURL), encoding: .utf8)!
let sourcePattern = #"(?s)\[source\].*?boundary\s*=\s*left.*?value\s*=\s*1(?:\.0)?"#
let sinkPattern = #"(?s)\[sink\].*?boundary\s*=\s*right.*?value\s*=\s*0(?:\.0)?"#
guard solver.range(of: sourcePattern, options: .regularExpression) != nil,
      solver.range(of: sinkPattern, options: .regularExpression) != nil else {
    fail("solver input does not establish exact left 1 V / right 0 V boundaries")
}

var modeCounts: [String: Int] = [:]
var idCounts: [String: Int] = [:]
var presenterActions: [[String: Any]] = [[
    "state": 0,
    "upper": "N/A",
    "lower": "N/A",
    "decision": "INITIAL",
    "source_action_index": NSNull(),
    "action_id": NSNull(),
    "upper_fraction": NSNull(),
    "lower_fraction": NSNull(),
]]

for (sourceIndex, action) in sourceActions.enumerated() {
    guard action["schema"] as? String == "adaptive-action/v1",
          let selection = action["selection_mode"] as? String,
          ["warmup", "explore", "exploit"].contains(selection),
          let id = action["id"] as? String,
          let upper = action["upper_fraction"] as? Double,
          let lower = action["lower_fraction"] as? Double,
          let voltage = action["source_voltage"] as? Double,
          abs(upper + lower - 1.0) < 1e-12,
          abs(voltage - 1.0) < 1e-12 else {
        fail("unsupported or incomplete source action at index \(sourceIndex)")
    }
    modeCounts[selection, default: 0] += 1
    idCounts[id, default: 0] += 1
    let upperStatus: String
    let lowerStatus: String
    if upper == 0 { upperStatus = "OFF" } else if upper > lower { upperStatus = "ACTIVE" } else { upperStatus = "INACTIVE" }
    if lower == 0 { lowerStatus = "OFF" } else if lower > upper { lowerStatus = "ACTIVE" } else { lowerStatus = "INACTIVE" }
    presenterActions.append([
        "state": sourceIndex + 1,
        "upper": upperStatus,
        "lower": lowerStatus,
        "decision": selection.uppercased(),
        "source_action_index": sourceIndex,
        "action_id": id,
        "upper_fraction": upper,
        "lower_fraction": lower,
        "observation_sha256": action["observation_sha256"]!,
    ])
}
guard presenterActions.count == 121 else { fail("presenter action mapping is incomplete") }

try? FileManager.default.createDirectory(at: outputURL, withIntermediateDirectories: true)
let presenterActionsURL = outputURL.appendingPathComponent("actions-presenter.json")
writeJSON([
    "schema_version": 1,
    "state_count": 121,
    "alignment": "state 0 is initial; state n uses source action n-1 that produced topology n",
    "actions": presenterActions,
], to: presenterActionsURL)

let relativeArm = relativePath(from: outputURL, to: armURL)
let common: [String: Any] = [
    "schema_version": 1,
    "title": "ADAPTIVE REMODELING · SEED 319 · 120 ACTIONS",
    "mode": "ADAPTIVE CONTROLLER",
    "state_count": 121,
    "fps": 4,
    "source_value": "1 V",
    "sink_value": "0 V",
    "source_frames": relativeArm,
    "actions_file": "actions-presenter.json",
    "frame_prefix": "topology-",
    "action_label": "APPLIED",
    "state_index_base": 0,
    "lattice_roi": [
        "x": 0,
        "y": 0,
        "width": 192,
        "height": 128,
        "cell_scale": 1,
        "display_scale": 6,
    ],
]
var dark = common
dark["palette"] = "DARK_LITERAL"
dark["write_movie"] = true
writeJSON(dark, to: outputURL.appendingPathComponent("presentation-dark.json"))
var light = common
light["palette"] = "LIGHT_ANATOMY"
light["write_movie"] = false
writeJSON(light, to: outputURL.appendingPathComponent("presentation-light.json"))

var topologyHashes: [String: String] = [:]
for name in topologyNames { topologyHashes[name] = hash(armURL.appendingPathComponent(name)) }
let evidence: [String: Any] = [
    "schema_version": 1,
    "completed_arm": armName,
    "validated_action_count": sourceActions.count,
    "validated_audit_count": auditLines.count,
    "validated_topology_count": topologyNames.count,
    "validated_metric_state_count": metricLines.count - 1,
    "selection_mode_counts": [
        "warmup": modeCounts["warmup", default: 0],
        "explore": modeCounts["explore", default: 0],
        "exploit": modeCounts["exploit", default: 0],
    ],
    "action_id_counts": idCounts,
    "boundaries": ["source": "left 1 V", "sink": "right 0 V"],
    "source_sha256": [
        "actions.json": hash(actionsURL),
        "audit.jsonl": hash(auditURL),
        "metrics.tsv": hash(metricsURL),
        "pilot-summary.json": hash(summaryURL),
        "voltage_conduction.i": hash(solverInputURL),
        "topology_pngs": topologyHashes,
    ],
]
writeJSON(evidence, to: outputURL.appendingPathComponent("source-evidence.json"))

print("validated_arm=\(armName)")
print("states=121")
print("actions=120")
print("warmup=\(modeCounts["warmup", default: 0])")
print("explore=\(modeCounts["explore", default: 0])")
print("exploit=\(modeCounts["exploit", default: 0])")
print("input=\(outputURL.path)")
