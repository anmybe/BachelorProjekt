import React from 'react';
import { Link } from 'react-router-dom';

const PaperCard = ({ paper }) => {
    return (
        <div style={{
            border: '1px solid rgba(255,255,255,0.6)',
            padding: '1.5rem',
            borderRadius: 'var(--radius-lg)',
            backgroundColor: 'rgba(255, 255, 255, 0.6)',
            backdropFilter: 'blur(12px)',
            boxShadow: 'var(--shadow-sm)',
            transition: 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)',
            cursor: 'pointer',
            position: 'relative',
            overflow: 'hidden'
        }}
            onMouseEnter={(e) => {
                e.currentTarget.style.transform = 'translateY(-4px)';
                e.currentTarget.style.boxShadow = '0 12px 24px -8px rgba(201, 180, 228, 0.4)';
                e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.9)';
                e.currentTarget.style.borderColor = 'rgba(201, 180, 228, 0.5)';
            }}
            onMouseLeave={(e) => {
                e.currentTarget.style.transform = 'translateY(0)';
                e.currentTarget.style.boxShadow = 'var(--shadow-sm)';
                e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.6)';
                e.currentTarget.style.borderColor = 'rgba(255,255,255,0.6)';
            }}
        >
            <Link to={`/paper/${paper.id}`} style={{ textDecoration: 'none', color: 'inherit', display: 'block' }}>
                <p style={{
                    margin: '0 0 1rem 0',
                    fontSize: '1rem',
                    lineHeight: '1.6',
                    color: 'var(--text-primary)',
                    display: '-webkit-box',
                    WebkitLineClamp: 3,
                    WebkitBoxOrient: 'vertical',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis'
                }}>
                    {paper.document_summary ? (paper.document_summary.length > 150 ? paper.document_summary.slice(0, 150) + '...' : paper.document_summary) : 'No summary available.'}
                </p>
                <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
                    <span style={{ fontWeight: 600, color: '#be185d', backgroundColor: '#fce7f3', padding: '0.1rem 0.6rem', borderRadius: '9999px', fontSize: '0.85rem' }}>{paper.year}</span>
                    <span style={{ color: 'var(--text-light)' }}>•</span>
                    <span style={{ fontFamily: 'monospace', backgroundColor: 'rgba(255,255,255,0.5)', padding: '2px 8px', borderRadius: '4px', color: 'var(--text-secondary)', border: '1px solid rgba(255,255,255,0.5)' }}>ID: {paper.id}</span>
                </div>
            </Link>
        </div>
    );
};

export default PaperCard;
