// Build presentation.pptx — meeting deck for the Defect Inspection Digital Twin.
const path = require("path");
const PptxGenJS = require("pptxgenjs");

const A = (f) => path.join(__dirname, "assets", f);

// ---- palette (circular-manufacturing / sustainability) ----
const INK = "16241D";       // dark green-black (dark slide bg)
const FOREST = "2C5F2D";    // primary
const MOSS = "6FA56B";      // supporting
const PAPER = "FFFFFF";     // content bg
const TEXT = "1B2A24";
const MUTED = "5B6472";
const GREEN = "2ECC71", AMBER = "F1C40F", RED = "E74C3C";
const HFONT = "Georgia", BFONT = "Arial";

const pptx = new PptxGenJS();
pptx.defineLayout({ name: "W", width: 13.33, height: 7.5 });
pptx.layout = "W";
pptx.theme = { headFontFace: HFONT, bodyFontFace: BFONT };
const W = 13.33, H = 7.5, M = 0.6;

// ---- helpers ----
function titleOf(slide, text, opts = {}) {
  slide.addText(text, {
    x: M, y: 0.45, w: W - 2 * M, h: 0.9, fontFace: HFONT, fontSize: 30, bold: true,
    color: opts.color || FOREST, align: "left", ...opts,
  });
}
function kicker(slide, text, color = MOSS) {
  slide.addText(text.toUpperCase(), {
    x: M, y: 0.2, w: W - 2 * M, h: 0.3, fontFace: BFONT, fontSize: 11, bold: true,
    color, charSpacing: 2, align: "left",
  });
}
function pageNum(slide, n) {
  slide.addText(String(n), { x: W - 0.8, y: H - 0.5, w: 0.4, h: 0.3,
    fontSize: 10, color: MUTED, align: "right" });
}
function bullets(slide, items, o = {}) {
  slide.addText(
    items.map((t) => ({ text: t, options: { bullet: { code: "2022", indent: 14 }, breakLine: true } })),
    { x: o.x ?? M, y: o.y ?? 1.7, w: o.w ?? 5.6, h: o.h ?? 4.6, fontFace: BFONT,
      fontSize: o.fontSize ?? 15, color: TEXT, lineSpacingMultiple: 1.25, valign: "top", paraSpaceAfter: 8 });
}
function pill(slide, text, x, y, fill, w = 1.7) {
  slide.addText(text, { x, y, w, h: 0.5, align: "center", valign: "middle",
    fontFace: BFONT, fontSize: 13, bold: true, color: text === "RECYCLE" ? "FFFFFF" : "13202B",
    fill: { color: fill }, rectRadius: 0.1, shape: pptx.ShapeType.roundRect });
}

// ============ Slide 1 — Title (dark) ============
let s = pptx.addSlide();
s.background = { color: INK };
s.addText("Defect Inspection Digital Twin", {
  x: M, y: 2.5, w: W - 2 * M, h: 1.1, fontFace: HFONT, fontSize: 44, bold: true, color: "FFFFFF" });
s.addText("Computer vision + ML for reuse / repair / recycle decisions in circular manufacturing",
  { x: M, y: 3.7, w: W - 2 * M, h: 0.7, fontFace: BFONT, fontSize: 18, color: "C7D8C2" });
// decision pills as a visual motif
pill(s, "REUSE", M, 4.9, GREEN); pill(s, "REPAIR", M + 1.9, 4.9, AMBER); pill(s, "RECYCLE", M + 3.8, 4.9, RED);
s.addText("Ashkan Aghamoali  ·  Project walkthrough  ·  2026",
  { x: M, y: 6.6, w: W - 2 * M, h: 0.4, fontFace: BFONT, fontSize: 13, color: "8FA98A" });
s.addNotes("Open with the problem. This is a simulation-only system that decides what to do with a recovered part: reuse, repair, or recycle.");

// ============ Slide 2 — The problem ============
s = pptx.addSlide(); s.background = { color: PAPER };
kicker(s, "The problem"); titleOf(s, "What do we do with a recovered part?");
bullets(s, [
  "Circular manufacturing keeps parts and materials in service instead of scrapping them.",
  "The bottleneck is triage: every returned part must be inspected and routed.",
  "Done by hand it is slow, subjective and inconsistent.",
  "Goal: automate the decision — reuse, repair, or recycle — end to end, in simulation.",
], { y: 1.8, w: 7.0, fontSize: 17 });
// big stat callout card on the right
s.addShape(pptx.ShapeType.roundRect, { x: 8.2, y: 1.9, w: 4.3, h: 3.7, fill: { color: "F2F7F0" }, line: { color: MOSS, width: 1 }, rectRadius: 0.12 });
s.addText("3", { x: 8.2, y: 2.2, w: 4.3, h: 1.4, align: "center", fontFace: HFONT, fontSize: 96, bold: true, color: FOREST });
s.addText("recovery paths, one automated decision", { x: 8.4, y: 3.7, w: 3.9, h: 0.8, align: "center", fontFace: BFONT, fontSize: 15, color: TEXT });
pill(s, "REUSE", 8.45, 4.75, GREEN, 1.25); pill(s, "REPAIR", 9.8, 4.75, AMBER, 1.25); pill(s, "RECYCLE", 11.15, 4.75, RED, 1.25);
pageNum(s, 2);
s.addNotes("Land the three words early. A worn part comes in; the system decides what to do with it.");

// ============ Slide 3 — System overview ============
s = pptx.addSlide(); s.background = { color: PAPER };
kicker(s, "Big picture"); titleOf(s, "One pipeline, four parts, three build stages");
s.addImage({ path: A("architecture_pipeline.png"), x: 1.1, y: 1.9, w: 11.1, h: 3.36 });
s.addText("A part image flows left to right: the camera feeds an image, the CV model finds and localizes the defect, the grader turns that into a decision, and the digital twin records every part.",
  { x: 1.1, y: 5.6, w: 11.1, h: 0.9, fontFace: BFONT, fontSize: 14, color: MUTED, align: "center" });
pageNum(s, 3);
s.addNotes("Point at each box as you name it. Three layers = Stage 1 vision, Stage 2 decision, Stage 3 robotics.");

// ============ Slide 4 — Stage 1 vision ============
s = pptx.addSlide(); s.background = { color: PAPER };
kicker(s, "Stage 1 · Computer vision"); titleOf(s, "Seeing — and locating — the defect");
s.addImage({ path: A("stage1_overlay.png"), x: M, y: 1.7, w: 7.4, h: 2.47 });
s.addText("original  |  Grad-CAM heatmap  |  overlay", { x: M, y: 4.2, w: 7.4, h: 0.3, fontSize: 11, italic: true, color: MUTED, align: "center" });
bullets(s, [
  "Pretrained PyTorch ResNet, fine-tuned on surface-defect images.",
  "Per part: defect type, a confidence, and a heatmap of where the defect is.",
  "Grad-CAM gives the location from simple image labels — no pixel masks needed.",
  "Outputs a defect-area %, used by the next stage.",
], { x: 8.3, y: 1.8, w: 4.4, h: 4.0, fontSize: 15 });
pageNum(s, 4);
s.addNotes("Why not exact outlines? Grad-CAM needs only simple labels, much cheaper, and enough to locate the defect. ~88% accuracy on the demo set, trained in a minute.");

// ============ Slide 5 — Stage 1 results ============
s = pptx.addSlide(); s.background = { color: PAPER };
kicker(s, "Stage 1 · Results"); titleOf(s, "It separates the defect classes");
s.addImage({ path: A("stage1_confusion.png"), x: M, y: 1.8, w: 3.7, h: 3.7 });
// stat callouts
s.addShape(pptx.ShapeType.roundRect, { x: 5.0, y: 1.9, w: 3.6, h: 1.7, fill: { color: "F2F7F0" }, line: { color: MOSS, width: 1 }, rectRadius: 0.1 });
s.addText([{ text: "~88%\n", options: { fontSize: 48, bold: true, color: FOREST, fontFace: HFONT } },
           { text: "test accuracy (demo set)", options: { fontSize: 14, color: TEXT } }],
  { x: 5.0, y: 2.05, w: 3.6, h: 1.4, align: "center", valign: "middle" });
s.addShape(pptx.ShapeType.roundRect, { x: 8.9, y: 1.9, w: 3.6, h: 1.7, fill: { color: "F2F7F0" }, line: { color: MOSS, width: 1 }, rectRadius: 0.1 });
s.addText([{ text: "~1 min\n", options: { fontSize: 48, bold: true, color: FOREST, fontFace: HFONT } },
           { text: "to fine-tune on CPU", options: { fontSize: 14, color: TEXT } }],
  { x: 8.9, y: 2.05, w: 3.6, h: 1.4, align: "center", valign: "middle" });
bullets(s, [
  "Strong diagonal = clean separation between good / scratch / crack.",
  "Lightweight backbone + transfer learning → fast, reproducible runs.",
  "Same code trains on real datasets (NEU-DET, casting) for real numbers.",
], { x: 5.0, y: 3.9, w: 7.5, h: 1.8, fontSize: 15 });
pageNum(s, 5);
s.addNotes("The 88% is on a synthetic demo set that proves the pipeline. For headline numbers, train on NEU-DET or casting.");

// ============ Slide 6 — Stage 2 decision ============
s = pptx.addSlide(); s.background = { color: PAPER };
kicker(s, "Stage 2 · Decision"); titleOf(s, "From defect to recovery decision");
s.addImage({ path: A("stage2_grading_bands.png"), x: M, y: 1.7, w: 9.2, h: 2.19 });
bullets(s, [
  "A condition score (0–100) from defect type + how much surface it covers.",
  "Crack → low → RECYCLE.  Scratch → mid → REPAIR.  Clean → high → REUSE.",
  "A transparent rule, not a black box — so every decision can be explained and audited.",
  "Confidence drops near a threshold, where the call is genuinely less certain.",
], { y: 4.2, w: 12.0, h: 2.8, fontSize: 16 });
pageNum(s, 6);
s.addNotes("Stress the explainability: an unexplained RECYCLE is hard to trust. Thresholds are tunable.");

// ============ Slide 7 — Stage 2 twin + dashboard ============
s = pptx.addSlide(); s.background = { color: PAPER };
kicker(s, "Stage 2 · Digital twin"); titleOf(s, "A live record of every part");
s.addImage({ path: A("stage2_decision_dist.png"), x: M, y: 1.8, w: 4.7, h: 3.15 });
bullets(s, [
  "Every inspected part is appended to the digital twin: score, decision, timestamp.",
  "A Streamlit dashboard shows the part, the overlay, the decision badge, and live stats.",
  "Running ‘recovery rate’ = share of parts kept in service (reuse + repair).",
], { x: 5.7, y: 1.9, w: 7.0, h: 2.6, fontSize: 15 });
s.addShape(pptx.ShapeType.roundRect, { x: 5.7, y: 4.7, w: 6.9, h: 1.4, fill: { color: INK }, rectRadius: 0.1 });
s.addText([{ text: "54%  ", options: { fontSize: 30, bold: true, color: GREEN, fontFace: HFONT } },
           { text: "recovery rate over 24 demo parts", options: { fontSize: 16, color: "E6EFE4" } }],
  { x: 5.9, y: 4.7, w: 6.5, h: 1.4, valign: "middle" });
pageNum(s, 7);
s.addNotes("If live, open the dashboard and pick a sample to show the badge update.");

// ============ Slide 8 — Stage 3 ROS 2 ============
s = pptx.addSlide(); s.background = { color: PAPER };
kicker(s, "Stage 3 · Robotics"); titleOf(s, "Wrapped in a ROS 2 node graph");
const nodes = [["Camera", MOSS], ["Inspection\nCV + ML", FOREST], ["Decision\ngrading", "C28A2B"], ["Digital Twin\nrecord", GREEN]];
let nx = M;
nodes.forEach(([label, c], i) => {
  s.addShape(pptx.ShapeType.roundRect, { x: nx, y: 1.9, w: 2.6, h: 1.3, fill: { color: c }, rectRadius: 0.1 });
  s.addText(label, { x: nx, y: 1.9, w: 2.6, h: 1.3, align: "center", valign: "middle", color: "FFFFFF", bold: true, fontSize: 15 });
  if (i < 3) s.addText("→", { x: nx + 2.55, y: 1.9, w: 0.55, h: 1.3, align: "center", valign: "middle", fontSize: 22, color: MUTED });
  nx += 3.15;
});
bullets(s, [
  "Each job is its own node, passing typed messages down the line.",
  "A minimal Gazebo scene (table + fixed camera) and RViz markers — green / amber / red.",
  "Nodes reuse the exact Stage 1 model and Stage 2 grader — no duplicated logic.",
  "Runs on Linux; shipped as a Docker image for a headless end-to-end demo.",
], { y: 3.7, w: 12.0, h: 3.2, fontSize: 16 });
pageNum(s, 8);
s.addNotes("Be honest: ROS/Gazebo run on Linux, packaged in Docker. Verified structurally; runs end-to-end in the container.");

// ============ Slide 9 — Tools & why ============
s = pptx.addSlide(); s.background = { color: PAPER };
kicker(s, "Choices"); titleOf(s, "Tools — and why");
const tools = [
  ["PyTorch + ResNet", "Pretrained → fast, lightweight fine-tuning"],
  ["Grad-CAM", "Localizes defects without costly pixel labels"],
  ["Rule-based grading", "Explainable, auditable, tunable"],
  ["Streamlit", "Interactive dashboard from a Python script"],
  ["ROS 2 + Gazebo", "Industry standard; swappable, isolated nodes"],
  ["All free / open", "Reproducible, no paid services anywhere"],
];
let gx = M, gy = 1.9;
tools.forEach((t, i) => {
  const col = i % 2, row = Math.floor(i / 2);
  const x = M + col * 6.2, y = 1.9 + row * 1.55;
  s.addShape(pptx.ShapeType.roundRect, { x, y, w: 5.85, h: 1.35, fill: { color: "F2F7F0" }, line: { color: "DCE7D8", width: 1 }, rectRadius: 0.08 });
  s.addText([{ text: t[0] + "\n", options: { fontSize: 17, bold: true, color: FOREST, fontFace: HFONT } },
             { text: t[1], options: { fontSize: 13, color: TEXT } }],
    { x: x + 0.25, y, w: 5.5, h: 1.35, valign: "middle" });
});
pageNum(s, 9);
s.addNotes("Every tool chosen to be lightweight, free, explainable, reproducible.");

// ============ Slide 10 — Closing (dark) ============
s = pptx.addSlide(); s.background = { color: INK };
s.addText("A complete, runnable demo", { x: M, y: 2.2, w: W - 2 * M, h: 0.9, fontFace: HFONT, fontSize: 40, bold: true, color: "FFFFFF" });
s.addText("Vision + ML automating the reuse / repair / recycle decision for circular manufacturing — three independent layers, fully reproducible, all open source.",
  { x: M, y: 3.3, w: W - 2 * M, h: 1.2, fontFace: BFONT, fontSize: 18, color: "C7D8C2" });
s.addText("github.com/iamashkan/defect-inspection-digital-twin",
  { x: M, y: 5.0, w: W - 2 * M, h: 0.5, fontFace: BFONT, fontSize: 15, color: MOSS });
pill(s, "REUSE", M, 5.8, GREEN); pill(s, "REPAIR", M + 1.9, 5.8, AMBER); pill(s, "RECYCLE", M + 3.8, 5.8, RED);
s.addNotes("Close: complete, reproducible, open source. Offer to dive into any stage.");

pptx.writeFile({ fileName: path.join(__dirname, "presentation.pptx") })
  .then((f) => console.log("wrote", f));
