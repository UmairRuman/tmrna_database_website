// ============================================
// FILE: frontend/src/services/api.js
// ============================================
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json'
  }
});

export const searchPeptide = async (sequence, threshold = 50) => {
  try {
    const response = await api.post('/api/search/peptide', {
      sequence,
      threshold
    });
    return response.data;
  } catch (error) {
    if (error.response) {
      throw new Error(error.response.data.error || 'Peptide search failed');
    } else if (error.request) {
      throw new Error('No response from server. Please check if the backend is running.');
    } else {
      throw new Error(error.message);
    }
  }
};

export const searchCodon = async (sequence, threshold = 50) => {
  try {
    const response = await api.post('/api/search/codon', {
      sequence,
      threshold
    });
    return response.data;
  } catch (error) {
    if (error.response) {
      throw new Error(error.response.data.error || 'Codon search failed');
    } else if (error.request) {
      throw new Error('No response from server. Please check if the backend is running.');
    } else {
      throw new Error(error.message);
    }
  }
};

export const getDatabaseInfo = async () => {
  try {
    const response = await api.get('/api/info');
    return response.data;
  } catch (error) {
    console.error('Failed to get database info:', error);
    return null;
  }
};

export const healthCheck = async () => {
  try {
    const response = await api.get('/api/health');
    return response.data;
  } catch (error) {
    return { status: 'unavailable' };
  }
};

