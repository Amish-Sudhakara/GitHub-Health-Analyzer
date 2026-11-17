import React, { useState } from 'react';
import { generateHealthReport } from '../utils/pdfGenerator';

export default function PdfDownloadCard({ data }) {
  const [downloading, setDownloading] = useState(false);

  const handleDownload = () => {
    setDownloading(true);
    try {
      generateHealthReport(data);
    } catch (err) {
      console.error('PDF generation error:', err);
      alert('Failed to generate PDF. Please try again.');
    } finally {
      setDownloading(false);
    }
  };

  return (
    <section className="pdf-actions-card">
      <div>
        <h3 className="pdf-info-title">Download Analysis Report</h3>
        <p className="pdf-info-subtitle">
          Export a complete PDF summary including metrics, monthly contributions, repository evaluations, and improvement tips.
        </p>
      </div>

      <button
        type="button"
        className="btn-primary"
        onClick={handleDownload}
        disabled={downloading}
      >
        {downloading ? 'Generating PDF...' : 'Download Report (PDF)'}
      </button>
    </section>
  );
}
