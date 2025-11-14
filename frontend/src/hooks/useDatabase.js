// ============================================
// FILE: frontend/src/hooks/useDatabase.js
// ============================================
/**
 * React hook for database operations
 */

import { useState, useEffect } from 'react';
import { databaseService } from '../services/database';

export const useDatabase = () => {
  const [isInitialized, setIsInitialized] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const initDB = async () => {
      try {
        setIsLoading(true);
        setProgress(0);

        // Simulate progress (actual progress tracking is complex with fetch)
        const progressInterval = setInterval(() => {
          setProgress(prev => {
            if (prev >= 90) {
              clearInterval(progressInterval);
              return 90;
            }
            return prev + 10;
          });
        }, 300);

        await databaseService.initialize();

        clearInterval(progressInterval);
        setProgress(100);
        setIsInitialized(true);
        setError(null);

      } catch (err) {
        setError(err.message);
        console.error('Database initialization error:', err);
      } finally {
        setIsLoading(false);
      }
    };

    initDB();
  }, []);

  return {
    isInitialized,
    isLoading,
    error,
    progress,
    db: databaseService
  };
};

