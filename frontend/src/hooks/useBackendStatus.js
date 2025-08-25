import { useState, useEffect } from 'react';

export const useBackendStatus = () => {
  const [isBackendOnline, setIsBackendOnline] = useState(true);

  useEffect(() => {
    const handleBackendStatusChange = (event) => {
      setIsBackendOnline(event.detail.isOnline);
    };

    // Listen for backend status changes
    window.addEventListener('backendStatusChange', handleBackendStatusChange);
    return () => {
      window.removeEventListener('backendStatusChange', handleBackendStatusChange);
    };
  }, []);

  return { isBackendOnline };
};