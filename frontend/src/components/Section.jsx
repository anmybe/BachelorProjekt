import React from 'react';

const Section = ({ title, children }) => {
    return (
        <div style={{ marginBottom: '2rem' }}>
            <h2 style={{ borderBottom: '2px solid #eee', paddingBottom: '0.5rem', marginBottom: '1rem' }}>
                {title}
            </h2>
            {children}
        </div>
    );
};

export default Section;
