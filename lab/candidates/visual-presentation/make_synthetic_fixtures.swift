#!/usr/bin/env swift

import AppKit
import Foundation

let width = 704
let height = 410
let roiX = 64
let roiY = 54
let logicalWidth = 96
let logicalHeight = 48
let scale = 6

func fail(_ message: String) -> Never {
    FileHandle.standardError.write(Data("error: \(message)\n".utf8))
    exit(1)
}

guard CommandLine.arguments.count == 2 else {
    fail("usage: make_synthetic_fixtures.swift OUTPUT_DIR")
}
let output = URL(fileURLWithPath: CommandLine.arguments[1], isDirectory: true)
try? FileManager.default.createDirectory(at: output, withIntermediateDirectories: true)

func makeBitmap() -> NSBitmapImageRep {
    guard let bitmap = NSBitmapImageRep(
        bitmapDataPlanes: nil,
        pixelsWide: width,
        pixelsHigh: height,
        bitsPerSample: 8,
        samplesPerPixel: 3,
        hasAlpha: false,
        isPlanar: false,
        colorSpaceName: .calibratedRGB,
        bytesPerRow: width * 4,
        bitsPerPixel: 32
    ), let data = bitmap.bitmapData else {
        fail("cannot allocate fixture bitmap")
    }
    for y in 0..<height {
        let row = data.advanced(by: y * bitmap.bytesPerRow)
        for x in 0..<width {
            let pixel = row.advanced(by: x * 4)
            pixel[0] = 5
            pixel[1] = 7
            pixel[2] = 11
            pixel[3] = 0
        }
    }
    for y in roiY..<(roiY + logicalHeight * scale) {
        let row = data.advanced(by: y * bitmap.bytesPerRow)
        for x in roiX..<(roiX + logicalWidth * scale) {
            let pixel = row.advanced(by: x * 4)
            pixel[0] = 0
            pixel[1] = 0
            pixel[2] = 0
        }
    }
    return bitmap
}

func occupiedCells(state: Int) -> Set<Int> {
    var cells = Set<Int>()
    func occupy(_ x: Int, _ y: Int) {
        guard x >= 0, x < logicalWidth, y >= 0, y < logicalHeight else { return }
        cells.insert(y * logicalWidth + x)
    }
    for y in 0..<logicalHeight {
        occupy(0, y)
        occupy(1, y)
        occupy(logicalWidth - 2, y)
        occupy(logicalWidth - 1, y)
    }
    for x in 1..<(logicalWidth - 1) {
        let center = 23 + Int((sin(Double(x) / 11.0) * 7.0).rounded())
        let thickness = state + 1
        for dy in -thickness...thickness { occupy(x, center + dy) }
        if x > 18 && x < 48 {
            let upper = center - (x - 18) / 3
            occupy(x, upper)
            if state >= 1 { occupy(x, upper - 1) }
        }
        if x > 44 && x < 82 {
            let lower = center + (x - 44) / 4
            occupy(x, lower)
            if state >= 2 { occupy(x, lower + 1) }
        }
    }
    return cells
}

for state in 0..<3 {
    let bitmap = makeBitmap()
    guard let data = bitmap.bitmapData else { fail("fixture bitmap has no data") }
    for index in occupiedCells(state: state) {
        let cellX = index % logicalWidth
        let cellY = index / logicalWidth
        for dy in 0..<scale {
            let row = data.advanced(by: (roiY + cellY * scale + dy) * bitmap.bytesPerRow)
            for dx in 0..<scale {
                let pixel = row.advanced(by: (roiX + cellX * scale + dx) * 4)
                pixel[0] = 255
                pixel[1] = 255
                pixel[2] = 255
            }
        }
    }
    guard let png = bitmap.representation(using: .png, properties: [:]) else {
        fail("cannot encode fixture state \(state)")
    }
    let path = output.appendingPathComponent(String(format: "frame.%04d.png", state))
    try! png.write(to: path, options: .atomic)
}

print("synthetic_states=3")
print("source_resolution=704x410")
print("lattice_roi=64,54,576,288")
print("logical_lattice=96x48")
print("cell_scale=6")
