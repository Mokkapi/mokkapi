// src/components/PageLayout/MainContent.tsx
import React, { useEffect, useState } from 'react';


export interface MainContentProps {
  selectedId: string | number | null;
}

interface ItemDetails {
  id: string | number;
  title: string;
  description: string;
}

const MainContent: React.FC<MainContentProps> = ({ selectedId }) => {
  const [details, setDetails] = useState<ItemDetails | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (selectedId == null) {
      setDetails(null);
      return;
    }
    setLoading(true);
    // dummy fetch:
    Promise.resolve({ id: selectedId, title: `Title ${selectedId}`, description: `Desc ${selectedId}` })
      .then(d => setDetails(d))
      .finally(() => setLoading(false));
  }, [selectedId]);

  if (selectedId == null) return <main><p>Select an item…</p></main>;
  if (loading)         return <main><p>Loading…</p></main>;
  if (!details)        return <main><p>Item not found.</p></main>;

  return (
    <>
      <h2>{details.title}</h2>
      <p>{details.description}</p>
    </>
  );
};

export default MainContent;
