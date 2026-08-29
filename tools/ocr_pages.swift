// Read a directory of page scans and recognise their text with Vision.
//
// The second witness for a collated edition has to be an INDEPENDENT reading of
// an independent printing. Archive.org's own text comes from 2008-era OCR; this
// is Apple's current recogniser running on the same kind of page, locally, and
// on the evidence it is markedly better. Nothing leaves the machine.
//
//   swiftc -O tools/ocr_pages.swift -o /tmp/ocr_pages
//   /tmp/ocr_pages <scan-dir> <out-dir> [--no-language-correction]
//
// For each page it writes:
//   page_NNNN.txt   the lines, in reading order, nothing removed
//   page_NNNN.tsv   line<TAB>ymin<TAB>ymax<TAB>confidence
//
// ⚠️ The .txt keeps EVERYTHING — running heads, page numbers, catchwords. The
// .tsv is how they are found and dropped later: furniture sits at the very top
// or bottom of the page, and its y tells you so. Stripping here would be
// throwing away evidence before anyone had looked at it.

import Foundation
import Vision
import CoreGraphics
import ImageIO

let args = CommandLine.arguments
guard args.count >= 3 else {
    FileHandle.standardError.write(
        "usage: ocr_pages <scan-dir> <out-dir> [--no-language-correction]\n".data(using: .utf8)!)
    exit(2)
}
let inDir = URL(fileURLWithPath: args[1])
let outDir = URL(fileURLWithPath: args[2])
let languageCorrection = !args.contains("--no-language-correction")
try? FileManager.default.createDirectory(at: outDir, withIntermediateDirectories: true)

let exts: Set<String> = ["tif", "tiff", "png", "jpg", "jpeg", "jp2"]
let pages = ((try? FileManager.default.contentsOfDirectory(at: inDir,
                includingPropertiesForKeys: nil)) ?? [])
    .filter { exts.contains($0.pathExtension.lowercased()) }
    .sorted { $0.lastPathComponent < $1.lastPathComponent }

guard !pages.isEmpty else {
    FileHandle.standardError.write("no page images in \(inDir.path)\n".data(using: .utf8)!)
    exit(1)
}
FileHandle.standardError.write(
    "\(pages.count) pages · language correction \(languageCorrection ? "on" : "off")\n"
        .data(using: .utf8)!)

let counter = NSLock()
var done = 0, failed = 0, totalLines = 0

DispatchQueue.concurrentPerform(iterations: pages.count) { i in
    let page = pages[i]
    let stem = page.deletingPathExtension().lastPathComponent

    guard let src = CGImageSourceCreateWithURL(page as CFURL, nil),
          let image = CGImageSourceCreateImageAtIndex(src, 0, nil) else {
        counter.lock(); failed += 1; counter.unlock(); return
    }

    let request = VNRecognizeTextRequest()
    request.recognitionLevel = .accurate
    request.usesLanguageCorrection = languageCorrection
    // A Victorian novel: no custom vocabulary, but the recogniser should not be
    // guessing at other languages.
    request.recognitionLanguages = ["en-US"]
    if #available(macOS 13.0, *) {
        request.revision = VNRecognizeTextRequestRevision3
    }

    do {
        try VNImageRequestHandler(cgImage: image, options: [:]).perform([request])
    } catch {
        counter.lock(); failed += 1; counter.unlock(); return
    }

    let observations = (request.results ?? [])
    // Vision returns observations in no guaranteed order; reading order is
    // top-to-bottom, then left-to-right for anything sharing a line.
    let lines = observations.sorted { a, b in
        let dy = b.boundingBox.midY - a.boundingBox.midY
        if abs(dy) > 0.004 { return dy < 0 }
        return a.boundingBox.minX < b.boundingBox.minX
    }

    var text = "", tsv = ""
    for line in lines {
        guard let best = line.topCandidates(1).first else { continue }
        text += best.string + "\n"
        // ⚠️ Vision's y runs from the BOTTOM. Flip it, so 0 is the top of the
        // page and a running head reads as a small number like everyone expects.
        let top = 1 - line.boundingBox.maxY
        let bottom = 1 - line.boundingBox.minY
        let clean = best.string.replacingOccurrences(of: "\t", with: " ")
        tsv += String(format: "%@\t%.4f\t%.4f\t%.3f\n", clean, top, bottom, best.confidence)
    }

    try? text.write(to: outDir.appendingPathComponent("\(stem).txt"),
                    atomically: true, encoding: .utf8)
    try? tsv.write(to: outDir.appendingPathComponent("\(stem).tsv"),
                   atomically: true, encoding: .utf8)

    counter.lock()
    done += 1
    totalLines += lines.count
    if done % 25 == 0 {
        FileHandle.standardError.write("  \(done)/\(pages.count)\n".data(using: .utf8)!)
    }
    counter.unlock()
}

FileHandle.standardError.write(
    "done: \(done) pages, \(totalLines) lines, \(failed) failed\n".data(using: .utf8)!)
exit(failed > 0 ? 1 : 0)
