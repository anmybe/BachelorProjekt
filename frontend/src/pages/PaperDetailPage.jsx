import React from 'react';
import { useParams, Link } from 'react-router-dom';
import { getPaperById } from '../data/loadPapers';
import BiomarkerCard from '../components/BiomarkerCard';
import Section from '../components/Section';

const PaperDetailPage = () => {
    const { id } = useParams();
    const paper = getPaperById(id);

    if (!paper) {
        return <div style={{ padding: '2rem' }}>Paper not found.</div>;
    }

    return (
        <div style={{ padding: '3rem 2rem', maxWidth: '1000px', margin: '0 auto' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
                <Link to="/" style={{ display: 'inline-flex', alignItems: 'center', color: 'var(--text-secondary)', fontWeight: 600, fontSize: '0.9rem', padding: '0.5rem 1rem', backgroundColor: 'rgba(255,255,255,0.6)', borderRadius: '9999px', boxShadow: 'var(--shadow-sm)', backdropFilter: 'blur(4px)' }}>
                    &larr; Back to Home
                </Link>
                <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', fontSize: '0.9rem' }}>
                    {paper.year && paper.year !== "Unknown" && (
                        <span style={{ fontWeight: 700, color: '#be185d', backgroundColor: '#fce7f3', padding: '0.35rem 1rem', borderRadius: '9999px', border: '1px solid rgba(255,255,255,0.6)' }}>{paper.year}</span>
                    )}
                    <span style={{ fontWeight: 700, color: '#be185d', backgroundColor: '#fce7f3', padding: '0.35rem 1rem', borderRadius: '9999px', border: '1px solid rgba(255,255,255,0.6)' }}>ID: {paper.id}</span>
                    {paper.doi && (
                        <a href={`https://doi.org/${paper.doi}`} target="_blank" rel="noopener noreferrer" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.25rem', color: 'var(--primary-color)', fontWeight: 600, transition: 'color 0.2s', padding: '0.35rem 1rem', backgroundColor: 'rgba(255,255,255,0.6)', borderRadius: '9999px', border: '1px solid rgba(255,255,255,0.6)' }}>
                            DOI ↗
                        </a>
                    )}
                </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '2rem', marginBottom: '3rem' }}>
                <Section title="Document Summary">
                    <div style={{ backgroundColor: 'rgba(255, 255, 255, 0.6)', backdropFilter: 'blur(12px)', padding: '2rem', borderRadius: 'var(--radius-lg)', boxShadow: 'var(--shadow-sm)', border: '1px solid rgba(255, 255, 255, 0.6)', height: '100%' }}>
                        <p style={{ lineHeight: '1.8', fontSize: '1.05rem', color: 'var(--text-primary)', margin: 0 }}>
                            {paper.document_summary}
                        </p>
                    </div>
                </Section>

                <Section title="Treatment Details">
                    <div style={{
                        border: '1px solid rgba(255, 255, 255, 0.6)',
                        padding: '2rem',
                        borderRadius: 'var(--radius-lg)',
                        backgroundColor: 'rgba(255, 255, 255, 0.6)',
                        backdropFilter: 'blur(12px)',
                        boxShadow: 'var(--shadow-sm)',
                        height: '100%'
                    }}>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                            <div>
                                <div style={labelStyle}>Therapy Type</div>
                                <div style={valueStyle}>{paper.treatment_details?.therapy_type || 'N/A'}</div>
                            </div>
                            <div>
                                <div style={labelStyle}>Dose Specificity</div>
                                <div style={valueStyle}>{paper.treatment_details?.dose_specificity || 'N/A'}</div>
                            </div>
                            {paper.treatment_details?.sensitivity_specificity && (
                                <div>
                                    <div style={labelStyle}>Sensitivity/Specificity</div>
                                    <div style={valueStyle}>{paper.treatment_details.sensitivity_specificity}</div>
                                </div>
                            )}
                        </div>
                    </div>
                </Section>
            </div>

            <Section title="Analyzed Biomarkers">
                {!paper.analyzed_biomarkers || paper.analyzed_biomarkers.length === 0 ? (
                    <p style={{ color: 'var(--text-secondary)', fontStyle: 'italic' }}>No biomarkers analyzed.</p>
                ) : (
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '1.5rem' }}>
                        {paper.analyzed_biomarkers.map((biomarker, index) => (
                            <BiomarkerCard key={index} biomarker={biomarker} />
                        ))}
                    </div>
                )}
            </Section>
        </div>
    );
};

const labelStyle = {
    fontSize: '0.875rem',
    color: 'var(--text-light)',
    marginBottom: '0.5rem',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
    fontWeight: 700
};

const valueStyle = {
    fontSize: '1.125rem',
    color: 'var(--text-primary)',
    fontWeight: 600
};

export default PaperDetailPage;
