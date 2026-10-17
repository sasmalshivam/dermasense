import { jsPDF } from "jspdf";

/**
 * Generates and downloads a clinical-grade PDF assessment summary directly in the browser.
 * Adheres strictly to non-diagnostic terminology and embeds the mandatory clinical disclaimer.
 *
 * @param {Object} result - Prediction response object from /api/predict
 * @param {string} userRegion - Optional coarse region string (e.g., "Khurda, Odisha")
 */
export function generateClinicalPDF(result, userRegion = "India") {
  const doc = new jsPDF({
    orientation: "portrait",
    unit: "mm",
    format: "a4",
  });

  const pageWidth = doc.internal.pageSize.getWidth();
  const pageHeight = doc.internal.pageSize.getHeight();
  const margin = 16;
  const contentWidth = pageWidth - margin * 2;
  let y = 18;

  // Helper for adding lines and advancing y
  const checkPageBreak = (neededHeight) => {
    if (y + neededHeight > pageHeight - 20) {
      doc.addPage();
      y = 18;
      // Header on subsequent pages
      doc.setFont("helvetica", "italic");
      doc.setFontSize(8);
      doc.setTextColor(120, 120, 120);
      doc.text("DermaSense Assessment Summary — SIH 2025 (PS 25049)", margin, 12);
      doc.line(margin, 14, pageWidth - margin, 14);
      y = 20;
    }
  };

  // Header Banner
  doc.setFillColor(15, 23, 42); // slate-900
  doc.rect(margin, y, contentWidth, 24, "F");

  doc.setFont("helvetica", "bold");
  doc.setFontSize(16);
  doc.setTextColor(255, 255, 255);
  doc.text("DermaSense — Skin Health Assessment Summary", margin + 6, y + 10);

  doc.setFont("helvetica", "normal");
  doc.setFontSize(9);
  doc.setTextColor(148, 163, 184); // slate-400
  doc.text(
    "Smart India Hackathon 2025 | Team Healthnautix (PS 25049) | Public Health Awareness",
    margin + 6,
    y + 18
  );

  y += 30;

  // Meta Box (Date, Coarse Region, Review Status)
  doc.setFillColor(248, 250, 252); // slate-50
  doc.setDrawColor(226, 232, 240); // slate-200
  doc.rect(margin, y, contentWidth, 18, "FD");

  doc.setFontSize(8.5);
  doc.setTextColor(51, 65, 85);

  const dateStr = new Date().toLocaleString("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
  });

  doc.text(`Report Date: ${dateStr}`, margin + 4, y + 6);
  doc.text(`Region: ${userRegion || "India"}`, margin + 4, y + 12);
  doc.text("Assessment Type: Non-Diagnostic Visual AI", margin + 80, y + 6);

  doc.setFont("helvetica", "bold");
  doc.setTextColor(185, 28, 28); // red-700
  doc.text("reviewed_by_clinician: false (Pending Clinical Examination)", margin + 80, y + 12);

  y += 24;

  // Primary Assessment Section
  doc.setFont("helvetica", "bold");
  doc.setFontSize(12);
  doc.setTextColor(15, 23, 42);
  doc.text("1. Primary Possible Condition", margin, y);
  y += 6;

  const topName = result.top_condition_name || "Unknown";
  const topProb = result.confidence_score
    ? `${(result.confidence_score * 100).toFixed(1)}%`
    : result.top_conditions?.[0]?.percentage || "N/A";
  const severity = (result.severity_level || "medium").toUpperCase();

  doc.setFillColor(241, 245, 249);
  doc.rect(margin, y, contentWidth, 16, "F");

  doc.setFont("helvetica", "bold");
  doc.setFontSize(11);
  doc.setTextColor(30, 41, 59);
  doc.text(`${topName} — Statistical Probability: ${topProb}`, margin + 4, y + 7);

  doc.setFontSize(9);
  doc.setFont("helvetica", "normal");
  const sevColor = severity === "HIGH" ? [220, 38, 38] : severity === "LOW" ? [22, 101, 52] : [202, 138, 4];
  doc.setTextColor(...sevColor);
  doc.text(`Severity Level: ${severity}`, margin + 4, y + 12);

  y += 22;

  // Urgent Notice if High Severity
  if (result.doctor_notice || severity === "HIGH") {
    checkPageBreak(18);
    doc.setFillColor(254, 242, 242); // red-50
    doc.setDrawColor(239, 68, 68); // red-500
    doc.rect(margin, y, contentWidth, 14, "FD");

    doc.setFont("helvetica", "bold");
    doc.setFontSize(8.5);
    doc.setTextColor(185, 28, 28);
    doc.text("ATTENTION: HIGH PRIORITY CLINICAL CONSULTATION RECOMMENDED", margin + 4, y + 5);

    doc.setFont("helvetica", "normal");
    doc.setFontSize(8);
    const noticeText = doc.splitTextToSize(
      result.doctor_notice ||
        "Visual features correspond to a high-priority lesion. Please schedule a clinical examination promptly.",
      contentWidth - 8
    );
    doc.text(noticeText, margin + 4, y + 10);
    y += 18;
  }

  // Top Differential Possibilities
  if (result.top_conditions && result.top_conditions.length > 1) {
    checkPageBreak(16);
    doc.setFont("helvetica", "bold");
    doc.setFontSize(10);
    doc.setTextColor(71, 85, 105);
    doc.text("Differential Ranked Possibilities:", margin, y);
    y += 5;

    doc.setFont("helvetica", "normal");
    doc.setFontSize(8.5);
    doc.setTextColor(100, 116, 139);
    result.top_conditions.slice(1, 3).forEach((cond) => {
      doc.text(`• ${cond.name} (${cond.percentage})`, margin + 4, y);
      y += 4.5;
    });
    y += 4;
  }

  // Clinical Guidance from Knowledge Base
  const kb = result.knowledge_base;
  if (kb) {
    const addSection = (title, itemsOrText, isWarning = false) => {
      if (!itemsOrText || (Array.isArray(itemsOrText) && itemsOrText.length === 0)) return;

      checkPageBreak(24);
      doc.setFont("helvetica", "bold");
      doc.setFontSize(10);
      doc.setTextColor(isWarning ? 185 : 30, isWarning ? 28 : 41, isWarning ? 28 : 59);
      doc.text(title, margin, y);
      y += 5;

      doc.setFont("helvetica", "normal");
      doc.setFontSize(8.5);
      doc.setTextColor(51, 65, 85);

      if (Array.isArray(itemsOrText)) {
        itemsOrText.forEach((item) => {
          const lines = doc.splitTextToSize(`• ${item}`, contentWidth - 4);
          checkPageBreak(lines.length * 4.5);
          doc.text(lines, margin + 2, y);
          y += lines.length * 4.5;
        });
      } else {
        const lines = doc.splitTextToSize(itemsOrText, contentWidth - 4);
        checkPageBreak(lines.length * 4.5);
        doc.text(lines, margin + 2, y);
        y += lines.length * 4.5;
      }
      y += 3;
    };

    addSection("2. Description & Overview", kb.description);
    addSection("3. Immediate First Aid & Initial Care", kb.first_aid);
    addSection("4. What Strictly NOT to Do (Harmful Practices)", kb.do_not, true);
    addSection("5. When to Consult a Medical Practitioner", kb.when_to_see_doctor);
    addSection("6. Red Flags & Critical Warnings", kb.red_flags, true);

    // Sources Cited
    if (kb.sources && kb.sources.length > 0) {
      checkPageBreak(20);
      doc.setFont("helvetica", "bold");
      doc.setFontSize(9);
      doc.setTextColor(71, 85, 105);
      doc.text("7. Authoritative Clinical References Cited:", margin, y);
      y += 4.5;

      doc.setFont("helvetica", "normal");
      doc.setFontSize(7.5);
      doc.setTextColor(37, 99, 235); // blue-600
      kb.sources.forEach((src) => {
        checkPageBreak(5);
        doc.text(`[${src.title}]: ${src.url}`, margin + 2, y);
        y += 4;
      });
      y += 4;
    }
  }

  // Mandatory Legal & Clinical Disclaimer Box
  checkPageBreak(35);
  doc.setDrawColor(180, 83, 9); // amber-700
  doc.setFillColor(254, 252, 232); // amber-50
  doc.rect(margin, y, contentWidth, 24, "FD");

  doc.setFont("helvetica", "bold");
  doc.setFontSize(8);
  doc.setTextColor(180, 83, 9);
  doc.text("NON-NEGOTIABLE CLINICAL & ETHICAL DISCLAIMER", margin + 4, y + 5);

  doc.setFont("helvetica", "normal");
  doc.setFontSize(7.5);
  doc.setTextColor(120, 53, 15);
  const disclaimerLines = doc.splitTextToSize(
    result.disclaimer ||
      "DISCLAIMER: DermaSense is an educational and skin health awareness tool developed for the Smart India Hackathon 2025. It does NOT provide a clinical diagnosis, prognosis, or formal medical advice. All predictions represent statistical 'possible conditions'. Always consult a qualified dermatologist. In case of emergency or rapid lesion progression, seek emergency medical care immediately.",
    contentWidth - 8
  );
  doc.text(disclaimerLines, margin + 4, y + 10);
  y += 28;

  // Doctor Consultation Verification Area
  checkPageBreak(20);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(8);
  doc.setTextColor(100, 116, 139);
  doc.text("Attending Physician / Dermatologist Sign-Off:", margin, y + 6);
  doc.line(margin + 75, y + 6, margin + 140, y + 6);
  doc.text("Clinical Date: ____/____/2026", margin + 145, y + 6);

  // Save the PDF
  const filename = `DermaSense_Assessment_${topName.replace(/[^a-zA-Z0-9]/g, "_")}_${new Date().toISOString().slice(0, 10)}.pdf`;
  doc.save(filename);
}

