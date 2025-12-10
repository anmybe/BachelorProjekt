import Papa from 'papaparse';
import biomarkerCsvContent from '../biomarker_summary_step4.csv?raw';
import { loadPapers } from './loadPapers';

let cachedBiomarkers = null;

export const loadBiomarkers = () => {
    if (cachedBiomarkers) return cachedBiomarkers;

    const results = Papa.parse(biomarkerCsvContent, {
        header: true,
        skipEmptyLines: true,
        delimiter: ',', // Updated to comma for step4 CSV
    });

    cachedBiomarkers = results.data.map(row => {
        // Parse Document IDs which might be comma separated
        const docIds = row['Document IDs'] ? row['Document IDs'].split(',').map(s => s.trim()) : [];

        return {
            name: row['Biomarker'],
            activityContext: row['Activity Context Summary'],
            effectSummary: row['Effect Summary'],
            sportImplications: row['Sport Implications'],
            relevance: row['Relevance for Sports (1–10)'], // Updated to en-dash
            groups: row['Biomarker Groups'],
            occurrences: row['Occurrences in Dataset'],
            docIds
        };
    });

    return cachedBiomarkers;
};

export const getBiomarkerByName = (name) => {
    const biomarkers = loadBiomarkers();
    return biomarkers.find(b => b.name === name);
};

export const getPapersForBiomarker = (biomarkerName) => {
    // We can use the docIds from the CSV to find papers directly
    const biomarker = getBiomarkerByName(biomarkerName);
    if (!biomarker) return [];

    const papers = loadPapers();
    // Filter papers that are in the docIds list
    return papers.filter(p => biomarker.docIds.includes(p.id));
};
