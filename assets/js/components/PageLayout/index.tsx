// src/components/PageLayout/index.tsx
import React, { useState, useCallback } from 'react';
import Sidebar from './Sidebar';
import MainContent from './MainContent';

export interface PageLayoutProps {
  /** any valid CSS width – e.g. '200px' or '20vw' */
  sidebarWidth?: string;
}

export default function PageLayout({ sidebarWidth = '250px' }: PageLayoutProps) {
  const [selectedId, setSelectedId] = useState<string|number|null>(null);
  const handleSelect = useCallback((id: string|number) => setSelectedId(id), []);

  return (
    <div className="flex h-screen">
      <aside
        className="flex-none overflow-y-auto bg-gray-100 border-r"
        style={{ width: sidebarWidth }}
      >
        <Sidebar selectedId={selectedId} onSelect={handleSelect} />
      </aside>

      <main className="flex-1 overflow-y-auto p-4">
        <MainContent selectedId={selectedId} />
      </main>
    </div>
  );
}
