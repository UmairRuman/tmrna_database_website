// ============================================
// FILE: frontend/src/hooks/useSearch.js
// ============================================
import { useState } from 'react';
import { databaseService } from '../services/database';
import { searchPeptide, searchCodon } from '../services/api';

export const useSearch = () => {
  const [isSearching, setIsSearching] = useState(false);
  const [results, setResults] = useState([]);
  const [error, setError] = useState(null);
  const [searchTime, setSearchTime] = useState(0);

  const searchKeyword = async (query) => {
    if (!query.trim()) {
      setResults([]);
      return;
    }

    setIsSearching(true);
    setError(null);
    const startTime = performance.now();

    try {
      const data = databaseService.searchKeyword(query);
      setResults(data.results);
      setSearchTime((performance.now() - startTime) / 1000);
    } catch (err) {
      setError(err.message);
      setResults([]);
    } finally {
      setIsSearching(false);
    }
  };

  const searchPeptideSimilarity = async (sequence, threshold) => {
    setIsSearching(true);
    setError(null);

    try {
      const data = await searchPeptide(sequence, threshold);
      setResults(data.results);
      setSearchTime(data.search_time);
    } catch (err) {
      setError(err.message);
      setResults([]);
    } finally {
      setIsSearching(false);
    }
  };

  const searchCodonSimilarity = async (sequence, threshold) => {
    setIsSearching(true);
    setError(null);

    try {
      const data = await searchCodon(sequence, threshold);
      setResults(data.results);
      setSearchTime(data.search_time);
    } catch (err) {
      setError(err.message);
      setResults([]);
    } finally {
      setIsSearching(false);
    }
  };

  const clearResults = () => {
    setResults([]);
    setError(null);
    setSearchTime(0);
  };

  return {
    isSearching,
    results,
    error,
    searchTime,
    searchKeyword,
    searchPeptideSimilarity,
    searchCodonSimilarity,
    clearResults
  };
};