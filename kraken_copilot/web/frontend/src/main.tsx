import React from 'react';
import ReactDOM from 'react-dom/client';
import { CopilotKit } from '@copilotkit/react-core/v2';
import App from './App';
import { ErrorBoundary } from './components/ErrorBoundary';
import './index.css';

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <ErrorBoundary>
      <CopilotKit runtimeUrl="/api/copilotkit">
        <App />
      </CopilotKit>
    </ErrorBoundary>
  </React.StrictMode>
);
