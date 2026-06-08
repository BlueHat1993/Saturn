import React from 'react';

export function Loader({ size = 18, label }: { size?: number; label?: string }) {
  return (
    <div className="loader" role="status" aria-live="polite">
      <div className="spinner" style={{ width: size, height: size }} />
      {label ? <span className="loader-label">{label}</span> : null}
    </div>
  );
}

export default Loader;
