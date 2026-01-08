import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { getAppConfig } from "./config";

import App from './components/App';

const { apiPrefix } = getAppConfig();

const root = ReactDOM.createRoot(
  document.getElementById('react-root')!
);

root.render(
  <BrowserRouter basename={apiPrefix}>
    <App />
  </BrowserRouter>
);
