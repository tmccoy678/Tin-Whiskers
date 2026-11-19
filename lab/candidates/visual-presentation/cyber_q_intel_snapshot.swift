#!/usr/bin/env swift

import Foundation

struct ActionMap: Codable {
    let index: Int
    let kind: String
    let name: String
    let target: [Int]
}

func fail(_ message: String) -> Never {
    FileHandle.standardError.write(Data("error: \(message)\n".utf8)); exit(1)
}

var tsvURL: URL?
var mapURL: URL?
var outputURL: URL?
var phase = "eval-adapt"
var scenario = "reversal-deception"
var policy = "neural-q"
var episode = 0
var index = 1
while index < CommandLine.arguments.count {
    switch CommandLine.arguments[index] {
    case "--tsv": tsvURL = URL(fileURLWithPath: CommandLine.arguments[index + 1]); index += 2
    case "--action-map": mapURL = URL(fileURLWithPath: CommandLine.arguments[index + 1]); index += 2
    case "--output": outputURL = URL(fileURLWithPath: CommandLine.arguments[index + 1]); index += 2
    case "--phase": phase = CommandLine.arguments[index + 1]; index += 2
    case "--scenario": scenario = CommandLine.arguments[index + 1]; index += 2
    case "--policy": policy = CommandLine.arguments[index + 1]; index += 2
    case "--episode": episode = Int(CommandLine.arguments[index + 1]) ?? -1; index += 2
    default: fail("unknown argument")
    }
}
guard let tsvURL, let mapURL, let outputURL, episode >= 0 else {
    fail("usage: cyber_q_intel_snapshot.swift --tsv FILE --action-map FILE --output FILE [filters]")
}

let actions = try JSONDecoder().decode([ActionMap].self, from: Data(contentsOf: mapURL)).sorted { $0.index < $1.index }
guard actions.map(\.index) == Array(0..<18) else { fail("action map must contain exact indices 0 through 17") }
let text = String(data: try Data(contentsOf: tsvURL), encoding: .utf8)!.replacingOccurrences(of: "\r\n", with: "\n")
let lines = text.split(separator: "\n", omittingEmptySubsequences: true).map(String.init)
guard let first = lines.first else { fail("empty Q lattice TSV") }
let header = first.split(separator: "\t", omittingEmptySubsequences: false).map(String.init)
let column = Dictionary(uniqueKeysWithValues: header.enumerated().map { ($0.element, $0.offset) })
for name in ["phase", "scenario", "policy", "episode", "step", "epsilon", "chosen_action", "reward", "success", "reversal_active_before"] {
    guard column[name] != nil else { fail("Q lattice TSV lacks \(name)") }
}
var selected: [String]?
for line in lines.dropFirst() {
    let fields = line.split(separator: "\t", omittingEmptySubsequences: false).map(String.init)
    guard fields.count == header.count else { fail("malformed Q lattice row") }
    if fields[column["phase"]!] == phase,
       fields[column["scenario"]!] == scenario,
       fields[column["policy"]!] == policy,
       Int(fields[column["episode"]!]) == episode {
        if selected == nil || Int(fields[column["step"]!])! > Int(selected![column["step"]!])! { selected = fields }
    }
}
guard let row = selected else { fail("no Q lattice row matches the requested surface") }
let chosen = Int(row[column["chosen_action"]!])!
let qValues = (0..<18).map { Double(row[column[String(format: "q_%02d", $0)]!] )! }
let ranking = qValues.enumerated().sorted { $0.element > $1.element }
let runner = ranking.first { $0.offset != chosen }!
let chosenAction = actions[chosen]
let runnerAction = actions[runner.offset]
let units = policy == "neural-q" ? "reward/50" : "raw reward"
let reversal = row[column["reversal_active_before"]!].isEmpty ? "N/A" : row[column["reversal_active_before"]!].uppercased()
let target = "[\(chosenAction.target.map(String.init).joined(separator: ","))]"
let runnerTarget = "[\(runnerAction.target.map(String.init).joined(separator: ","))]"

var output: [String] = [
    "CLASSICAL Q VALUES · NOT QUANTUM · DELAYED CURRENT SNAPSHOT",
    "PHASE \(phase) | SCENARIO \(scenario) | POLICY \(policy)",
    "EPISODE \(episode) | STEP \(row[column["step"]!]) | REVERSAL BEFORE \(reversal)",
    "UNITS \(units) | REWARD \(row[column["reward"]!]) | SUCCESS \(row[column["success"]!]) | EPSILON \(row[column["epsilon"]!])",
    String(format: "CHOSEN a%02d %@%@  Q=%+.4f", chosen, chosenAction.kind, target, qValues[chosen]),
    String(format: "RUNNER a%02d %@%@  Q=%+.4f  MARGIN=%+.4f", runner.offset, runnerAction.kind, runnerTarget, runner.element, qValues[chosen] - runner.element),
    "",
]
for start in stride(from: 0, to: 18, by: 6) {
    let segment = (start..<min(start + 6, 18)).map { action in
        String(format: "%@a%02d:%+.4f", action == chosen ? "*" : " ", action, qValues[action])
    }.joined(separator: "  ")
    output.append(segment)
}
output.append("* = CHOSEN · ACTION MAP IS INDEX/KIND/TARGET · CURRENT FRAME ONLY · NO HISTORY")
let surface = "\u{001B}[2J\u{001B}[H" + output.joined(separator: "\n") + "\n"
try? FileManager.default.createDirectory(at: outputURL.deletingLastPathComponent(), withIntermediateDirectories: true)
try Data(surface.utf8).write(to: outputURL, options: .atomic)
print("overwrote=\(outputURL.path)")
print("chosen=a\(chosen) \(chosenAction.kind) \(target)")
print("step=\(row[column["step"]!])")
print("units=\(units)")
