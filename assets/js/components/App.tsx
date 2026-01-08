// App.tsx
import React from 'react';
import { Routes, Route } from 'react-router-dom';
import { Navbar } from './Navbar';
import { Footer } from './Footer';
import PageLayout from './PageLayout/index';

/*
import Home from './pages/Home';
import Login from './pages/Login';

    // nested under Navbar is:
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/login" element={<Login />} />
      </Routes>

*/

export default function App() {
  return (
    <>
      <Navbar />
      <PageLayout />
      <Footer />
    </>
  );
}
