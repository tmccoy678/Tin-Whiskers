#!/usr/bin/env swift

import Foundation

func fail(_ message: String) -> Never {
    FileHandle.standardError.write(Data("error: \(message)\n".utf8)); exit(1)
}
guard CommandLine.arguments.count == 2 else { fail("usage: test_manifest_validation.swift CANDIDATE_ROOT") }
let root = URL(fileURLWithPath: CommandLine.arguments[1], isDirectory: true)
let fixtures = root.appendingPathComponent("fixtures", isDirectory: true)
let validation = fixtures.appendingPathComponent("validation", isDirectory: true)
let generated = root.appendingPathComponent("generated/validation", isDirectory: true)
try? FileManager.default.createDirectory(at: validation, withIntermediateDirectories: true)
try? FileManager.default.createDirectory(at: generated, withIntermediateDirectories: true)

func object(_ url: URL) -> [String: Any] {
    (try? JSONSerialization.jsonObject(with: Data(contentsOf: url))) as? [String: Any] ?? [:]
}
func write(_ value: [String: Any], _ name: String) -> URL {
    let url = validation.appendingPathComponent(name)
    let data = try! JSONSerialization.data(withJSONObject: value, options: [.prettyPrinted, .sortedKeys])
    try! data.write(to: url, options: .atomic)
    return url
}
func rejected(_ manifest: URL, _ name: String) -> Bool {
    let process = Process()
    process.executableURL = URL(fileURLWithPath: "/usr/bin/swift")
    process.arguments = [
        root.appendingPathComponent("evidence_presenter.swift").path,
        "--manifest", manifest.path,
        "--output", generated.appendingPathComponent(name).path,
    ]
    let pipe = Pipe(); process.standardOutput = pipe; process.standardError = pipe
    try! process.run(); process.waitUntilExit()
    return process.terminationStatus != 0
}

let adaptivePresentationURL = fixtures.appendingPathComponent("adaptive-presentation.json")
let adaptiveActionsURL = fixtures.appendingPathComponent("adaptive-actions.json")
var countActions = object(adaptiveActionsURL)
countActions["state_count"] = 2
countActions["actions"] = Array((countActions["actions"] as! [[String: Any]]).prefix(2))
_ = write(countActions, "count-actions.json")
var countPresentation = object(adaptivePresentationURL)
countPresentation["source_frames"] = "../source-states"
countPresentation["actions_file"] = "count-actions.json"
let countManifest = write(countPresentation, "count-presentation.json")

var modePresentation = object(fixtures.appendingPathComponent("fixed-presentation.json"))
modePresentation["source_frames"] = "../source-states"
modePresentation["actions_file"] = "../adaptive-actions.json"
let modeManifest = write(modePresentation, "mode-presentation.json")

var roiPresentation = object(adaptivePresentationURL)
roiPresentation["source_frames"] = "../source-states"
roiPresentation["actions_file"] = "../adaptive-actions.json"
var roi = roiPresentation["lattice_roi"] as! [String: Any]
roi["width"] = 575
roiPresentation["lattice_roi"] = roi
let roiManifest = write(roiPresentation, "roi-presentation.json")

let checks = [
    "state_count_mismatch": rejected(countManifest, "count-output"),
    "mode_action_mismatch": rejected(modeManifest, "mode-output"),
    "nonintegral_lattice_roi": rejected(roiManifest, "roi-output"),
]
let passed = checks.values.allSatisfy { $0 }
let result: [String: Any] = ["passed": passed, "rejections": checks]
let data = try JSONSerialization.data(withJSONObject: result, options: [.prettyPrinted, .sortedKeys])
try data.write(to: generated.appendingPathComponent("manifest-rejection-results.json"), options: .atomic)
print("passed=\(passed)")
for key in checks.keys.sorted() { print("\(key)=\(checks[key]!)") }
if !passed { exit(1) }
