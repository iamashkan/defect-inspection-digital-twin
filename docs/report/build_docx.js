// Build thesis.docx — the Word version of the project report.
const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, ImageRun,
  Footer, AlignmentType, LevelFormat, HeadingLevel, BorderStyle, WidthType,
  ShadingType, TableOfContents, PageNumber, PageBreak,
} = require("docx");

const ASSETS = __dirname + "/assets/";
const CONTENT_W = 9360; // US Letter, 1" margins (DXA)

// ---- helpers ----------------------------------------------------------------
const H1 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun(t)] });
const H2 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(t)] });
const H3 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun(t)] });

function P(text, opts = {}) {
  return new Paragraph({
    spacing: { after: 120, line: 276 },
    children: [new TextRun({ text, ...opts })],
  });
}

// Paragraph with mixed runs: pass array of {text, bold, italic}
function PR(runs, opts = {}) {
  return new Paragraph({
    spacing: { after: 120, line: 276 },
    children: runs.map((r) => new TextRun(r)),
    ...opts,
  });
}

function bullet(text) {
  return new Paragraph({
    numbering: { reference: "bullets", level: 0 },
    spacing: { after: 60 },
    children: [new TextRun(text)],
  });
}

// "Why chosen" callout: shaded, left-bordered paragraph with a bold lead-in.
function why(lead, text) {
  return new Paragraph({
    spacing: { before: 80, after: 140 },
    shading: { type: ShadingType.CLEAR, fill: "F1FAF4" },
    border: { left: { style: BorderStyle.SINGLE, size: 18, color: "2ECC71", space: 8 } },
    children: [
      new TextRun({ text: lead + "  ", bold: true }),
      new TextRun({ text }),
    ],
  });
}

function figure(file, w, h, caption) {
  return [
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 120, after: 40 },
      children: [new ImageRun({
        type: "png",
        data: fs.readFileSync(ASSETS + file),
        transformation: { width: w, height: h },
        altText: { title: caption, description: caption, name: file },
      })],
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { after: 160 },
      children: [new TextRun({ text: caption, italics: true, size: 18, color: "5B6472" })],
    }),
  ];
}

const BORDER = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
const BORDERS = { top: BORDER, bottom: BORDER, left: BORDER, right: BORDER,
                  insideHorizontal: BORDER, insideVertical: BORDER };
const CELL_MARGINS = { top: 60, left: 110, bottom: 60, right: 110 };

function cell(text, width, { head = false, bold = false } = {}) {
  return new TableCell({
    width: { size: width, type: WidthType.DXA },
    margins: CELL_MARGINS,
    shading: head ? { type: ShadingType.CLEAR, fill: "EEF3FC" } : undefined,
    children: [new Paragraph({ children: [new TextRun({ text, bold: head || bold, size: 19 })] })],
  });
}

function table(colWidths, rows) {
  return new Table({
    width: { size: CONTENT_W, type: WidthType.DXA },
    columnWidths: colWidths,
    borders: BORDERS,
    rows: rows.map((cells, i) =>
      new TableRow({
        tableHeader: i === 0,
        children: cells.map((c, j) => cell(c, colWidths[j], { head: i === 0 })),
      })),
  });
}

// ---- document ---------------------------------------------------------------
const doc = new Document({
  creator: "Ashkan Aghamoali",
  title: "Defect Inspection Digital Twin — Project Report",
  styles: {
    default: { document: { run: { font: "Arial", size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 30, bold: true, color: "1D2330", font: "Arial" },
        paragraph: { spacing: { before: 320, after: 140 }, outlineLevel: 0,
          border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: "3B6FD4", space: 4 } } } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 25, bold: true, color: "27324A", font: "Arial" },
        paragraph: { spacing: { before: 240, after: 100 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 22, bold: true, color: "3B6FD4", font: "Arial" },
        paragraph: { spacing: { before: 160, after: 80 }, outlineLevel: 2 } },
    ],
  },
  numbering: {
    config: [
      { reference: "bullets",
        levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 540, hanging: 260 } } } }] },
    ],
  },
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 },
      margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } } },
    footers: {
      default: new Footer({ children: [new Paragraph({
        alignment: AlignmentType.CENTER,
        children: [
          new TextRun({ text: "Defect Inspection Digital Twin  ·  Ashkan Aghamoali  ·  page ",
            size: 16, color: "8893A4" }),
          new TextRun({ children: [PageNumber.CURRENT], size: 16, color: "8893A4" }),
        ],
      })] }),
    },
    children: [
      // ---- Title block ----
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 600, after: 60 },
        children: [new TextRun({ text: "Defect Inspection Digital Twin", bold: true, size: 44, color: "1D2330" })] }),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 40 },
        children: [new TextRun({ text: "A simulation-only computer-vision & machine-learning pipeline for",
          size: 24, color: "5B6472" })] }),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 },
        children: [new TextRun({ text: "reuse / repair / recycle decisions in circular manufacturing",
          size: 24, color: "5B6472" })] }),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 320 },
        border: { bottom: { style: BorderStyle.SINGLE, size: 12, color: "1D2330", space: 6 } },
        children: [new TextRun({ text: "Ashkan Aghamoali   ·   Project Report   ·   2026", size: 20, color: "5B6472" })] }),

      // ---- Abstract ----
      new Paragraph({ spacing: { after: 80 }, shading: { type: ShadingType.CLEAR, fill: "F7F9FC" },
        border: { top: { style: BorderStyle.SINGLE, size: 4, color: "E2E6EE", space: 6 },
                  bottom: { style: BorderStyle.SINGLE, size: 4, color: "E2E6EE", space: 6 } },
        children: [new TextRun({ text: "Abstract", bold: true, size: 24 })] }),
      P("When a worn or broken component is recovered at the end of its life, the most valuable engineering decision is what to do with it next: reuse it, repair it, or send it to material recycling. This project builds a complete, runnable system that automates that triage entirely in simulation. A PyTorch computer-vision model detects surface defects and localizes them with Grad-CAM; a transparent grading module converts the detected features into a condition score and a REUSE / REPAIR / RECYCLE decision with a confidence; a digital twin keeps a live virtual record of every part; and the whole thing is wrapped in a ROS 2 (Humble) node graph with a Gazebo inspection cell and an RViz visualization. The system is built in three independently-runnable stages, uses only free and open tools, and is fully reproducible."),

      // ---- TOC ----
      new Paragraph({ spacing: { before: 200, after: 80 }, children: [new TextRun({ text: "Contents", bold: true, size: 24 })] }),
      new TableOfContents("Contents", { hyperlink: true, headingStyleRange: "1-2" }),
      new Paragraph({ children: [new PageBreak()] }),

      // ---- 1. Introduction ----
      H1("1. Introduction & motivation"),
      P("Circular manufacturing — often abbreviated Re-X for reuse, repair, recycle — aims to keep materials and components in service for as long as possible instead of discarding them. The bottleneck is inspection and triage: every recovered part must be assessed and routed to the right recovery path. Done by hand this is slow, subjective, and inconsistent."),
      P("The objective of this project is to demonstrate, end to end and in pure simulation, how computer vision and machine learning can automate that triage: take an image of a recovered part, find and grade its surface defects, and output an auditable recovery decision, while maintaining a digital record of every part."),
      why("Design principle.", "The system is built in three layers that each run on their own — a vision stage, a decision/record stage, and a robotics-integration stage — so it can be developed, demonstrated, and graded incrementally rather than as one monolith."),

      // ---- 2. Overview ----
      H1("2. System overview"),
      P("A part image flows left to right through four logical components. The vision stage produces a defect class, a localization heatmap and a confidence; the decision stage turns those features into a condition score and a recovery decision; the digital twin records the outcome; and in Stage 3 each component becomes a ROS 2 node."),
      ...figure("architecture_pipeline.png", 600, 182, "Figure 1 — The processing pipeline and how the three build stages map onto it."),

      // ---- 3. Stage 1 ----
      H1("3. Stage 1 — Defect detection (computer vision)"),
      H3("3.1 Data"),
      P("The loader accepts any ImageFolder-style dataset, which is how the recommended public surface-defect datasets are organized — NEU-DET (six steel-surface defect classes) and the Kaggle casting product dataset (defective vs. OK). To make the whole pipeline runnable offline with zero downloads, the project also includes a synthetic data generator that paints procedural defects onto metallic-grey surfaces in three classes: good, scratch and crack."),
      why("Why a synthetic fallback?", "It guarantees the train → inference → visualization loop runs anywhere, with no dataset download, no internet, and no paid services — essential for reproducibility and a quick demo. It is a smoke test, not a benchmark; real accuracy figures come from NEU-DET or the casting dataset."),
      H3("3.2 Model — transfer learning on a lightweight backbone"),
      P("The classifier is a ResNet-18 (default) or MobileNetV3-Small backbone, pretrained on ImageNet, with a fresh classification head sized to the number of defect classes."),
      why("Why these backbones, and why fine-tuning?", "Surface-defect datasets are small, so training from scratch would overfit and be slow. A pretrained backbone already knows generic edge/texture features, so fine-tuning converges in minutes on a mid-range GPU. ResNet-18 is a strong default; MobileNetV3-Small is the lighter option for edge deployment. Both are small and fast — exactly the project's constraint."),
      H3("3.3 Localization — Grad-CAM as the defect “mask”"),
      P("For each image the system must output not only what defect is present but where. Rather than requiring pixel-level annotations, the project uses Grad-CAM (Gradient-weighted Class Activation Mapping): it weights the final convolutional layer's activation maps by the gradient of the predicted class score, producing a class-discriminative heatmap. Thresholding that heatmap yields a binary defect mask and a defect-area %."),
      why("Why Grad-CAM instead of segmentation?", "A segmentation model (e.g. U-Net) needs pixel-accurate masks, which the public datasets mostly lack. Grad-CAM needs only image-level class labels, adds almost no training cost, and still gives a defect location and an area-based severity proxy. The downstream contract is unchanged, so a U-Net can be swapped in later."),
      H3("3.4 Training method"),
      P("Training uses the AdamW optimizer with a cosine learning-rate schedule, cross-entropy loss with light label smoothing, gentle augmentation, fixed seeds for reproducibility, and best-on-validation checkpointing. It can run on a free Google Colab GPU via the included notebook."),
      why("Why gentle augmentation?", "Defects are subtle texture cues; aggressive colour or crop jitter can destroy the very signal the model needs, so augmentation is deliberately mild."),
      H3("3.5 Results"),
      P("On the offline synthetic dataset, a 2–5 epoch fine-tune reaches roughly 0.88 test accuracy in about a minute on CPU. Each image yields a class, a confidence, a defect-area %, and the three-panel overlay below."),
      ...figure("stage1_overlay.png", 600, 200, "Figure 2 — Per-image output: original | Grad-CAM heatmap | overlay. The heatmap lands on the fracture (crack 100.0% area=21.1%)."),
      ...figure("stage1_confusion.png", 300, 300, "Figure 3 — Row-normalized confusion matrix; a strong diagonal indicates good class separation."),

      // ---- 4. Stage 2 ----
      H1("4. Stage 2 — Grading, decision & digital twin"),
      H3("4.1 From defect features to a condition score"),
      P("The grader converts three features — defect class, defect area %, and model confidence — into a condition score on a 0–100 scale using a transparent rule: condition = 100 × (1 − penalty), where penalty = severity_weight · severity(class) + area_weight · (area% / area_full). severity(class) ranges from 0 (cosmetic, e.g. a scratch) to 1 (structural, e.g. a crack). The score then maps to a decision: below 50 → RECYCLE, 50–80 → REPAIR, 80 and above → REUSE."),
      ...figure("stage2_grading_bands.png", 600, 143, "Figure 4 — Condition score → recovery decision, with the three demo classes placed by their scores."),
      why("Why a transparent rule instead of a black box?", "In a real inspection setting an unexplained “RECYCLE” is hard to trust or audit. Every term in this rule is inspectable, the thresholds are adjustable, and the decision confidence is deliberately lowered when the score sits near a band boundary. It is explainable by construction."),
      H3("4.2 The digital twin"),
      P("Each inspected part is appended to a digital-twin store (a JSON-Lines file) as one record holding the part id, timestamp, predicted class, condition score, decision, decision confidence, and the heatmap/overlay paths. The store is append-only, human-readable, and loadable into pandas — no database server required."),
      why("Why JSON-Lines rather than a database?", "It is zero-setup, diff-friendly, and exactly enough for a single-cell simulation. The data layer is isolated behind a small class, so swapping in SQLite later is a one-file change."),
      H3("4.3 Dashboard & results"),
      P("A Streamlit dashboard provides an Inspect view (pick a part, run the model live, see the decision badge + overlay, record it) and a Statistics view (parts inspected, average condition, recovery rate, decision-mix chart). Running the headless pipeline over the 24-image synthetic test set routes clean parts to REUSE, cosmetic defects to REPAIR, and cracks to RECYCLE, and computes a running recovery rate (the share kept in service)."),
      ...figure("stage2_decision_dist.png", 380, 255, "Figure 5 — Decision distribution recorded in the digital twin over 24 inspected parts."),

      // ---- 5. Stage 3 ----
      H1("5. Stage 3 — ROS 2 / Gazebo / RViz integration"),
      P("Stage 3 turns the pipeline into a robotics system. Four ROS 2 (Humble) nodes each own one concern and pass typed messages:"),
      table([1900, 1700, 2860, 2900], [
        ["Node", "Subscribes", "Publishes", "Role"],
        ["camera_node", "—", "/inspection/image_raw", "Streams recovered-part images (simulated camera)."],
        ["inspection_node", "image_raw", "/inspection/overlay, /detection", "Runs the Stage 1 model + Grad-CAM."],
        ["decision_node", "detection", "/inspection/result", "Stage 2 grading → decision."],
        ["digital_twin_node", "result", "/inspection/decision_marker", "Records the part; colored RViz markers."],
      ]),
      P("A minimal Gazebo world provides the inspection cell — a table, a part, and a fixed downward camera — and an RViz configuration shows the live overlay image and a color-coded decision marker (green REUSE / amber REPAIR / red RECYCLE) with running statistics.", { }),
      why("Why ROS 2, and why one node per concern?", "ROS 2 is the de facto standard for robot software; splitting camera / inspection / decision / twin into separate nodes mirrors how a real cell is built — each part can be swapped, tested, or run on a different machine independently, and the typed messages document the interface. The nodes import the same Stage 1 model and Stage 2 grader, so no logic is duplicated."),
      P("Note: ROS 2 and Gazebo run on Linux. The project ships a Docker image (ROS 2 Humble desktop-full) for a headless end-to-end demo, and documents the native Ubuntu commands for the full RViz + Gazebo GUI.", { italics: true }),

      // ---- 6. Tools ----
      H1("6. Tools & methods — and why they were chosen"),
      table([2200, 3000, 4160], [
        ["Tool / method", "Used for", "Why chosen"],
        ["Python", "Whole project", "Standard for ML + robotics; one language across all stages."],
        ["PyTorch", "CV model + training", "Flexible, free; easy transfer learning and Grad-CAM via hooks."],
        ["ResNet-18 / MobileNetV3", "Backbone", "Small, pretrained, fast to fine-tune; MobileNet for edge."],
        ["Grad-CAM", "Defect localization", "Needs only image-level labels, near-zero extra cost, gives location + area."],
        ["OpenCV", "Image I/O, overlays, synthetic data", "Fast, ubiquitous, no licensing cost."],
        ["scikit-learn", "Metrics, confusion matrix", "Standard, reliable evaluation utilities."],
        ["Streamlit", "Dashboard", "Turns a Python script into an interactive web UI with minimal code."],
        ["JSON-Lines + pandas", "Digital-twin store", "Zero-setup, human-readable, append-only, easy analytics."],
        ["ROS 2 Humble", "Node graph", "Industry-standard robot middleware; clean separation; typed messages."],
        ["Gazebo", "Inspection-cell sim", "Standard ROS-integrated simulator for a fixed-camera scene."],
        ["RViz", "Visualization", "Native ROS 2 viewer for the image stream and decision markers."],
        ["Docker", "Reproducible ROS env", "Runs the Linux-only ROS/Gazebo stack on any host."],
      ]),

      // ---- 7. Results summary ----
      H1("7. Results summary"),
      table([1500, 3560, 4300], [
        ["Stage", "What it produces", "Demo result"],
        ["1 — Vision", "Class + Grad-CAM mask + confidence + area%", "~0.88 test accuracy on synthetic data; heatmaps land on the real defect."],
        ["2 — Decision", "Condition score → decision + digital-twin record", "Clean→REUSE, scratch→REPAIR, crack→RECYCLE; running recovery-rate statistic."],
        ["3 — Robotics", "4-node ROS 2 graph + Gazebo cell + RViz markers", "Decisions stream through the graph; colored markers + stats in RViz."],
      ]),

      // ---- 8. Limitations ----
      H1("8. Limitations & future work"),
      bullet("Synthetic data is a smoke test — headline accuracy should be reported on a real dataset (NEU-DET / casting), which the pipeline already supports."),
      bullet("Grad-CAM is coarse — if pixel masks become available, the vision stage can be upgraded to true segmentation without changing the downstream contract."),
      bullet("Grading is rule-based — a deliberate, explainable choice; a learned grader could be added and compared once labelled data exists."),
      bullet("Stage 3 runtime is Linux-only and was verified structurally (build/launch validity) rather than on hardware."),

      // ---- 9. Reproduce ----
      H1("9. How to reproduce"),
      P("Stage 1: python -m stage1_vision.dataset --make-synthetic; python -m stage1_vision.train --data data/synthetic --epochs 5; python -m stage1_vision.inference --weights outputs/best_model.pt --images data/synthetic/test --out outputs/predictions"),
      P("Stage 2: python -m stage2_decision.pipeline --weights outputs/best_model.pt --images data/synthetic/test --reset-twin; streamlit run stage2_decision/dashboard.py"),
      P("Stage 3: docker build -f stage3_ros2/Dockerfile.ros2 -t defect-twin-ros2 . ; docker run --rm -it defect-twin-ros2"),
      P("Source: github.com/iamashkan/defect-inspection-digital-twin", { color: "3B6FD4" }),

      // ---- 10. Conclusion ----
      H1("10. Conclusion"),
      P("This project delivers a complete, reproducible demonstration that vision + ML can automate the reuse/repair/recycle triage at the heart of circular manufacturing. It is deliberately layered — a fast, explainable vision stage; a transparent decision and digital-twin stage; and a standard robotics-integration stage — using only free, open tools. Each design choice favoured being lightweight, explainable, and reproducible over raw model complexity, which is the right trade-off for an inspection system that must be trusted and audited."),
    ],
  }],
});

Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(__dirname + "/thesis.docx", buf);
  console.log("wrote thesis.docx (" + Math.round(buf.length / 1024) + " KB)");
});
