import AVFoundation
import CoreGraphics
import CoreVideo
import Foundation
import ImageIO

guard (CommandLine.arguments.count == 4 || CommandLine.arguments.count == 5),
      let fps = Int32(CommandLine.arguments[3]), fps > 0 else {
    fputs("usage: png_sequence_to_mp4 FRAME_DIR OUTPUT.mp4 FPS [SCALE]\n", stderr)
    exit(2)
}
let requestedScale = CommandLine.arguments.count == 5 ? Int(CommandLine.arguments[4]) : 6
guard let scale = requestedScale, scale > 0 else {
    fputs("scale must be a positive integer\n", stderr)
    exit(2)
}

let directory = URL(fileURLWithPath: CommandLine.arguments[1], isDirectory: true)
let output = URL(fileURLWithPath: CommandLine.arguments[2])
let files = try FileManager.default.contentsOfDirectory(
    at: directory,
    includingPropertiesForKeys: nil
).filter { $0.pathExtension.lowercased() == "png" }
 .sorted { $0.lastPathComponent < $1.lastPathComponent }

guard let firstURL = files.first,
      let firstSource = CGImageSourceCreateWithURL(firstURL as CFURL, nil),
      let first = CGImageSourceCreateImageAtIndex(firstSource, 0, nil) else {
    fputs("no readable PNG frames\n", stderr)
    exit(1)
}

if FileManager.default.fileExists(atPath: output.path) {
    try FileManager.default.removeItem(at: output)
}

let writer = try AVAssetWriter(outputURL: output, fileType: .mp4)
let videoWidth = first.width * scale
let videoHeight = first.height * scale
let settings: [String: Any] = [
    AVVideoCodecKey: AVVideoCodecType.h264,
    AVVideoWidthKey: videoWidth,
    AVVideoHeightKey: videoHeight,
    AVVideoCompressionPropertiesKey: [
        AVVideoAverageBitRateKey: 2_000_000,
        AVVideoProfileLevelKey: AVVideoProfileLevelH264HighAutoLevel
    ]
]
let input = AVAssetWriterInput(mediaType: .video, outputSettings: settings)
input.expectsMediaDataInRealTime = false
let attributes: [String: Any] = [
    kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA,
    kCVPixelBufferWidthKey as String: videoWidth,
    kCVPixelBufferHeightKey as String: videoHeight
]
let adaptor = AVAssetWriterInputPixelBufferAdaptor(
    assetWriterInput: input,
    sourcePixelBufferAttributes: attributes
)
guard writer.canAdd(input) else {
    fputs("video input rejected\n", stderr)
    exit(1)
}
writer.add(input)
writer.startWriting()
writer.startSession(atSourceTime: .zero)

func makePixelBuffer(_ image: CGImage) -> CVPixelBuffer? {
    var buffer: CVPixelBuffer?
    let status = CVPixelBufferCreate(
        kCFAllocatorDefault,
        videoWidth,
        videoHeight,
        kCVPixelFormatType_32BGRA,
        attributes as CFDictionary,
        &buffer
    )
    guard status == kCVReturnSuccess, let buffer else { return nil }
    CVPixelBufferLockBaseAddress(buffer, [])
    defer { CVPixelBufferUnlockBaseAddress(buffer, []) }
    guard let context = CGContext(
        data: CVPixelBufferGetBaseAddress(buffer),
        width: videoWidth,
        height: videoHeight,
        bitsPerComponent: 8,
        bytesPerRow: CVPixelBufferGetBytesPerRow(buffer),
        space: CGColorSpaceCreateDeviceRGB(),
        bitmapInfo: CGImageAlphaInfo.premultipliedFirst.rawValue |
            CGBitmapInfo.byteOrder32Little.rawValue
    ) else { return nil }
    context.setFillColor(CGColor(gray: 0, alpha: 1))
    context.fill(CGRect(x: 0, y: 0, width: videoWidth, height: videoHeight))
    context.interpolationQuality = .none
    context.draw(image, in: CGRect(x: 0, y: 0, width: videoWidth, height: videoHeight))
    return buffer
}

for (index, url) in files.enumerated() {
    guard let source = CGImageSourceCreateWithURL(url as CFURL, nil),
          let image = CGImageSourceCreateImageAtIndex(source, 0, nil),
          let buffer = makePixelBuffer(image) else {
        fputs("unreadable frame: \(url.path)\n", stderr)
        exit(1)
    }
    while !input.isReadyForMoreMediaData {
        Thread.sleep(forTimeInterval: 0.002)
    }
    let time = CMTime(value: Int64(index), timescale: fps)
    guard adaptor.append(buffer, withPresentationTime: time) else {
        fputs("could not append frame \(index)\n", stderr)
        exit(1)
    }
}

input.markAsFinished()
let semaphore = DispatchSemaphore(value: 0)
writer.finishWriting { semaphore.signal() }
semaphore.wait()
if writer.status != .completed {
    fputs("video encoding failed: \(writer.error?.localizedDescription ?? "unknown")\n", stderr)
    exit(1)
}
