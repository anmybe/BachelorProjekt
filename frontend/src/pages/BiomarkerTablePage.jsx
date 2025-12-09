import React, { useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { loadBiomarkers } from '../data/loadBiomarkers';
import backgroundImage from '../assets/background.png';

const BiomarkerTablePage = () => {
    const biomarkers = useMemo(() => loadBiomarkers(), []);
    const [searchTerm, setSearchTerm] = useState('');
    const [sortConfig, setSortConfig] = useState({ key: 'name', direction: 'asc' });

    const handleSort = (key) => {
        let direction = 'asc';
        if (sortConfig.key === key && sortConfig.direction === 'asc') {
            direction = 'desc';
        }
        setSortConfig({ key, direction });
    };

    const filteredBiomarkers = useMemo(() => {
        let sortedData = [...biomarkers];
        if (sortConfig.key) {
            sortedData.sort((a, b) => {
                if (a[sortConfig.key] < b[sortConfig.key]) {
                    return sortConfig.direction === 'asc' ? -1 : 1;
                }
                if (a[sortConfig.key] > b[sortConfig.key]) {
                    return sortConfig.direction === 'asc' ? 1 : -1;
                }
                return 0;
            });
        }
        return sortedData.filter(b =>
            b.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
            b.groups.toLowerCase().includes(searchTerm.toLowerCase())
        );
    }, [biomarkers, searchTerm, sortConfig]);

    return (
        <div>
            {/* Hero Section */}
            <div style={{
                height: '100vh',
                width: '100%',
                backgroundImage: `url(${backgroundImage})`,
                backgroundSize: 'cover',
                backgroundPosition: 'center',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'center',
                alignItems: 'center',
                textAlign: 'center',
                padding: '2rem',
                position: 'relative'
            }}>
                <div style={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    right: 0,
                    bottom: 0,
                    backgroundColor: 'rgba(0,0,0,0.1)' // Slight overlay for readability
                }}></div>
                <h1 style={{
                    fontSize: '4rem',
                    fontWeight: 800,
                    color: '#fff',
                    textShadow: '0 4px 12px rgba(0,0,0,0.2)',
                    zIndex: 1,
                    marginBottom: '1rem',
                    letterSpacing: '-0.02em',
                    maxWidth: '800px',
                    lineHeight: 1.1
                }}>
                    Biomarker Uncovered:<br />Rise of the Athlete
                </h1>
                <div style={{
                    position: 'absolute',
                    bottom: '3rem',
                    color: '#fff',
                    zIndex: 1,
                    animation: 'bounce 2s infinite',
                    fontSize: '2rem',
                    opacity: 0.8
                }}>
                    ↓
                </div>
            </div>

            {/* Main Content */}
            <div style={{ padding: '4rem 2rem', maxWidth: '1200px', margin: '0 auto', minHeight: '100vh' }}>
                <h2 style={{ marginBottom: '2rem', fontSize: '2.25rem', fontWeight: 800, letterSpacing: '-0.03em', color: 'var(--text-primary)' }}>Biomarker Summary</h2>
                <div style={{
                    overflowX: 'auto',
                    backgroundColor: 'rgba(255, 255, 255, 0.6)',
                    backdropFilter: 'blur(12px)',
                    borderRadius: 'var(--radius-lg)',
                    boxShadow: 'var(--shadow-md)',
                    border: '1px solid rgba(255, 255, 255, 0.6)'
                }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: '800px' }}>
                        <thead>
                            <tr style={{ borderBottom: '1px solid rgba(0,0,0,0.05)', backgroundColor: 'rgba(255,255,255,0.4)' }}>
                                <th style={{ padding: '1.25rem', textAlign: 'left', fontWeight: 700, color: 'var(--text-secondary)', fontSize: '0.875rem', textTransform: 'uppercase', letterSpacing: '0.05em', cursor: 'pointer' }} onClick={() => handleSort('name')}>Biomarker</th>
                                <th style={{ padding: '1.25rem', textAlign: 'left', fontWeight: 700, color: 'var(--text-secondary)', fontSize: '0.875rem', textTransform: 'uppercase', letterSpacing: '0.05em', cursor: 'pointer' }} onClick={() => handleSort('groups')}>Group</th>
                                <th style={{ padding: '1.25rem', textAlign: 'left', fontWeight: 700, color: 'var(--text-secondary)', fontSize: '0.875rem', textTransform: 'uppercase', letterSpacing: '0.05em', cursor: 'pointer' }} onClick={() => handleSort('relevance')}>Relevance</th>
                                <th style={{ padding: '1.25rem', textAlign: 'left', fontWeight: 700, color: 'var(--text-secondary)', fontSize: '0.875rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Summary</th>
                            </tr>
                        </thead>
                        <tbody>
                            {filteredBiomarkers.map((biomarker, index) => (
                                <tr key={index} style={{
                                    borderBottom: '1px solid rgba(0,0,0,0.03)',
                                    transition: 'background-color 0.2s',
                                    cursor: 'pointer'
                                }}
                                    onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.5)'}
                                    onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
                                >
                                    <td style={{ padding: '1.25rem' }}>
                                        <Link to={`/biomarker/${encodeURIComponent(biomarker.name)}`} style={{ fontWeight: 600, color: 'var(--primary-color)', textDecoration: 'none', fontSize: '1.05rem' }}>
                                            {biomarker.name}
                                        </Link>
                                    </td>
                                    <td style={{ padding: '1.25rem' }}>
                                        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                                            {biomarker.groups.split(',').map((g, i) => (
                                                <span key={i} style={{
                                                    fontSize: '0.75rem',
                                                    padding: '0.25rem 0.75rem',
                                                    backgroundColor: '#fdf4ff',
                                                    color: '#86198f',
                                                    borderRadius: '9999px',
                                                    border: '1px solid rgba(255,255,255,0.6)',
                                                    fontWeight: 600
                                                }}>
                                                    {g.trim().replace(/_/g, ' ')}
                                                </span>
                                            ))}
                                        </div>
                                    </td>
                                    <td style={{ padding: '1.25rem' }}>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                            <div style={{
                                                width: '100%',
                                                maxWidth: '80px',
                                                height: '6px',
                                                backgroundColor: 'rgba(0,0,0,0.1)',
                                                borderRadius: '9999px',
                                                overflow: 'hidden'
                                            }}>
                                                <div style={{
                                                    width: `${(biomarker.relevance / 10) * 100}%`,
                                                    height: '100%',
                                                    background: 'linear-gradient(90deg, #F8B9B4, #F6C8D9)',
                                                    borderRadius: '9999px'
                                                }}></div>
                                            </div>
                                            <span style={{ fontWeight: 600, color: 'var(--text-secondary)', fontSize: '0.9rem' }}>{biomarker.relevance}</span>
                                        </div>
                                    </td>
                                    <td style={{ padding: '1.25rem', color: 'var(--text-secondary)', fontSize: '0.95rem', lineHeight: 1.5 }}>
                                        {biomarker.effectSummary.slice(0, 100)}...
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
            <style>{`
                @keyframes bounce {
                    0%, 20%, 50%, 80%, 100% { transform: translateY(0); }
                    40% { transform: translateY(-10px); }
                    60% { transform: translateY(-5px); }
                }
            `}</style>
        </div>
    );
};

export default BiomarkerTablePage;
