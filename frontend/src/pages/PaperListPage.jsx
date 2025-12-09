import React from 'react';
import { loadPapers } from '../data/loadPapers';
import PaperCard from '../components/PaperCard';
import Section from '../components/Section';

const PaperListPage = () => {
    const papers = loadPapers();

    return (
        <div style={{ padding: '2rem', maxWidth: '800px', margin: '0 auto' }}>
            <Section title="Scientific Papers">
                {papers.length === 0 ? (
                    <p>No papers found.</p>
                ) : (
                    papers.map(paper => (
                        <PaperCard key={paper.id} paper={paper} />
                    ))
                )}
            </Section>
        </div>
    );
};

export default PaperListPage;
