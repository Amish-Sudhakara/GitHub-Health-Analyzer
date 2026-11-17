import jsPDF from 'jspdf';
import autoTablePlugin, { applyPlugin } from 'jspdf-autotable';

try {
  applyPlugin(jsPDF);
} catch (e) {
  // Plugin already applied or running in modular environment
}

const renderAutoTable = (doc, options) => {
  if (typeof doc.autoTable === 'function') {
    doc.autoTable(options);
  } else if (typeof autoTablePlugin === 'function') {
    autoTablePlugin(doc, options);
  } else if (autoTablePlugin && typeof autoTablePlugin.default === 'function') {
    autoTablePlugin.default(doc, options);
  }
};

/**
 * Generate a clean, professional PDF analysis report using jsPDF and jspdf-autotable.
 * Matches the Slate & Sage design tone with clean typography, tables, and pagination.
 */
export function generateHealthReport(data) {
  if (!data) return;

  const doc = new jsPDF({
    orientation: 'portrait',
    unit: 'pt',
    format: 'a4',
  });

  const pageWidth = doc.internal.pageSize.getWidth();
  const pageHeight = doc.internal.pageSize.getHeight();
  const margin = 40;
  const contentWidth = pageWidth - margin * 2;

  // Colors
  const primaryColor = [32, 40, 37];     // #202825
  const secondaryColor = [100, 113, 106]; // #64716A
  const accentColor = [71, 115, 92];     // #47735C
  const accentBg = [237, 243, 238];      // #EDF3EE
  const borderColor = [226, 231, 225];   // #E2E7E1

  let y = margin + 10;

  // 1. Report Header Bar
  doc.setFillColor(...accentColor);
  doc.rect(margin, y, 6, 38, 'F');

  doc.setFont('helvetica', 'bold');
  doc.setFontSize(20);
  doc.setTextColor(...primaryColor);
  doc.text('GitHub Health Analysis', margin + 14, y + 18);

  doc.setFont('helvetica', 'normal');
  doc.setFontSize(10);
  doc.setTextColor(...secondaryColor);
  doc.text('A lightweight snapshot of public GitHub activity and project maintenance', margin + 14, y + 32);

  y += 50;

  // 2. Profile & Context Box
  doc.setFillColor(...accentBg);
  doc.roundedRect(margin, y, contentWidth, 54, 4, 4, 'F');
  doc.setDrawColor(...borderColor);
  doc.roundedRect(margin, y, contentWidth, 54, 4, 4, 'S');

  doc.setFont('helvetica', 'bold');
  doc.setFontSize(11);
  doc.setTextColor(...primaryColor);
  const nameLabel = data.profile.name ? `${data.profile.name} (@${data.username})` : `@${data.username}`;
  doc.text(nameLabel, margin + 14, y + 20);

  doc.setFont('helvetica', 'normal');
  doc.setFontSize(9);
  doc.setTextColor(...secondaryColor);
  const bio = data.profile.bio ? `Bio: ${data.profile.bio.substring(0, 80)}` : 'Public Profile Analysis';
  doc.text(bio, margin + 14, y + 34);

  const reportDate = `Generated: ${data.meta.analyzed_at_formatted}  |  Window: ${data.meta.window_start} to ${data.meta.window_end}`;
  doc.text(reportDate, margin + 14, y + 46);

  y += 68;

  // 3. Summary Statistics Grid
  const cardWidth = (contentWidth - 18) / 4;
  const cardHeight = 48;
  const metrics = [
    { label: 'CONTRIBUTIONS', val: String(data.metrics.total_contributions || 0), sub: 'Past 12 months' },
    { label: 'ACTIVE WEEKS', val: String(data.metrics.active_weeks || 0), sub: `of ${data.metrics.total_observed_weeks || 53} observed` },
    { label: 'PUBLIC REPOS', val: String(data.metrics.public_repos_count || 0), sub: `${data.metrics.eligible_repos_count || 0} eligible original` },
    { label: 'ACTIVITY RATING', val: data.metrics.activity_rating || 'Good', sub: 'Based on weekly activity' },
  ];

  metrics.forEach((m, i) => {
    const cx = margin + i * (cardWidth + 6);
    doc.setFillColor(255, 255, 255);
    doc.setDrawColor(...borderColor);
    doc.roundedRect(cx, y, cardWidth, cardHeight, 4, 4, 'FD');

    doc.setFont('helvetica', 'bold');
    doc.setFontSize(7.5);
    doc.setTextColor(...secondaryColor);
    doc.text(m.label, cx + 8, y + 14);

    doc.setFont('helvetica', 'bold');
    doc.setFontSize(13);
    doc.setTextColor(...primaryColor);
    doc.text(m.val, cx + 8, y + 30);

    doc.setFont('helvetica', 'normal');
    doc.setFontSize(7.5);
    doc.setTextColor(...secondaryColor);
    doc.text(m.sub, cx + 8, y + 42);
  });

  y += 62;

  // 4. Monthly Contributions Table (if available)
  if (data.contributions && data.contributions.monthly && data.contributions.monthly.length > 0) {
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(12);
    doc.setTextColor(...primaryColor);
    doc.text('Monthly Contribution Breakdown', margin, y);
    y += 8;

    const monthlyRows = data.contributions.monthly.map((m) => [m.month, String(m.contributions)]);

    // Group into 2 columns for compact table
    const half = Math.ceil(monthlyRows.length / 2);
    const colA = monthlyRows.slice(0, half);
    const colB = monthlyRows.slice(half);

    const mergedRows = [];
    for (let i = 0; i < half; i++) {
      const a = colA[i] || ['', ''];
      const b = colB[i] || ['', ''];
      mergedRows.push([a[0], a[1], b[0], b[1]]);
    }

    renderAutoTable(doc, {
      startY: y,
      head: [['Month', 'Contributions', 'Month', 'Contributions']],
      body: mergedRows,
      theme: 'grid',
      styles: {
        fontSize: 8.5,
        cellPadding: 4,
        textColor: primaryColor,
        lineColor: borderColor,
      },
      headStyles: {
        fillColor: accentBg,
        textColor: primaryColor,
        fontStyle: 'bold',
      },
      margin: { left: margin, right: margin },
    });

    const tableFinalY = doc.lastAutoTable ? doc.lastAutoTable.finalY : y + 60;
    y = tableFinalY + 16;
  }

  // 5. Repository Analysis Table
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(12);
  doc.setTextColor(...primaryColor);
  doc.text('Repository Maintenance & Documentation Analysis', margin, y);
  y += 8;

  const repoRows = (data.repositories || []).map((r) => {
    const readmeText = r.checks.readme_evaluated
      ? (r.checks.has_readme ? 'README: Yes' : 'README: No')
      : 'README: N/A';
    const recentText = r.checks.recent_push ? '<180d: Yes' : '<180d: No';
    const commitsText = r.checks.commits_evaluated
      ? (r.checks.commits_ge_10 ? '≥10 Commits: Yes' : '≥10 Commits: No')
      : 'Commits: N/A';
    const checks = `${readmeText} | ${recentText} | ${commitsText}`;

    const commitDisplay = r.commit_count_display || (r.commit_count != null ? String(r.commit_count) : 'N/A');

    return [
      r.name,
      r.language || 'Not specified',
      String(r.stargazers_count || 0),
      commitDisplay,
      r.pushed_at_formatted || 'Unknown',
      checks,
      r.rating,
    ];
  });

  if (repoRows.length > 0) {
    renderAutoTable(doc, {
      startY: y,
      head: [['Repository', 'Primary Lang', 'Stars', 'Commits', 'Last Push', 'Maintenance Signals', 'Rating']],
      body: repoRows,
      theme: 'striped',
      styles: {
        fontSize: 8,
        cellPadding: 5,
        textColor: primaryColor,
        lineColor: borderColor,
      },
      headStyles: {
        fillColor: accentColor,
        textColor: [255, 255, 255],
        fontStyle: 'bold',
      },
      columnStyles: {
        0: { cellWidth: 85, fontStyle: 'bold' },
        1: { cellWidth: 65 },
        2: { cellWidth: 30, halign: 'center' },
        3: { cellWidth: 40, halign: 'center' },
        4: { cellWidth: 55 },
        5: { cellWidth: 145 },
        6: { cellWidth: 60, fontStyle: 'bold' },
      },
      margin: { left: margin, right: margin },
    });
    const repoFinalY = doc.lastAutoTable ? doc.lastAutoTable.finalY : y + 80;
    y = repoFinalY + 18;
  } else {
    doc.setFont('helvetica', 'italic');
    doc.setFontSize(9);
    doc.setTextColor(...secondaryColor);
    doc.text('No eligible original public repositories found for evaluation.', margin, y + 10);
    y += 24;
  }

  // Check page overflow before Suggestions
  if (y > pageHeight - 120) {
    doc.addPage();
    y = margin + 10;
  }

  // 6. Improvement Suggestions
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(12);
  doc.setTextColor(...primaryColor);
  doc.text('Actionable Improvement Suggestions', margin, y);
  y += 14;

  const suggestions = data.suggestions || [];
  suggestions.forEach((tip, idx) => {
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(9);
    doc.setTextColor(...accentColor);
    doc.text(`${idx + 1}.`, margin + 6, y);

    doc.setFont('helvetica', 'normal');
    doc.setFontSize(9);
    doc.setTextColor(...primaryColor);
    const splitTip = doc.splitTextToSize(tip, contentWidth - 24);
    doc.text(splitTip, margin + 20, y);
    y += splitTip.length * 12 + 4;
  });

  y += 12;

  // Check page overflow before methodology footer
  if (y > pageHeight - 80) {
    doc.addPage();
    y = margin + 10;
  }

  // 7. Methodology & Limitations Notice
  doc.setDrawColor(...borderColor);
  doc.line(margin, y, pageWidth - margin, y);
  y += 12;

  doc.setFont('helvetica', 'bold');
  doc.setFontSize(8);
  doc.setTextColor(...secondaryColor);
  doc.text('Methodology & Limitations:', margin, y);

  doc.setFont('helvetica', 'normal');
  doc.setFontSize(7.5);
  doc.setTextColor(...secondaryColor);
  const disclaimer =
    'This evaluation is a lightweight snapshot based exclusively on public GitHub API signals (contributions, README presence, push recency, and commit history). It does not assess internal source code quality, architecture, or algorithmic proficiency. Private repositories and offline contributions are not evaluated.';
  const splitDisclaimer = doc.splitTextToSize(disclaimer, contentWidth);
  doc.text(splitDisclaimer, margin, y + 10);

  // 8. Footer Page Numbers on all pages
  const totalPages = doc.internal.getNumberOfPages();
  for (let i = 1; i <= totalPages; i++) {
    doc.setPage(i);
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(8);
    doc.setTextColor(...secondaryColor);
    doc.text(
      `GitHub Health Analyzer  |  Page ${i} of ${totalPages}`,
      pageWidth / 2,
      pageHeight - 20,
      { align: 'center' }
    );
  }

  // Download PDF file
  const filename = `github-health-${data.username}.pdf`;
  doc.save(filename);
}
