import React, { useState } from 'react';
import { Link } from 'react-router-dom';

const BiomarkerCard = ({ biomarker }) => {
    const [isOpen, setIsOpen] = useState(false);

    return (
        <div
            onClick={() => setIsOpen(!isOpen)}
            style={{
                border: '1px solid rgba(255,255,255,0.6)',
                borderRadius: 'var(--radius-lg)',
                overflow: 'hidden',
                backgroundColor: isOpen ? 'rgba(255, 255, 255, 0.9)' : 'rgba(255, 255, 255, 0.6)',
                backdropFilter: 'blur(12px)',
                boxShadow: isOpen ? '0 12px 24px -8px rgba(201, 180, 228, 0.4)' : 'var(--shadow-sm)',
                transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                cursor: 'pointer',
                display: 'flex',
                flexDirection: 'column',
                position: 'relative',
                minHeight: isOpen ? 'auto' : '160px'
            }}
        >
            <div style={{
                padding: '1.5rem',
                flex: 1,
                display: 'flex',
                flexDirection: 'column',
                justifyContent: isOpen ? 'flex-start' : 'center',
                alignItems: isOpen ? 'flex-start' : 'center',
                textAlign: isOpen ? 'left' : 'center',
                gap: '1rem'
            }}>
                <h3 style={{
                    margin: 0,
                    fontSize: '1.25rem',
                    fontWeight: 700,
                    color: 'var(--primary-color)',
                    width: '100%'
                }}>
                    {biomarker.biomarker_name}
                </h3>

                {!isOpen && (
                    <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                        Click to view details
                    </div>
                )}

                {isOpen && (
                    <div style={{ width: '100%', display: 'grid', gap: '1.25rem', marginTop: '0.5rem' }}>
                        <div>
                            <div style={labelStyle}>Effect</div>
                            <div style={valueStyle}>{biomarker.measured_effect?.direction_of_change} <span style={{ color: 'var(--text-light)', fontWeight: 400 }}>({biomarker.measured_effect?.quantification || 'No quantification'})</span></div>
                        </div>
                        <div>
                            <div style={labelStyle}>Context</div>
                            <div style={{ lineHeight: 1.6, color: 'var(--text-secondary)', fontSize: '0.95rem' }}>{biomarker.relevant_activity_context}</div>
                        </div>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                            <div>
                                <div style={labelStyle}>Type</div>
                                <div style={valueStyle}>{biomarker.activity_type}</div>
                            </div>
                            <div>
                                <div style={labelStyle}>Tissue</div>
                                <div style={valueStyle}>{biomarker.measured_tissue_or_fluid}</div>
                            </div>
                        </div>
                    </div>
                )}
            </div>

            <div style={{
                padding: '0.75rem 1.5rem',
                borderTop: '1px solid rgba(255,255,255,0.5)',
                backgroundColor: 'rgba(255,255,255,0.3)',
                display: 'flex',
                justifyContent: 'center'
            }}>
                <Link
                    to={`/biomarker/${encodeURIComponent(biomarker.biomarker_name)}`}
                    onClick={(e) => e.stopPropagation()}
                    style={{
                        fontSize: '0.85rem',
                        fontWeight: 600,
                        color: 'var(--text-secondary)',
                        textDecoration: 'none',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.25rem',
                        transition: 'color 0.2s'
                    }}
                    onMouseEnter={(e) => e.target.style.color = 'var(--primary-color)'}
                    onMouseLeave={(e) => e.target.style.color = 'var(--text-secondary)'}
                >
                    View Global Summary &rarr;
                </Link>
            </div>
        </div>
    );
};

const labelStyle = {
    fontSize: '0.75rem',
    color: 'var(--text-light)',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
    fontWeight: 700,
    marginBottom: '0.25rem'
};

const valueStyle = {
    fontSize: '1rem',
    color: 'var(--text-primary)',
    fontWeight: 500
};

export default BiomarkerCard;
