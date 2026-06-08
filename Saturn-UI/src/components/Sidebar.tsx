import { Icon } from '@mdi/react';
import { mdiHome, mdiStar, mdiFileDocument, mdiCog } from '@mdi/js';

const navItems = [
  { label: 'Home', path: mdiHome },
  { label: 'Constellations', path: mdiStar },
  { label: 'Documents', path: mdiFileDocument },
  { label: 'Settings', path: mdiCog },
];

export function Sidebar() {
  return (
    <aside className="sidebar">
      <nav className="sidebar-nav" aria-label="Main navigation">
        {navItems.map(({ label, path }) => (
          <button key={label} type="button" className="sidebar-item" aria-label={label}>
            <Icon path={path} size={1} className="sidebar-icon" aria-hidden="true" />
            <span className="sidebar-tooltip">{label}</span>
          </button>
        ))}
      </nav>
    </aside>
  );
}
