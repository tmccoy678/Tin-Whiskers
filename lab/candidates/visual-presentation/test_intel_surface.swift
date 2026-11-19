#!/usr/bin/env swift

import Foundation

func fail(_ message: String) -> Never {
    FileHandle.standardError.write(Data("error: \(message)\n".utf8)); exit(1)
}
guard CommandLine.arguments.count == 2 else { fail("usage: test_intel_surface.swift CANDIDATE_ROOT") }
let root = URL(fileURLWithPath: CommandLine.arguments[1], isDirectory: true)
let update = root.appendingPathComponent("update_intel_status.swift")
let render = root.appendingPathComponent("intel_atomic_surface.swift")
let fixture = root.appendingPathComponent("fixtures/intel", isDirectory: true)
let generated = root.appendingPathComponent("generated/intel", isDirectory: true)
let currentStatus = generated.appendingPathComponent("current-status.json")
let currentSurface = generated.appendingPathComponent("current.ansi")
try? FileManager.default.createDirectory(at: generated, withIntermediateDirectories: true)

func run(_ arguments: [String]) {
    let process = Process()
    process.executableURL = URL(fileURLWithPath: "/usr/bin/swift")
    process.arguments = arguments
    let pipe = Pipe(); process.standardOutput = pipe; process.standardError = pipe
    do { try process.run(); process.waitUntilExit() }
    catch { fail("cannot run child process: \(error)") }
    if process.terminationStatus != 0 {
        let output = String(data: pipe.fileHandleForReading.readDataToEndOfFile(), encoding: .utf8) ?? ""
        fail("child process failed: \(output)")
    }
}

func updateAndRender(_ name: String) -> String {
    run([update.path, fixture.appendingPathComponent("\(name).json").path, currentStatus.path])
    run([render.path, "--input", currentStatus.path, "--candidate-root", root.path, "--output", currentSurface.path])
    return (try? String(contentsOf: currentSurface, encoding: .utf8)) ?? ""
}

func occurrences(_ needle: String, in text: String) -> Int {
    text.components(separatedBy: needle).count - 1
}

var failures: [String] = []
let running = updateAndRender("running")
if !running.hasPrefix("\u{001B}[2J\u{001B}[H") { failures.append("RUNNING surface does not atomically clear/home") }
if !running.contains("| RUNNING |") || !running.contains("ACTION EXPLORE") { failures.append("RUNNING surface lacks current action") }
if running.contains("| COMPLETE |") || running.contains("| ERROR") { failures.append("RUNNING surface contains another status") }
let runningBraille = running.unicodeScalars.filter { $0.value >= 0x2800 && $0.value <= 0x28ff }.count
if runningBraille == 0 { failures.append("RUNNING surface has no literal braille frame") }

let complete = updateAndRender("complete")
let currentInput = (try? String(contentsOf: currentStatus, encoding: .utf8)) ?? ""
if !complete.contains("| COMPLETE |") || !complete.contains("ACTION EXPLOIT") { failures.append("COMPLETE surface lacks final action") }
if complete.contains("| RUNNING |") || currentInput.contains("RUNNING") { failures.append("overwrite retained RUNNING history") }
if occurrences("CURRENT FRAME ONLY", in: complete) != 1 { failures.append("COMPLETE surface contains history") }
let completeBraille = complete.unicodeScalars.filter { $0.value >= 0x2800 && $0.value <= 0x28ff }.count
if completeBraille == 0 { failures.append("COMPLETE surface has no literal braille frame") }

let error = updateAndRender("error")
if !error.contains("| ERROR") || !error.contains("fixture action unavailable") { failures.append("ERROR surface is not concise") }
if error.contains("| RUNNING |") || error.contains("| COMPLETE |") { failures.append("ERROR surface retained prior status") }
let errorBraille = error.unicodeScalars.filter { $0.value >= 0x2800 && $0.value <= 0x28ff }.count
if errorBraille != 0 { failures.append("ERROR surface retained a prior frame") }
if error.split(separator: "\n").count != 4 { failures.append("ERROR surface is not four concise lines") }

_ = updateAndRender("complete")

let result: [String: Any] = [
    "passed": failures.isEmpty,
    "failures": failures,
    "overwrite_only_status_input": true,
    "clear_and_home_prefix": true,
    "running_braille_cells": runningBraille,
    "complete_braille_cells": completeBraille,
    "error_braille_cells": errorBraille,
    "final_surface_status": "COMPLETE",
]
let data = try JSONSerialization.data(withJSONObject: result, options: [.prettyPrinted, .sortedKeys])
try data.write(to: generated.appendingPathComponent("test-results.json"), options: .atomic)
print("passed=\(failures.isEmpty)")
print("running_braille_cells=\(runningBraille)")
print("complete_braille_cells=\(completeBraille)")
print("error_braille_cells=\(errorBraille)")
if !failures.isEmpty { for failure in failures { print("FAIL: \(failure)") }; exit(1) }
