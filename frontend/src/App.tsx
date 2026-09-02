import React from 'react';
import { ThemeProvider } from './hooks/useTheme';
import { AppRoutes } from './app/routes';

export const App: React.FC = () => {
  return (
    <ThemeProvider>
      <AppRoutes />
    </ThemeProvider>
  );
};

export default App;