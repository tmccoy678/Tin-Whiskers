#!/usr/bin/env swift

import AppKit
import AVFoundation
import CoreVideo
import Foundation

enum Mode: String, Codable { case fixed = "FIXED-RULE CONTROL"; case adaptive = "ADAPTIVE CONTROLLER" }
enum Stimulus: String, Codable { case active = "ACTIVE"; case inactive = "INACTIVE"; case off = "OFF"; case notApplicable = "N/A" }
enum Decision: String, Codable { case fixed = "FIXED"; case warmup = "WARMUP"; case explore = "EXPLORE"; case exploit = "EXPLOIT"; case initial = "INITIAL" }
enum Palette: String, Codable { case darkLiteral = "DARK_LITERAL"; case lightAnatomy = "LIGHT_ANATOMY" }
struct LatticeROI: Codable { let x: Int; let y: Int; let width: Int; let height: Int; let cell_scale: Int; let display_scale: Int? }
struct PresentationManifest: Codable {
    let schema_version: Int; let title: String; let mode: Mode; let state_count: Int; let fps: Int32
    let source_value: String; let sink_value: String; let source_frames: String; let actions_file: String
    let lattice_roi: LatticeROI
    let frame_prefix: String?; let action_label: String?; let palette: Palette?; let write_movie: Bool?
    let state_index_base: Int?
}
struct Action: Codable { let state: Int; let upper: Stimulus; let lower: Stimulus; let decision: Decision; let connection: String? }
struct ActionsManifest: Codable { let schema_version: Int; let state_count: Int; let actions: [Action] }
struct Region { let x: Int; let y: Int; let width: Int; let height: Int }
struct Layout {
    let width: Int; let height: Int; let anatomyX = 144; let anatomyY = 124
    let anatomyWidth: Int; let anatomyHeight: Int
    init(_ roi: LatticeROI) {
        let scale = roi.display_scale ?? 1
        anatomyWidth = roi.width * scale; anatomyHeight = roi.height * scale
        width = anatomyWidth + 288; height = anatomyHeight + 192
    }
}

func fail(_ message: String) -> Never {
    FileHandle.standardError.write(Data("error: \(message)\n".utf8)); exit(1)
}

var manifestURL: URL?
var outputURL: URL?
var argument = 1
while argument < CommandLine.arguments.count {
    switch CommandLine.arguments[argument] {
    case "--manifest":
        guard argument + 1 < CommandLine.arguments.count else { fail("--manifest needs a path") }
        manifestURL = URL(fileURLWithPath: CommandLine.arguments[argument + 1]); argument += 2
    case "--output":
        guard argument + 1 < CommandLine.arguments.count else { fail("--output needs a path") }
        outputURL = URL(fileURLWithPath: CommandLine.arguments[argument + 1], isDirectory: true); argument += 2
    default: fail("unknown argument")
    }
}
guard let manifestURL, let outputURL else { fail("usage: check_presenter.swift --manifest FILE --output DIR") }

func decode<T: Decodable>(_ type: T.Type, _ url: URL) -> T {
    do { return try JSONDecoder().decode(type, from: Data(contentsOf: url)) }
    catch { fail("cannot decode \(url.path): \(error)") }
}
func bitmap(_ url: URL) -> NSBitmapImageRep {
    guard let data = try? Data(contentsOf: url), let image = NSBitmapImageRep(data: data) else { fail("cannot read \(url.path)") }
    return image
}
func comparePNGs(source: NSBitmapImageRep, rendered: NSBitmapImageRep, manifest: PresentationManifest, layout: Layout) -> (Int, Int) {
    guard let a = source.bitmapData, let b = rendered.bitmapData else { fail("missing bitmap data") }
    let scale = manifest.lattice_roi.display_scale ?? 1
    let palette = manifest.palette ?? .darkLiteral
    var pixels = 0; var bytes = 0
    for y in 0..<manifest.lattice_roi.height {
        let ar = a.advanced(by: (manifest.lattice_roi.y + y) * source.bytesPerRow)
        for x in 0..<manifest.lattice_roi.width {
            let ap = ar.advanced(by: (manifest.lattice_roi.x + x) * 4)
            let expected: [UInt8]
            if palette == .lightAnatomy {
                let black = ap[0] == 0 && ap[1] == 0 && ap[2] == 0
                let white = ap[0] == 255 && ap[1] == 255 && ap[2] == 255
                guard black || white else { fail("light source is not literal black/white") }
                expected = white ? [20, 28, 24] : [247, 244, 236]
            } else {
                expected = [ap[0], ap[1], ap[2]]
            }
            for dy in 0..<scale {
                let br = b.advanced(by: (layout.anatomyY + y * scale + dy) * rendered.bytesPerRow)
                for dx in 0..<scale {
                    let bp = br.advanced(by: (layout.anatomyX + x * scale + dx) * 4)
                    var differs = false
                    for c in 0..<3 where expected[c] != bp[c] { bytes += 1; differs = true }
                    if differs { pixels += 1 }
                }
            }
        }
    }
    return (pixels, bytes)
}
func compareDecoded(source: NSBitmapImageRep, buffer: CVPixelBuffer, manifest: PresentationManifest, layout: Layout) -> (Int, Int) {
    guard let a = source.bitmapData else { fail("missing source bitmap data") }
    let scale = manifest.lattice_roi.display_scale ?? 1
    let palette = manifest.palette ?? .darkLiteral
    CVPixelBufferLockBaseAddress(buffer, .readOnly); defer { CVPixelBufferUnlockBaseAddress(buffer, .readOnly) }
    guard let base = CVPixelBufferGetBaseAddress(buffer) else { fail("missing decoded data") }
    let rowBytes = CVPixelBufferGetBytesPerRow(buffer)
    var pixels = 0; var bytes = 0
    for y in 0..<manifest.lattice_roi.height {
        let ar = a.advanced(by: (manifest.lattice_roi.y + y) * source.bytesPerRow)
        for x in 0..<manifest.lattice_roi.width {
            let ap = ar.advanced(by: (manifest.lattice_roi.x + x) * 4)
            let expected: [UInt8]
            if palette == .lightAnatomy {
                let black = ap[0] == 0 && ap[1] == 0 && ap[2] == 0
                let white = ap[0] == 255 && ap[1] == 255 && ap[2] == 255
                guard black || white else { fail("light source is not literal black/white") }
                expected = white ? [20, 28, 24] : [247, 244, 236]
            } else {
                expected = [ap[0], ap[1], ap[2]]
            }
            for dy in 0..<scale {
                let br = base.advanced(by: (layout.anatomyY + y * scale + dy) * rowBytes).assumingMemoryBound(to: UInt8.self)
                for dx in 0..<scale {
                    let bp = br.advanced(by: (layout.anatomyX + x * scale + dx) * 4)
                    let actual = [bp[2], bp[1], bp[0]]
                    var differs = false
                    for c in 0..<3 where expected[c] != actual[c] { bytes += 1; differs = true }
                    if differs { pixels += 1 }
                }
            }
        }
    }
    return (pixels, bytes)
}
func regionBytes(_ image: NSBitmapImageRep, _ region: Region) -> [UInt8] {
    guard let data = image.bitmapData else { fail("missing bitmap data") }
    var result: [UInt8] = []; result.reserveCapacity(region.width * region.height * 3)
    for y in region.y..<(region.y + region.height) {
        let row = data.advanced(by: y * image.bytesPerRow)
        for x in region.x..<(region.x + region.width) {
            let p = row.advanced(by: x * 4); result += [p[0], p[1], p[2]]
        }
    }
    return result
}
func nonBackground(_ image: NSBitmapImageRep, _ region: Region, palette: Palette) -> Int {
    guard let data = image.bitmapData else { fail("missing bitmap data") }
    let background: [UInt8] = palette == .lightAnatomy ? [247, 244, 236] : [5, 7, 11]
    var result = 0
    for y in region.y..<(region.y + region.height) {
        let row = data.advanced(by: y * image.bytesPerRow)
        for x in region.x..<(region.x + region.width) {
            let p = row.advanced(by: x * 4)
            if p[0] != background[0] || p[1] != background[1] || p[2] != background[2] { result += 1 }
        }
    }
    return result
}

let manifest = decode(PresentationManifest.self, manifestURL)
let base = manifestURL.deletingLastPathComponent()
let actions = decode(ActionsManifest.self, base.appendingPathComponent(manifest.actions_file))
let sourceDirectory = manifest.source_frames.hasPrefix("/")
    ? URL(fileURLWithPath: manifest.source_frames, isDirectory: true)
    : base.appendingPathComponent(manifest.source_frames, isDirectory: true)
let stateDirectory = outputURL.appendingPathComponent("states", isDirectory: true)
let layout = Layout(manifest.lattice_roi)
let palette = manifest.palette ?? .darkLiteral
let framePrefix = manifest.frame_prefix ?? "frame."
var failures: [String] = []

if actions.state_count != manifest.state_count || actions.actions.count != manifest.state_count { failures.append("action/state count mismatch") }
let stateFiles = ((try? FileManager.default.contentsOfDirectory(atPath: stateDirectory.path)) ?? []).filter { $0.hasSuffix(".png") }.sorted()
if stateFiles.count != manifest.state_count { failures.append("rendered state count mismatch") }

let titleRegion = Region(x: 40, y: 10, width: layout.width - 80, height: 70)
let railRegion = Region(x: 140, y: 88, width: layout.width - 280, height: 34)
let leftStatusRegion = Region(x: 0, y: layout.anatomyY, width: 144, height: layout.anatomyHeight)
let bottomRegion = Region(x: 140, y: layout.anatomyY + layout.anatomyHeight + 8, width: layout.width - 280, height: 60)
var fixedTitle: [UInt8]?
var fixedRails: [UInt8]?
var maximumRenderedPixels = 0
var maximumRenderedBytes = 0
var minimumTextPixels = Int.max

for state in 0..<min(manifest.state_count, stateFiles.count) {
    let name = String(format: "%@%04d.png", framePrefix, state)
    let source = bitmap(sourceDirectory.appendingPathComponent(name))
    let rendered = bitmap(stateDirectory.appendingPathComponent(name))
    if rendered.pixelsWide != layout.width || rendered.pixelsHigh != layout.height { failures.append("state \(state) resolution mismatch") }
    let comparison = comparePNGs(source: source, rendered: rendered, manifest: manifest, layout: layout)
    maximumRenderedPixels = max(maximumRenderedPixels, comparison.0); maximumRenderedBytes = max(maximumRenderedBytes, comparison.1)
    if comparison.0 != 0 { failures.append("state \(state) changes anatomy") }
    let title = regionBytes(rendered, titleRegion); let rails = regionBytes(rendered, railRegion)
    if fixedTitle == nil { fixedTitle = title } else if fixedTitle! != title { failures.append("title/mode region changed at state \(state)") }
    if fixedRails == nil { fixedRails = rails } else if fixedRails! != rails { failures.append("source/sink region changed at state \(state)") }
    let count = [titleRegion, railRegion, leftStatusRegion, bottomRegion]
        .map { nonBackground(rendered, $0, palette: palette) }.min() ?? 0
    minimumTextPixels = min(minimumTextPixels, count)
    if count < 30 { failures.append("required text region empty at state \(state)") }
}

let writeMovie = manifest.write_movie ?? true
var codec: FourCharCode = 0
var fps: Float = 0
var duration = 0.0
var expectedFrames = 0
var decodedFrames = 0
var maximumDecodedPixels = 0
var maximumDecodedBytes = 0
if writeMovie {
    let movieURL = outputURL.appendingPathComponent("presentation-lossless-rgb.mov")
    let asset = AVURLAsset(url: movieURL)
    guard let track = asset.tracks(withMediaType: .video).first else { fail("missing movie track") }
    let movieWidth = Int(track.naturalSize.width.rounded())
    let movieHeight = Int(track.naturalSize.height.rounded())
    fps = track.nominalFrameRate
    duration = CMTimeGetSeconds(asset.duration)
    guard let descriptionValue = track.formatDescriptions.first else { fail("missing movie codec") }
    let description = descriptionValue as! CMFormatDescription
    codec = CMFormatDescriptionGetMediaSubType(description)
    expectedFrames = Int(manifest.fps) * 2 + max(0, manifest.state_count - 2)
    let expectedDuration = Double(expectedFrames) / Double(manifest.fps)
    if movieWidth != layout.width || movieHeight != layout.height { failures.append("movie resolution mismatch") }
    if abs(fps - Float(manifest.fps)) > 0.001 { failures.append("movie fps mismatch") }
    if abs(duration - expectedDuration) > 0.001 { failures.append("movie duration mismatch") }
    if codec != kCVPixelFormatType_24RGB { failures.append("movie is not raw 24-bit RGB") }
    let stateMap = Array(repeating: 0, count: Int(manifest.fps))
        + (manifest.state_count > 2 ? Array(1..<(manifest.state_count - 1)) : [])
        + Array(repeating: manifest.state_count - 1, count: Int(manifest.fps))
    do {
        let reader = try AVAssetReader(asset: asset)
        let output = AVAssetReaderTrackOutput(track: track, outputSettings: [kCVPixelBufferPixelFormatTypeKey as String: Int(kCVPixelFormatType_32BGRA)])
        guard reader.canAdd(output) else { fail("cannot add reader output") }
        reader.add(output); guard reader.startReading() else { fail("cannot decode movie") }
        while let sample = output.copyNextSampleBuffer() {
            guard let buffer = CMSampleBufferGetImageBuffer(sample), decodedFrames < stateMap.count else { continue }
            let state = stateMap[decodedFrames]
            let source = bitmap(sourceDirectory.appendingPathComponent(String(format: "%@%04d.png", framePrefix, state)))
            let comparison = compareDecoded(source: source, buffer: buffer, manifest: manifest, layout: layout)
            maximumDecodedPixels = max(maximumDecodedPixels, comparison.0)
            maximumDecodedBytes = max(maximumDecodedBytes, comparison.1)
            if comparison.0 != 0 { failures.append("decoded movie frame \(decodedFrames) changes anatomy") }
            decodedFrames += 1
        }
        if reader.status != .completed { failures.append("movie decoder did not complete") }
    } catch { fail("cannot read movie: \(error)") }
    if decodedFrames != expectedFrames { failures.append("decoded frame count mismatch") }
} else {
    let staleMovie = outputURL.appendingPathComponent("presentation-lossless-rgb.mov")
    if FileManager.default.fileExists(atPath: staleMovie.path) { failures.append("frames-only output contains a stale movie") }
}

let result: [String: Any] = [
    "passed": failures.isEmpty,
    "failures": failures,
    "mode": manifest.mode.rawValue,
    "state_count": manifest.state_count,
    "action_decisions": actions.actions.map { $0.decision.rawValue },
    "source_value": manifest.source_value,
    "sink_value": manifest.sink_value,
    "palette": palette.rawValue,
    "rendered_resolution": [layout.width, layout.height],
    "maximum_rendered_anatomy_pixel_mismatches": maximumRenderedPixels,
    "maximum_rendered_anatomy_channel_byte_mismatches": maximumRenderedBytes,
    "minimum_nonbackground_pixels_in_required_text_regions": minimumTextPixels,
    "movie": [
        "written": writeMovie,
        "codec_subtype": codec,
        "decoded_frames": decodedFrames,
        "expected_frames": expectedFrames,
        "fps": fps,
        "duration_seconds": duration,
        "maximum_decoded_anatomy_pixel_mismatches": maximumDecodedPixels,
        "maximum_decoded_anatomy_channel_byte_mismatches": maximumDecodedBytes,
    ],
]
let data = try JSONSerialization.data(withJSONObject: result, options: [.prettyPrinted, .sortedKeys])
try data.write(to: outputURL.appendingPathComponent("acceptance.json"), options: .atomic)
print("passed=\(failures.isEmpty)")
print("mode=\(manifest.mode.rawValue)")
print("states=\(manifest.state_count)")
print("decoded_frames=\(decodedFrames)")
print("rendered_anatomy_pixel_mismatches=\(maximumRenderedPixels)")
print("decoded_anatomy_pixel_mismatches=\(maximumDecodedPixels)")
if !failures.isEmpty { for failure in failures { print("FAIL: \(failure)") }; exit(1) }
