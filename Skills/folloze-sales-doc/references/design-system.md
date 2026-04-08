# Folloze Sales Doc — Design System Reference

This file contains the complete set of reusable design constants and component functions for all Folloze sales documents. Copy these verbatim into every document generation script.

---

## Brand Colors

```javascript
const BRAND_BLUE  = "1E3A5F";   // Navy — headers, headings, labels
const ACCENT_TEAL = "0EA5E9";   // Teal — accents, underlines, highlights
const LIGHT_BLUE  = "EFF6FF";   // Light blue — alternating table rows
const LIGHT_GRAY  = "F8FAFC";   // Near-white — quote boxes, subtle backgrounds
const MID_GRAY    = "94A3B8";   // Gray — footer text, secondary labels
const SLATE       = "475569";   // Slate — secondary body text
const DARK        = "1E293B";   // Near-black — primary body text
const WHITE       = "FFFFFF";
```

---

## Page Setup

Always use US Letter with 1-inch side margins and slightly tighter top/bottom:

```javascript
sections: [{
  properties: {
    page: {
      size: { width: 12240, height: 15840 },
      margin: { top: 1080, right: 1260, bottom: 1080, left: 1260 }
    }
  },
  children: [ /* content */ ]
}]
// Content width = 12240 - 1260 - 1260 = 9720 DXA
// Use 9360 for tables (leaves a small visual margin)
```

---

## Document Styles Block

Always include this styles block in every Document constructor:

```javascript
styles: {
  default: { document: { run: { font: "Arial", size: 20 } } },
  paragraphStyles: [
    {
      id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
      run: { size: 28, bold: true, font: "Arial", color: BRAND_BLUE },
      paragraph: { spacing: { before: 320, after: 120 }, outlineLevel: 0 }
    },
    {
      id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
      run: { size: 22, bold: true, font: "Arial", color: BRAND_BLUE },
      paragraph: { spacing: { before: 240, after: 80 }, outlineLevel: 1 }
    }
  ]
}
```

---

## Numbering Config (Bullets)

Always include in Document constructor alongside styles:

```javascript
numbering: {
  config: [
    {
      reference: "bullets",
      levels: [{
        level: 0, format: LevelFormat.BULLET, text: "•",
        alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 480, hanging: 240 } } }
      }]
    }
  ]
}
```

---

## Border Helpers

```javascript
const border    = { style: BorderStyle.SINGLE, size: 1, color: "E2E8F0" };
const borders   = { top: border, bottom: border, left: border, right: border };
const noBorder  = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
const noBorders = { top: noBorder, bottom: noBorder, left: noBorder, right: noBorder };
```

---

## Component Functions

### h1(text) — Section Heading with Teal Underline
```javascript
function h1(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    spacing: { before: 320, after: 120 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 3, color: ACCENT_TEAL, space: 4 } },
    children: [new TextRun({ text, font: "Arial", size: 28, bold: true, color: BRAND_BLUE })]
  });
}
```

### h2(text) — Sub-section Heading
```javascript
function h2(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    spacing: { before: 240, after: 80 },
    children: [new TextRun({ text, font: "Arial", size: 22, bold: true, color: BRAND_BLUE })]
  });
}
```

### body(text, opts) — Body Paragraph
```javascript
function body(text, opts = {}) {
  return new Paragraph({
    spacing: { before: 60, after: 60 },
    children: [new TextRun({ text, font: "Arial", size: 20, color: DARK, ...opts })]
  });
}
```

### bullet(text, bold_prefix) — Bullet Point
```javascript
// bold_prefix is optional — use for "Label: description" bullets
function bullet(text, bold_prefix = null) {
  return new Paragraph({
    numbering: { reference: "bullets", level: 0 },
    spacing: { before: 40, after: 40 },
    children: bold_prefix
      ? [
          new TextRun({ text: bold_prefix + " ", font: "Arial", size: 20, bold: true, color: DARK }),
          new TextRun({ text, font: "Arial", size: 20, color: DARK })
        ]
      : [new TextRun({ text, font: "Arial", size: 20, color: DARK })]
  });
}
```

### sectionSpacer() — Vertical Whitespace
```javascript
function sectionSpacer() {
  return new Paragraph({ spacing: { before: 40, after: 40 }, children: [new TextRun("")] });
}
```

### labelValue(label, value) — Inline Label: Value
```javascript
function labelValue(label, value) {
  return new Paragraph({
    spacing: { before: 50, after: 50 },
    children: [
      new TextRun({ text: label + ": ", font: "Arial", size: 20, bold: true, color: BRAND_BLUE }),
      new TextRun({ text: value, font: "Arial", size: 20, color: DARK })
    ]
  });
}
```

---

## Table Components

### headerBlock(title, subtitle, meta) — Full-Width Navy Header
```javascript
// title     = e.g. "Tailscale — ABM Manager"
// subtitle  = e.g. "DISCOVERY CALL PREP"
// meta      = e.g. "Selling: Folloze  │  Date: March 11, 2026"
function headerBlock(title, subtitle, meta) {
  return new Table({
    width: { size: 9360, type: WidthType.DXA },
    columnWidths: [9360],
    rows: [
      new TableRow({
        children: [
          new TableCell({
            borders: noBorders,
            width: { size: 9360, type: WidthType.DXA },
            shading: { fill: BRAND_BLUE, type: ShadingType.CLEAR },
            margins: { top: 280, bottom: 280, left: 360, right: 360 },
            children: [
              new Paragraph({
                spacing: { after: 60 },
                children: [new TextRun({ text: subtitle, font: "Arial", size: 18, color: ACCENT_TEAL, bold: true })]
              }),
              new Paragraph({
                spacing: { after: 80 },
                children: [new TextRun({ text: title, font: "Arial", size: 34, bold: true, color: WHITE })]
              }),
              new Paragraph({
                children: [new TextRun({ text: meta, font: "Arial", size: 19, color: "CBD5E1" })]
              })
            ]
          })
        ]
      })
    ]
  });
}
```

### twoColTable(rows) — Label | Value Table (alternating rows)
```javascript
// rows = array of [label, value] pairs
function twoColTable(rows) {
  return new Table({
    width: { size: 9360, type: WidthType.DXA },
    columnWidths: [2200, 7160],
    rows: rows.map((r, i) =>
      new TableRow({
        children: [
          new TableCell({
            borders,
            width: { size: 2200, type: WidthType.DXA },
            shading: { fill: i % 2 === 0 ? "EFF6FF" : WHITE, type: ShadingType.CLEAR },
            margins: { top: 80, bottom: 80, left: 120, right: 120 },
            children: [new Paragraph({
              children: [new TextRun({ text: r[0], font: "Arial", size: 19, bold: true, color: BRAND_BLUE })]
            })]
          }),
          new TableCell({
            borders,
            width: { size: 7160, type: WidthType.DXA },
            shading: { fill: i % 2 === 0 ? "EFF6FF" : WHITE, type: ShadingType.CLEAR },
            margins: { top: 80, bottom: 80, left: 120, right: 120 },
            children: [new Paragraph({
              children: [new TextRun({ text: r[1], font: "Arial", size: 19, color: DARK })]
            })]
          })
        ]
      })
    )
  });
}
```

### calloutBox(title, lines) — Full-Width Navy Callout
```javascript
// Use for "Why Now", key signals, situation summaries, strategic context
function calloutBox(title, lines) {
  return new Table({
    width: { size: 9360, type: WidthType.DXA },
    columnWidths: [9360],
    rows: [
      new TableRow({
        children: [
          new TableCell({
            borders,
            width: { size: 9360, type: WidthType.DXA },
            shading: { fill: BRAND_BLUE, type: ShadingType.CLEAR },
            margins: { top: 160, bottom: 160, left: 200, right: 200 },
            children: [
              new Paragraph({
                spacing: { before: 60, after: 80 },
                children: [new TextRun({ text: title, font: "Arial", size: 20, bold: true, color: WHITE })]
              }),
              ...lines.map(l => new Paragraph({
                spacing: { before: 40, after: 40 },
                children: [new TextRun({ text: "› " + l, font: "Arial", size: 19, color: WHITE })]
              }))
            ]
          })
        ]
      })
    ]
  });
}
```

### personCard(name, title, notes) — Contact Profile Card
```javascript
// Use for key contacts, champions, stakeholders
function personCard(name, title, notes) {
  return new Table({
    width: { size: 9360, type: WidthType.DXA },
    columnWidths: [9360],
    rows: [
      new TableRow({
        children: [
          new TableCell({
            borders,
            width: { size: 9360, type: WidthType.DXA },
            shading: { fill: "F0F9FF", type: ShadingType.CLEAR },
            margins: { top: 120, bottom: 120, left: 180, right: 180 },
            children: [
              new Paragraph({
                spacing: { after: 40 },
                children: [
                  new TextRun({ text: name, font: "Arial", size: 22, bold: true, color: BRAND_BLUE }),
                  new TextRun({ text: "  ·  " + title, font: "Arial", size: 19, color: SLATE })
                ]
              }),
              new Paragraph({
                children: [new TextRun({ text: notes, font: "Arial", size: 19, color: DARK })]
              })
            ]
          })
        ]
      })
    ]
  });
}
```

### quoteBox(lines) — Light Gray Quote / Dialogue Box
```javascript
// Use for suggested openers, sample scripts, key quotes from the prospect
function quoteBox(lines) {
  return new Table({
    width: { size: 9360, type: WidthType.DXA },
    columnWidths: [9360],
    rows: [
      new TableRow({
        children: [
          new TableCell({
            borders,
            width: { size: 9360, type: WidthType.DXA },
            shading: { fill: LIGHT_GRAY, type: ShadingType.CLEAR },
            margins: { top: 160, bottom: 160, left: 220, right: 220 },
            children: lines.map((l, i) => new Paragraph({
              spacing: { after: i < lines.length - 1 ? 80 : 0 },
              children: [new TextRun({ text: l, font: "Arial", size: 19, italics: true, color: "334155" })]
            }))
          })
        ]
      })
    ]
  });
}
```

### statusTable(rows) — Traffic Light / Health Status Table
```javascript
// rows = [[label, status, notes]] where status is "🟢 Green" / "🟡 Amber" / "🔴 Red"
// Use in Renewal Prep and QBR docs for health scoring
function statusTable(rows) {
  return new Table({
    width: { size: 9360, type: WidthType.DXA },
    columnWidths: [2800, 1400, 5160],
    rows: [
      // Header row
      new TableRow({
        children: ["Area", "Status", "Notes"].map((h, idx) =>
          new TableCell({
            borders,
            width: { size: [2800, 1400, 5160][idx], type: WidthType.DXA },
            shading: { fill: BRAND_BLUE, type: ShadingType.CLEAR },
            margins: { top: 80, bottom: 80, left: 120, right: 120 },
            children: [new Paragraph({
              children: [new TextRun({ text: h, font: "Arial", size: 19, bold: true, color: WHITE })]
            })]
          })
        )
      }),
      // Data rows
      ...rows.map((r, i) =>
        new TableRow({
          children: r.map((cell, idx) =>
            new TableCell({
              borders,
              width: { size: [2800, 1400, 5160][idx], type: WidthType.DXA },
              shading: { fill: i % 2 === 0 ? LIGHT_BLUE : WHITE, type: ShadingType.CLEAR },
              margins: { top: 80, bottom: 80, left: 120, right: 120 },
              children: [new Paragraph({
                children: [new TextRun({ text: cell, font: "Arial", size: 19, color: DARK })]
              })]
            })
          )
        })
      )
    ]
  });
}
```

### milestoneTable(rows) — 30/60/90 Day or Phase Table
```javascript
// rows = [[phase, owner, goal, status]]
// Use in Onboarding Plan docs
function milestoneTable(rows) {
  const colWidths = [1400, 1800, 4360, 1800];
  const headers = ["Phase", "Owner", "Goal", "Status"];
  return new Table({
    width: { size: 9360, type: WidthType.DXA },
    columnWidths: colWidths,
    rows: [
      new TableRow({
        children: headers.map((h, idx) =>
          new TableCell({
            borders,
            width: { size: colWidths[idx], type: WidthType.DXA },
            shading: { fill: BRAND_BLUE, type: ShadingType.CLEAR },
            margins: { top: 80, bottom: 80, left: 120, right: 120 },
            children: [new Paragraph({
              children: [new TextRun({ text: h, font: "Arial", size: 19, bold: true, color: WHITE })]
            })]
          })
        )
      }),
      ...rows.map((r, i) =>
        new TableRow({
          children: r.map((cell, idx) =>
            new TableCell({
              borders,
              width: { size: colWidths[idx], type: WidthType.DXA },
              shading: { fill: i % 2 === 0 ? LIGHT_BLUE : WHITE, type: ShadingType.CLEAR },
              margins: { top: 80, bottom: 80, left: 120, right: 120 },
              children: [new Paragraph({
                children: [new TextRun({ text: cell, font: "Arial", size: 19, color: DARK })]
              })]
            })
          )
        })
      )
    ]
  });
}
```

---

## Footer

Always end every document with a centered footer paragraph:

```javascript
new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { before: 160 },
  children: [
    new TextRun({
      text: "Prepared by Folloze  ·  [Account Name]  ·  [Date]",
      font: "Arial", size: 17, color: MID_GRAY
    })
  ]
})
```

---

## Boilerplate Script Shell

Use this as the starting point for every document generation script:

```javascript
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  HeadingLevel, AlignmentType, BorderStyle, WidthType, ShadingType, LevelFormat
} = require('docx');
const fs = require('fs');

// ── COLORS ──────────────────────────────────────────────
const BRAND_BLUE  = "1E3A5F";
const ACCENT_TEAL = "0EA5E9";
const LIGHT_BLUE  = "EFF6FF";
const LIGHT_GRAY  = "F8FAFC";
const MID_GRAY    = "94A3B8";
const SLATE       = "475569";
const DARK        = "1E293B";
const WHITE       = "FFFFFF";

// ── BORDERS ─────────────────────────────────────────────
const border    = { style: BorderStyle.SINGLE, size: 1, color: "E2E8F0" };
const borders   = { top: border, bottom: border, left: border, right: border };
const noBorder  = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
const noBorders = { top: noBorder, bottom: noBorder, left: noBorder, right: noBorder };

// ── COMPONENT FUNCTIONS ──────────────────────────────────
// [paste h1, h2, body, bullet, sectionSpacer, labelValue,
//  headerBlock, twoColTable, calloutBox, personCard,
//  quoteBox, statusTable, milestoneTable here]

// ── DOCUMENT ─────────────────────────────────────────────
const doc = new Document({
  numbering: {
    config: [{
      reference: "bullets",
      levels: [{ level: 0, format: LevelFormat.BULLET, text: "•",
        alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 480, hanging: 240 } } } }]
    }]
  },
  styles: {
    default: { document: { run: { font: "Arial", size: 20 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 28, bold: true, font: "Arial", color: BRAND_BLUE },
        paragraph: { spacing: { before: 320, after: 120 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 22, bold: true, font: "Arial", color: BRAND_BLUE },
        paragraph: { spacing: { before: 240, after: 80 }, outlineLevel: 1 } },
    ]
  },
  sections: [{
    properties: {
      page: {
        size: { width: 12240, height: 15840 },
        margin: { top: 1080, right: 1260, bottom: 1080, left: 1260 }
      }
    },
    children: [
      // content goes here
    ]
  }]
});

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync('/mnt/user-data/outputs/[Account]_[DocType]_Folloze.docx', buf);
  console.log('Done!');
});
```

---

## Component Usage Guide

| Component | When to Use |
|---|---|
| `headerBlock` | Top of every document — always first |
| `twoColTable` | Structured facts: snapshots, cheat sheets, quick refs |
| `calloutBox` | High-priority signals, situation summaries, strategic context |
| `personCard` | Any named contact — champion, stakeholder, exec |
| `quoteBox` | Suggested scripts, meeting openers, key quotes from prospect |
| `statusTable` | Health scoring, renewal risk, QBR traffic lights |
| `milestoneTable` | Onboarding phases, project timelines, 30/60/90 plans |
| `h1` + `h2` | Section and sub-section headings throughout |
| `bullet` | Lists within sections; use `bold_prefix` for labeled lists |
| `sectionSpacer` | Between any two block elements for breathing room |
