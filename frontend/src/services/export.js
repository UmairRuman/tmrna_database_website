
// FILE: frontend/src/services/export.js
// ============================================
export const exportToCSV = (results, filename = 'tmrna_results.csv') => {
  if (!results || results.length === 0) {
    alert('No results to export');
    return;
  }

  const keys = Object.keys(results[0]);
  const header = keys.join(',');

  const rows = results.map(result => {
    return keys.map(key => {
      const value = result[key];
      if (typeof value === 'string' && (value.includes(',') || value.includes('"'))) {
        return `"${value.replace(/"/g, '""')}"`;
      }
      return value;
    }).join(',');
  });

  const csv = [header, ...rows].join('\n');

  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
};

export const exportToFASTA = (results, sequenceType = 'peptide', filename = 'tmrna_sequences.fasta') => {
  if (!results || results.length === 0) {
    alert('No results to export');
    return;
  }

  const fastaLines = [];

  results.forEach(result => {
    fastaLines.push(`>${result.identifier}`);
    
    if (sequenceType === 'peptide') {
      fastaLines.push(result.tag_peptide);
    } else if (sequenceType === 'codon') {
      fastaLines.push(result.codons.replace(/-/g, ''));
    } else if (sequenceType === 'tmrna') {
      fastaLines.push(result.tmrna_sequence);
    }
  });

  const fasta = fastaLines.join('\n');

  const blob = new Blob([fasta], { type: 'text/plain;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
};


