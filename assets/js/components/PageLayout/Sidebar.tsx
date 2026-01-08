// src/components/PageLayout/Sidebar.tsx
import React from 'react';


export interface SidebarProps {
  selectedId: string | number | null;
  onSelect: (id: string | number) => void;
}

const Sidebar: React.FC<SidebarProps> = ({ selectedId, onSelect }) => {
  const items = [
      { id: 'item1', label: 'Item 1' },
      { id: 'item2', label: 'Item 2' },
      { id: 'item3', label: 'Item 3' },
  ];

  return (
    <>
      <ul>
        {items.map(item => (
          <li key={item.id}>
            <button
              type="button"
              className={item.id === selectedId ? 'active' : undefined}
              onClick={() => onSelect(item.id)}
            >
              {item.label}
            </button>
          </li>
        ))}
      </ul>
    </>
  );
};

export default Sidebar;
