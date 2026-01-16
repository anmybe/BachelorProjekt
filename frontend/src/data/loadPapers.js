import paperLinks from '../paper_id_links_correct_path.json';

export const loadPapers = () => {
    const modules = import.meta.glob('../paper_summary/*.json', { eager: true });

    return Object.entries(modules).map(([path, moduleData]) => {
        // Extract ID from filename: ../paper_summary/12345678_analysis.json -> 12345678
        const filename = path.split('/').pop();
        const idMatch = filename.match(/^(\d+)/);
        const id = idMatch ? idMatch[1] : filename;

        // Handle both array-wrapped and direct object JSON structures
        const rawData = moduleData.default || moduleData;
        const data = Array.isArray(rawData) ? rawData[0] : rawData;

        // Flatten extracted_data if present (some JSONs have this nested structure)
        const extractedData = data.extracted_data || {};
        const document_summary = extractedData.document_summary || data.document_summary;
        const treatment_details = extractedData.treatment_details || data.treatment_details;
        const analyzed_biomarkers = extractedData.analyzed_biomarkers || data.analyzed_biomarkers;

        // Get DOI from links
        const doi = paperLinks[id] || null;

        // Extract year from metadata if available
        const year = data.metadata?.year || data.Year || "Unknown";
        const title = data.metadata?.title || data.Title || document_summary?.slice(0, 80) + "..." || "Untitled";

        return {
            id,
            path,
            doi,
            year,
            title,
            ...data,
            document_summary,
            treatment_details,
            analyzed_biomarkers
        };
    });
};

export const getPaperById = (id) => {
    const papers = loadPapers();
    return papers.find(p => p.id === id);
};
