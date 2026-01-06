import React from 'react';
import { useParams, Link } from 'react-router-dom';
import { getBiomarkerByName, getPapersForBiomarker } from '../data/loadBiomarkers';
import PaperCard from '../components/PaperCard';
import Section from '../components/Section';

const formatGroups = (groups) => {
    if (!groups) return '';
    return groups.split(',').map(g => {
        return g.trim().split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
    }).join(', ');
};

const BiomarkerPage = () => {
    const { name } = useParams();
    const decodedName = decodeURIComponent(name);
    const biomarker = getBiomarkerByName(decodedName);
    const papers = getPapersForBiomarker(decodedName);

    if (!biomarker) {
        return <div style={{ padding: '2rem' }}>Biomarker not found.</div>;
    }

    return (
        <div style={{ padding: '3rem 2rem', maxWidth: '1000px', margin: '0 auto' }}>
            <Link to="/" style={{ display: 'inline-flex', alignItems: 'center', marginBottom: '2rem', color: 'var(--text-secondary)', fontWeight: 600, fontSize: '0.9rem', padding: '0.5rem 1rem', backgroundColor: 'rgba(255,255,255,0.6)', borderRadius: '9999px', boxShadow: 'var(--shadow-sm)', backdropFilter: 'blur(4px)' }}>
                &larr; Back to Summary
            </Link>

            <div style={{ marginBottom: '4rem', textAlign: 'center' }}>
                <h1 style={{ marginBottom: '1rem', fontSize: '3.5rem', fontWeight: 800, letterSpacing: '-0.03em', color: 'var(--text-primary)' }}>{biomarker.name}</h1>
                <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', justifyContent: 'center', color: 'var(--text-secondary)' }}>
                    {biomarker.groups && biomarker.groups.split(',').map((g, idx) => (
                        <span key={idx} style={{
                            background: 'linear-gradient(135deg, #fdf4ff 0%, #fae8ff 100%)',
                            color: '#86198f',
                            padding: '0.5rem 1rem',
                            borderRadius: '9999px',
                            fontWeight: 700,
                            fontSize: '0.875rem',
                            textTransform: 'capitalize',
                            border: '1px solid rgba(255,255,255,0.6)',
                            boxShadow: '0 2px 4px rgba(0,0,0,0.03)'
                        }}>
                            {g.trim().replace(/_/g, ' ')}
                        </span>
                    ))}
                    <span style={{ fontWeight: 700, fontSize: '1.1rem', color: 'var(--text-primary)' }}>Relevance: <span style={{ color: '#be185d' }}>{biomarker.relevance}/10</span></span>
                </div>
            </div>

            <Section title="Detailed Analysis">
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '2rem' }}>
                    <div style={cardStyle}>
                        <h3 style={cardHeaderStyle}>Activity Context</h3>
                        <p style={cardBodyStyle}>{biomarker.activityContext}</p>
                    </div>
                    <div style={cardStyle}>
                        <h3 style={cardHeaderStyle}>Effect Summary</h3>
                        <p style={cardBodyStyle}>{biomarker.effectSummary}</p>
                    </div>
                    <div style={{ ...cardStyle, gridColumn: '1 / -1', background: 'linear-gradient(to right, rgba(255,255,255,0.8), rgba(249,250,251,0.8))' }}>
                        <h3 style={cardHeaderStyle}>Sport Implications</h3>
                        <p style={cardBodyStyle}>{biomarker.sportImplications}</p>
                    </div>
                </div>
            </Section>

            <Section title={`Referenced Papers (${papers.length})`}>
                {papers.length === 0 ? (
                    <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-secondary)', backgroundColor: 'rgba(255,255,255,0.4)', borderRadius: 'var(--radius-lg)', border: '1px dashed rgba(0,0,0,0.1)' }}>
                        No papers found in the dataset.
                    </div>
                ) : (
                    <div style={{ display: 'grid', gap: '1.5rem' }}>
                        {papers.map(paper => (
                            <PaperCard key={paper.id} paper={paper} />
                        ))}
                    </div>
                )}
            </Section>
        </div>
    );
};

const cardStyle = {
    backgroundColor: 'rgba(255, 255, 255, 0.7)',
    backdropFilter: 'blur(16px)',
    WebkitBackdropFilter: 'blur(16px)',
    padding: '2rem',
    borderRadius: 'var(--radius-xl)',
    border: '1px solid rgba(255, 255, 255, 0.8)',
    boxShadow: 'var(--shadow-md)',
    transition: 'transform 0.3s ease, box-shadow 0.3s ease'
};

const cardHeaderStyle = {
    fontSize: '1.25rem',
    marginBottom: '1rem',
    color: 'var(--primary-color)',
    fontWeight: 700
};

const cardBodyStyle = {
    color: 'var(--text-secondary)',
    lineHeight: 1.7,
    margin: 0,
    fontSize: '1.05rem'
};

export default BiomarkerPage;
