/**
 * Render analysis/report/report.md as a Word document.
 *
 * Written as a converter rather than a hand-built document so the .docx can be
 * regenerated whenever the report changes: it parses the markdown (headings,
 * tables, figures, lists, code, inline emphasis) and emits styled docx-js
 * elements.
 *
 *   node analysis/scripts/32_report_docx.js
 */
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType,
  Table, TableRow, TableCell, WidthType, ShadingType, BorderStyle,
  ImageRun, LevelFormat, PageOrientation,
} = require("docx");

const ROOT = path.resolve(__dirname, "..", "..");
const ANALYSIS_DIR = path.join(ROOT, "analysis");
const REPORT_DIR = path.join(ANALYSIS_DIR, "report");
// defaults to the full study report; pass a markdown path to render another
// document (the long-form article uses the same converter)
const SRC = process.argv[2] || "report.md";
const MD = path.isAbsolute(SRC) ? SRC : path.join(REPORT_DIR, SRC);
const OUT = MD.replace(/\.md$/, ".docx");

// US Letter, 1" margins -> content width in DXA (1440 per inch)
const PAGE_W = 12240, MARGIN = 1440;
const CONTENT_W = PAGE_W - 2 * MARGIN;
const CONTENT_PX = 624; // 6.5in at 96dpi, for image scaling

const BODY = "Cambria", HEAD = "Calibri", MONO = "Consolas";
const INK = "1A1A1A", MUTED = "595959", RULE = "D9D9D9", ACCENT = "1F4E79";

/** PNG intrinsic size, read straight from the IHDR chunk. */
function pngSize(file) {
  const b = fs.readFileSync(file);
  return { w: b.readUInt32BE(16), h: b.readUInt32BE(20) };
}

/**
 * Split a line of markdown into runs, honouring **bold**, *italic* and `code`.
 * Handled with one pass so nested markers do not produce stray asterisks.
 */
function inlineRuns(text, base = {}) {
  const runs = [];
  const re = /(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g;
  let last = 0, m;
  const push = (t, extra) => {
    if (t) runs.push(new TextRun({ text: t, font: BODY, size: 21, color: INK, ...base, ...extra }));
  };
  while ((m = re.exec(text)) !== null) {
    push(text.slice(last, m.index));
    const tok = m[0];
    if (tok.startsWith("**")) push(tok.slice(2, -2), { bold: true });
    else if (tok.startsWith("`")) push(tok.slice(1, -1), { font: MONO, size: 19 });
    else push(tok.slice(1, -1), { italics: true, color: MUTED });
    last = m.index + tok.length;
  }
  push(text.slice(last));
  return runs.length ? runs : [new TextRun({ text: "", font: BODY, size: 21 })];
}

const para = (text, opts = {}) =>
  new Paragraph({ children: inlineRuns(text), spacing: { after: 140, line: 276 }, ...opts });

/** Column widths proportional to content, clamped so no column collapses. */
function columnWidths(rows) {
  const n = rows[0].length;
  const longest = Array(n).fill(1);
  rows.forEach((r) => r.forEach((c, i) => {
    longest[i] = Math.max(longest[i], c.replace(/\*\*|`/g, "").length);
  }));
  const floor = 6;
  const adj = longest.map((v) => Math.max(v, floor));
  const total = adj.reduce((a, b) => a + b, 0);
  const w = adj.map((v) => Math.round((v / total) * CONTENT_W));
  // absorb rounding drift into the last column so the sum matches exactly
  w[n - 1] += CONTENT_W - w.reduce((a, b) => a + b, 0);
  return w;
}

function buildTable(header, body) {
  const widths = columnWidths([header, ...body]);
  const cell = (text, i, isHead) =>
    new TableCell({
      width: { size: widths[i], type: WidthType.DXA },
      shading: isHead
        ? { type: ShadingType.CLEAR, fill: "F2F2F2", color: "auto" }
        : undefined,
      margins: { top: 60, bottom: 60, left: 90, right: 90 },
      children: [new Paragraph({
        spacing: { after: 0, line: 240 },
        alignment: i === 0 ? AlignmentType.LEFT : AlignmentType.RIGHT,
        children: inlineRuns(text, {
          font: isHead ? HEAD : (i === 0 ? BODY : MONO),
          size: isHead ? 17 : 18,
          bold: isHead || undefined,
          color: isHead ? MUTED : INK,
        }),
      })],
    });
  const border = { style: BorderStyle.SINGLE, size: 2, color: RULE };
  return new Table({
    columnWidths: widths,
    width: { size: CONTENT_W, type: WidthType.DXA },
    borders: {
      top: border, bottom: border, left: border, right: border,
      insideHorizontal: border, insideVertical: border,
    },
    rows: [
      new TableRow({
        tableHeader: true,
        children: header.map((c, i) => cell(c, i, true)),
      }),
      ...body.map((r) => new TableRow({ children: r.map((c, i) => cell(c, i, false)) })),
    ],
  });
}

const splitRow = (line) =>
  line.trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map((s) => s.trim());

function convert(md) {
  const lines = md.split("\n");
  const out = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];
    const t = line.trim();

    if (!t) { i++; continue; }

    // horizontal rule -> thin spacer rule between major sections
    if (/^---+$/.test(t)) {
      out.push(new Paragraph({
        spacing: { before: 60, after: 180 },
        border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: RULE } },
        children: [new TextRun({ text: "", size: 2 })],
      }));
      i++; continue;
    }

    // fenced code
    if (t.startsWith("```")) {
      i++;
      const buf = [];
      while (i < lines.length && !lines[i].trim().startsWith("```")) buf.push(lines[i++]);
      i++;
      buf.forEach((c) => out.push(new Paragraph({
        spacing: { after: 0, line: 240 },
        shading: { type: ShadingType.CLEAR, fill: "F7F7F5", color: "auto" },
        children: [new TextRun({ text: c || " ", font: MONO, size: 18, color: INK })],
      })));
      out.push(new Paragraph({ spacing: { after: 140 }, children: [] }));
      continue;
    }

    // figure
    const img = t.match(/^!\[([^\]]*)\]\(([^)]+)\)$/);
    if (img) {
      // figure paths in the markdown are relative to analysis/, not the
      // report directory the markdown itself lives in
      const file = path.join(ANALYSIS_DIR, img[2]);
      if (fs.existsSync(file)) {
        const { w, h } = pngSize(file);
        out.push(new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { before: 80, after: 60 },
          children: [new ImageRun({
            type: "png",
            data: fs.readFileSync(file),
            transformation: { width: CONTENT_PX, height: Math.round((h / w) * CONTENT_PX) },
          })],
        }));
        out.push(new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { after: 200 },
          children: [new TextRun({ text: img[1], font: HEAD, size: 16, color: MUTED, italics: true })],
        }));
      }
      i++; continue;
    }

    // table
    if (t.startsWith("|") && i + 1 < lines.length && /^\|[\s:|-]+\|$/.test(lines[i + 1].trim())) {
      const header = splitRow(lines[i]);
      i += 2;
      const body = [];
      while (i < lines.length && lines[i].trim().startsWith("|")) body.push(splitRow(lines[i++]));
      out.push(buildTable(header, body));
      out.push(new Paragraph({ spacing: { after: 200 }, children: [] }));
      continue;
    }

    // headings
    const h = t.match(/^(#{1,4})\s+(.*)$/);
    if (h) {
      const depth = h[1].length, text = h[2];
      if (depth === 1) {
        out.push(new Paragraph({
          spacing: { after: 120 },
          children: inlineRuns(text, { font: HEAD, size: 44, bold: true, color: INK }),
        }));
      } else {
        out.push(new Paragraph({
          heading: depth === 2 ? HeadingLevel.HEADING_1 : HeadingLevel.HEADING_2,
          spacing: { before: depth === 2 ? 300 : 220, after: 120 },
          children: inlineRuns(text, {
            font: HEAD,
            size: depth === 2 ? 30 : 24,
            bold: true,
            color: depth === 2 ? ACCENT : INK,
          }),
        }));
      }
      i++; continue;
    }

    // lists
    const bullet = t.match(/^[-*]\s+(.*)$/);
    if (bullet) {
      out.push(new Paragraph({
        numbering: { reference: "bullets", level: 0 },
        spacing: { after: 100, line: 276 },
        children: inlineRuns(bullet[1]),
      }));
      i++; continue;
    }
    const num = t.match(/^\d+\.\s+(.*)$/);
    if (num) {
      out.push(new Paragraph({
        numbering: { reference: "ordered", level: 0 },
        spacing: { after: 100, line: 276 },
        children: inlineRuns(num[1]),
      }));
      i++; continue;
    }

    // the bold standfirst directly under the title
    if (/^\*\*.*\*\*$/.test(t) && out.length <= 2) {
      out.push(new Paragraph({
        spacing: { after: 260 },
        children: inlineRuns(t.slice(2, -2), { font: HEAD, size: 24, color: MUTED }),
      }));
      i++; continue;
    }

    out.push(para(t));
    i++;
  }
  return out;
}

const doc = new Document({
  creator: "mlb-statcast-pipeline",
  // an explicit Normal style, so body text has a definition to inherit from
  // rather than relying on docDefaults alone (Google Docs is stricter here)
  styles: {
    default: {
      document: {
        run: { font: BODY, size: 21, color: INK },
        paragraph: { spacing: { after: 140, line: 276 } },
      },
    },
    paragraphStyles: [{
      id: "Normal", name: "Normal", quickFormat: true,
      run: { font: BODY, size: 21, color: INK },
      paragraph: { spacing: { after: 140, line: 276 } },
    }],
  },
  title: "Is modern pitch design making MLB pitchers throw the same?",
  description: "Statcast study of pitch homogenisation, 2021-2026",
  numbering: {
    config: [
      {
        reference: "bullets",
        levels: [{
          level: 0, format: LevelFormat.BULLET, text: "•",
          alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 460, hanging: 260 } } },
        }],
      },
      {
        reference: "ordered",
        levels: [{
          level: 0, format: LevelFormat.DECIMAL, text: "%1.",
          alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 460, hanging: 260 } } },
        }],
      },
    ],
  },
  sections: [{
    properties: {
      page: {
        size: { width: PAGE_W, height: 15840, orientation: PageOrientation.PORTRAIT },
        margin: { top: MARGIN, bottom: MARGIN, left: MARGIN, right: MARGIN },
      },
    },
    children: convert(fs.readFileSync(MD, "utf8")),
  }],
});

/**
 * docx-js defines a Normal style but does not flag it as the default paragraph
 * style, so parsers other than Word cannot resolve the style of an unstyled
 * body paragraph. Marking it default is what OOXML expects and costs nothing.
 */
async function finalise(buf) {
  const JSZip = require("jszip");
  const zip = await JSZip.loadAsync(buf);
  const styles = await zip.file("word/styles.xml").async("string");
  const fixed = styles.replace(
    '<w:style w:type="paragraph" w:styleId="Normal">',
    '<w:style w:type="paragraph" w:default="1" w:styleId="Normal">',
  );
  zip.file("word/styles.xml", fixed);
  return zip.generateAsync({ type: "nodebuffer", compression: "DEFLATE" });
}

Packer.toBuffer(doc)
  .then(finalise)
  .then((buf) => {
    fs.writeFileSync(OUT, buf);
    console.log(`wrote ${OUT} (${Math.round(buf.length / 1024)} KB)`);
  });
