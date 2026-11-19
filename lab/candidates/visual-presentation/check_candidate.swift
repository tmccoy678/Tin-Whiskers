#!/usr/bin/env swift

import AppKit
import AVFoundation
import CoreImage
import CoreVideo
import Foundation

struct Layout {
    static let sourceWidth = 1280
    static let sourceHeight = 860
    static let sourceX = 64
    static let sourceY = 54
    static let anatomyWidth = 1152
    static let anatomyHeight = 768

    static let width = 1440
    static let height = 960
    static let anatomyX = 144
    static let anatomyY = 124
    static let fps: Float = 4
    static let sourceStates = 37
    static let movieFrames = 43
    static let movieDuration = 10.75
}

struct Arguments {
    let source: URL
    let output: URL
}

struct Region {
    let x: Int
    let y: Int
    let width: Int
    let height: Int
}

func fail(_ message: String) -> Never {
    FileHandle.standardError.write(Data("error: \(message)\n".utf8))
    exit(1)
}

func parseArguments() -> Arguments {
    var source: URL?
    var output: URL?
    var index = 1
    let args = CommandLine.arguments
    while index < args.count {
        switch args[index] {
        case "--source":
            guard index + 1 < args.count else { fail("--source needs a path") }
            source = URL(fileURLWithPath: args[index + 1], isDirectory: true)
            index += 2
        case "--output":
            guard index + 1 < args.count else { fail("--output needs a path") }
            output = URL(fileURLWithPath: args[index + 1], isDirectory: true)
            index += 2
        default:
            fail("unknown argument \(args[index])")
        }
    }
    guard let source, let output else {
        fail("usage: check_candidate.swift --source FRAME_DIR --output OUTPUT_DIR")
    }
    return Arguments(source: source, output: output)
}

func loadBitmap(_ url: URL) -> NSBitmapImageRep {
    guard let data = try? Data(contentsOf: url),
          let bitmap = NSBitmapImageRep(data: data) else {
        fail("cannot read \(url.path)")
    }
    return bitmap
}

func regionBytes(_ bitmap: NSBitmapImageRep, region: Region) -> [UInt8] {
    guard bitmap.bitsPerPixel == 32, let data = bitmap.bitmapData else {
        fail("unexpected bitmap layout")
    }
    var output: [UInt8] = []
    output.reserveCapacity(region.width * region.height * 3)
    for y in region.y..<(region.y + region.height) {
        let row = data.advanced(by: y * bitmap.bytesPerRow)
        for x in region.x..<(region.x + region.width) {
            let pixel = row.advanced(by: x * 4)
            output.append(pixel[0])
            output.append(pixel[1])
            output.append(pixel[2])
        }
    }
    return output
}

func nonBackgroundPixelCount(_ bitmap: NSBitmapImageRep, region: Region) -> Int {
    guard let data = bitmap.bitmapData else { fail("bitmap has no data") }
    var count = 0
    for y in region.y..<(region.y + region.height) {
        let row = data.advanced(by: y * bitmap.bytesPerRow)
        for x in region.x..<(region.x + region.width) {
            let pixel = row.advanced(by: x * 4)
            if pixel[0] != 5 || pixel[1] != 7 || pixel[2] != 11 {
                count += 1
            }
        }
    }
    return count
}

func compareRenderedAnatomy(source: NSBitmapImageRep, candidate: NSBitmapImageRep) -> (pixels: Int, bytes: Int) {
    guard let sourceData = source.bitmapData,
          let candidateData = candidate.bitmapData else {
        fail("bitmap has no data")
    }
    var pixelMismatches = 0
    var byteMismatches = 0
    for y in 0..<Layout.anatomyHeight {
        let sourceRow = sourceData.advanced(by: (Layout.sourceY + y) * source.bytesPerRow)
        let candidateRow = candidateData.advanced(by: (Layout.anatomyY + y) * candidate.bytesPerRow)
        for x in 0..<Layout.anatomyWidth {
            let input = sourceRow.advanced(by: (Layout.sourceX + x) * 4)
            let output = candidateRow.advanced(by: (Layout.anatomyX + x) * 4)
            var differs = false
            for channel in 0..<3 where input[channel] != output[channel] {
                byteMismatches += 1
                differs = true
            }
            if differs { pixelMismatches += 1 }
        }
    }
    return (pixelMismatches, byteMismatches)
}

func compareDecodedAnatomy(source: NSBitmapImageRep, pixelBuffer: CVPixelBuffer) -> (pixels: Int, bytes: Int) {
    guard let sourceData = source.bitmapData else { fail("source bitmap has no data") }
    CVPixelBufferLockBaseAddress(pixelBuffer, .readOnly)
    defer { CVPixelBufferUnlockBaseAddress(pixelBuffer, .readOnly) }
    guard let base = CVPixelBufferGetBaseAddress(pixelBuffer) else {
        fail("decoded frame has no data")
    }
    let bytesPerRow = CVPixelBufferGetBytesPerRow(pixelBuffer)
    var pixelMismatches = 0
    var byteMismatches = 0
    for y in 0..<Layout.anatomyHeight {
        let sourceRow = sourceData.advanced(by: (Layout.sourceY + y) * source.bytesPerRow)
        let decodedRow = base.advanced(by: (Layout.anatomyY + y) * bytesPerRow).assumingMemoryBound(to: UInt8.self)
        for x in 0..<Layout.anatomyWidth {
            let input = sourceRow.advanced(by: (Layout.sourceX + x) * 4)
            let output = decodedRow.advanced(by: (Layout.anatomyX + x) * 4)
            let expected = [input[0], input[1], input[2]]
            let actual = [output[2], output[1], output[0]]
            var differs = false
            for channel in 0..<3 where expected[channel] != actual[channel] {
                byteMismatches += 1
                differs = true
            }
            if differs { pixelMismatches += 1 }
        }
    }
    return (pixelMismatches, byteMismatches)
}

func saveDecodedFrame(_ pixelBuffer: CVPixelBuffer, to url: URL) {
    let image = CIImage(cvPixelBuffer: pixelBuffer)
    let context = CIContext(options: [.cacheIntermediates: false])
    guard let cgImage = context.createCGImage(image, from: image.extent),
          let data = NSBitmapImageRep(cgImage: cgImage).representation(using: .png, properties: [:]) else {
        fail("cannot render decoded representative frame")
    }
    do {
        try data.write(to: url, options: .atomic)
    } catch {
        fail("cannot save decoded representative frame: \(error)")
    }
}

let arguments = parseArguments()
let fileManager = FileManager.default
let stateDirectory = arguments.output.appendingPathComponent("states", isDirectory: true)
let decodedDirectory = arguments.output.appendingPathComponent("decoded", isDirectory: true)
try? fileManager.createDirectory(at: decodedDirectory, withIntermediateDirectories: true)

let stateFiles = (try? fileManager.contentsOfDirectory(
    at: stateDirectory,
    includingPropertiesForKeys: nil
))?.filter { $0.pathExtension == "png" }.sorted { $0.lastPathComponent < $1.lastPathComponent } ?? []

var failures: [String] = []
if stateFiles.count != Layout.sourceStates {
    failures.append("rendered state count is \(stateFiles.count), expected \(Layout.sourceStates)")
}

let titleRegion = Region(x: 120, y: 12, width: 1200, height: 68)
let railRegion = Region(x: 144, y: 88, width: 1152, height: 32)
let stimulusRegion = Region(x: 0, y: 420, width: 144, height: 206)
let legendRegion = Region(x: 140, y: 902, width: 700, height: 42)
let stateRegion = Region(x: 1030, y: 902, width: 276, height: 42)

var fixedTitle: [UInt8]?
var fixedRails: [UInt8]?
var fixedLegend: [UInt8]?
var maximumRenderedPixelMismatches = 0
var maximumRenderedByteMismatches = 0
var minimumTextPixelCount = Int.max

for state in 0..<min(stateFiles.count, Layout.sourceStates) {
    let source = loadBitmap(arguments.source.appendingPathComponent(String(format: "frame.%04d.png", state)))
    let candidate = loadBitmap(stateDirectory.appendingPathComponent(String(format: "frame.%04d.png", state)))
    if candidate.pixelsWide != Layout.width || candidate.pixelsHigh != Layout.height {
        failures.append("state \(state) resolution is \(candidate.pixelsWide)x\(candidate.pixelsHigh)")
    }
    let anatomy = compareRenderedAnatomy(source: source, candidate: candidate)
    maximumRenderedPixelMismatches = max(maximumRenderedPixelMismatches, anatomy.pixels)
    maximumRenderedByteMismatches = max(maximumRenderedByteMismatches, anatomy.bytes)
    if anatomy.pixels != 0 {
        failures.append("state \(state) changes \(anatomy.pixels) anatomy pixels")
    }

    let title = regionBytes(candidate, region: titleRegion)
    let rails = regionBytes(candidate, region: railRegion)
    let legend = regionBytes(candidate, region: legendRegion)
    if fixedTitle == nil { fixedTitle = title } else if fixedTitle! != title {
        failures.append("state \(state) has a changing or missing title/control region")
    }
    if fixedRails == nil { fixedRails = rails } else if fixedRails! != rails {
        failures.append("state \(state) has a changing or missing source/sink label region")
    }
    if fixedLegend == nil { fixedLegend = legend } else if fixedLegend! != legend {
        failures.append("state \(state) has a changing or missing legend region")
    }
    let textPixels = [titleRegion, railRegion, stimulusRegion, legendRegion, stateRegion]
        .map { nonBackgroundPixelCount(candidate, region: $0) }
        .min() ?? 0
    minimumTextPixelCount = min(minimumTextPixelCount, textPixels)
    if textPixels < 40 {
        failures.append("state \(state) has an empty foreground text region")
    }
}

let movieURL = arguments.output.appendingPathComponent("current-fiber-remodel-presentation-lossless-rgb.mov")
let asset = AVURLAsset(url: movieURL)
guard let track = asset.tracks(withMediaType: .video).first else {
    fail("movie has no video track")
}
let movieWidth = Int(track.naturalSize.width.rounded())
let movieHeight = Int(track.naturalSize.height.rounded())
let nominalFPS = track.nominalFrameRate
let duration = CMTimeGetSeconds(asset.duration)
guard let firstFormatValue = track.formatDescriptions.first else {
    fail("movie track has no format description")
}
let firstFormat = firstFormatValue as! CMFormatDescription
let codecSubtype = CMFormatDescriptionGetMediaSubType(firstFormat)
if codecSubtype != kCVPixelFormatType_24RGB {
    failures.append("movie codec subtype is \(codecSubtype), expected uncompressed 24-bit RGB")
}
if movieWidth != Layout.width || movieHeight != Layout.height {
    failures.append("movie resolution is \(movieWidth)x\(movieHeight)")
}
if abs(nominalFPS - Layout.fps) > 0.001 {
    failures.append("movie frame rate is \(nominalFPS), expected \(Layout.fps)")
}
if abs(duration - Layout.movieDuration) > 0.001 {
    failures.append("movie duration is \(duration), expected \(Layout.movieDuration)")
}

let stateForMovieFrame = Array(repeating: 0, count: 4)
    + Array(1...35)
    + Array(repeating: 36, count: 4)
let representativeMovieFrames = [12: 9, 21: 18, 30: 27]
var representativeResults: [String: [String: Int]] = [:]
var decodedFrameCount = 0

do {
    let reader = try AVAssetReader(asset: asset)
    let output = AVAssetReaderTrackOutput(
        track: track,
        outputSettings: [
            kCVPixelBufferPixelFormatTypeKey as String: Int(kCVPixelFormatType_32BGRA),
        ]
    )
    guard reader.canAdd(output) else { fail("cannot add decoded movie output") }
    reader.add(output)
    guard reader.startReading() else { fail("cannot start movie decode") }
    while let sample = output.copyNextSampleBuffer() {
        guard let pixelBuffer = CMSampleBufferGetImageBuffer(sample) else { continue }
        let frameIndex = decodedFrameCount
        if let state = representativeMovieFrames[frameIndex] {
            let source = loadBitmap(arguments.source.appendingPathComponent(String(format: "frame.%04d.png", state)))
            let comparison = compareDecodedAnatomy(source: source, pixelBuffer: pixelBuffer)
            representativeResults[String(state)] = [
                "movie_frame": frameIndex,
                "pixel_mismatches": comparison.pixels,
                "channel_byte_mismatches": comparison.bytes,
            ]
            if comparison.pixels != 0 {
                failures.append("decoded state \(state) changes \(comparison.pixels) anatomy pixels")
            }
            saveDecodedFrame(
                pixelBuffer,
                to: decodedDirectory.appendingPathComponent(String(format: "state.%04d.png", state))
            )
        }
        if frameIndex < stateForMovieFrame.count {
            let expectedState = stateForMovieFrame[frameIndex]
            if frameIndex < 4 || frameIndex >= 39 {
                let source = loadBitmap(arguments.source.appendingPathComponent(String(format: "frame.%04d.png", expectedState)))
                let endpoint = compareDecodedAnatomy(source: source, pixelBuffer: pixelBuffer)
                if endpoint.pixels != 0 {
                    failures.append("endpoint hold frame \(frameIndex) changes anatomy")
                }
            }
        }
        decodedFrameCount += 1
    }
    if reader.status != .completed {
        failures.append("movie decoder ended with status \(reader.status.rawValue)")
    }
} catch {
    fail("cannot decode movie: \(error)")
}

if decodedFrameCount != Layout.movieFrames {
    failures.append("decoded frame count is \(decodedFrameCount), expected \(Layout.movieFrames)")
}
for state in [9, 18, 27] where representativeResults[String(state)] == nil {
    failures.append("decoded representative state \(state) was not found")
}

let result: [String: Any] = [
    "passed": failures.isEmpty,
    "failures": failures,
    "rendered_states": stateFiles.count,
    "rendered_resolution": [Layout.width, Layout.height],
    "maximum_rendered_anatomy_pixel_mismatches": maximumRenderedPixelMismatches,
    "maximum_rendered_anatomy_channel_byte_mismatches": maximumRenderedByteMismatches,
    "minimum_nonbackground_pixels_in_required_text_regions": minimumTextPixelCount,
    "movie": [
        "codec": "uncompressed 24-bit RGB lossless all-intra",
        "codec_subtype": codecSubtype,
        "resolution": [movieWidth, movieHeight],
        "fps": nominalFPS,
        "duration_seconds": duration,
        "decoded_frames": decodedFrameCount,
        "endpoint_hold_frames_each": 4,
    ],
    "decoded_representative_anatomy": representativeResults,
]
let json = try JSONSerialization.data(withJSONObject: result, options: [.prettyPrinted, .sortedKeys])
let resultURL = arguments.output.appendingPathComponent("check-results.json")
try json.write(to: resultURL, options: .atomic)

print("passed=\(failures.isEmpty)")
print("rendered_states=\(stateFiles.count)")
print("maximum_rendered_anatomy_pixel_mismatches=\(maximumRenderedPixelMismatches)")
print("movie_resolution=\(movieWidth)x\(movieHeight)")
print("movie_fps=\(nominalFPS)")
print("movie_duration_seconds=\(duration)")
print("decoded_frames=\(decodedFrameCount)")
for state in [9, 18, 27] {
    let values = representativeResults[String(state)] ?? [:]
    print("state_\(state)_pixel_mismatches=\(values["pixel_mismatches"] ?? -1)")
    print("state_\(state)_channel_byte_mismatches=\(values["channel_byte_mismatches"] ?? -1)")
}
print("results=\(resultURL.path)")

if !failures.isEmpty {
    for failure in failures { FileHandle.standardError.write(Data("FAIL: \(failure)\n".utf8)) }
    exit(1)
}
