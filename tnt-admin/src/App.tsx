import React from 'react';
import { Toaster } from 'react-hot-toast';
import { AppRouter } from './router';

function App() {
  return (
    <>
      <AppRouter />
      <Toaster
        position="top-right"
        gutter={8}
        toastOptions={{
          duration: 3500,
          style: {
            background: '#ffffff',
            color: '#111827',
            border: '1px solid rgba(15,23,42,0.08)',
            borderRadius: '12px',
            fontSize: '13px',
            fontFamily: 'Inter, system-ui, sans-serif',
            padding: '10px 14px',
            boxShadow: '0 1px 2px rgba(0,0,0,0.04), 0 12px 24px rgba(0,0,0,0.05)',
          },
          success: {
            iconTheme: {
              primary: '#22C55E',
              secondary: '#ffffff',
            },
          },
          error: {
            iconTheme: {
              primary: '#EF4444',
              secondary: '#ffffff',
            },
          },
        }}
      />
    </>
  );
}

export default App;