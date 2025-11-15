// ============================================
// FILE: frontend/src/components/AutocompleteDropdown.jsx
// NEW FILE: Reusable autocomplete component
// ============================================

import React from 'react';
import { Search } from 'lucide-react';

export const AutocompleteDropdown = ({ 
  suggestions, 
  onSelect, 
  isDarkMode,
  query 
}) => {
  if (suggestions.length === 0) return null;

  const highlightMatch = (text, query) => {
    if (!query) return text;
    
    const parts = text.split(new RegExp(`(${query})`, 'gi'));
    return parts.map((part, i) => 
      part.toLowerCase() === query.toLowerCase() ? (
        <span key={i} className="font-bold text-blue-500">{part}</span>
      ) : (
        <span key={i}>{part}</span>
      )
    );
  };

  return (
    <div 
      className={`absolute z-50 w-full mt-2 ${
        isDarkMode ? 'bg-gray-700' : 'bg-white'
      } rounded-lg shadow-xl border ${
        isDarkMode ? 'border-gray-600' : 'border-gray-200'
      } max-h-96 overflow-y-auto`}
    >
      <div className={`px-3 py-2 text-xs ${
        isDarkMode ? 'text-gray-400 border-gray-600' : 'text-gray-500 border-gray-200'
      } border-b flex items-center gap-2`}>
        <Search className="w-3 h-3" />
        {suggestions.length} suggestion{suggestions.length !== 1 ? 's' : ''} found
      </div>
      
      {suggestions.map((suggestion, idx) => (
        <button
          key={idx}
          onClick={() => onSelect(suggestion.identifier)}
          className={`w-full px-4 py-3 text-left transition-colors ${
            isDarkMode 
              ? 'hover:bg-gray-600 text-gray-200' 
              : 'hover:bg-gray-50 text-gray-800'
          } ${idx === suggestions.length - 1 ? '' : 'border-b'} ${
            isDarkMode ? 'border-gray-600' : 'border-gray-100'
          }`}
        >
          <div className="flex flex-col gap-1">
            <div className={`text-sm font-mono ${
              isDarkMode ? 'text-blue-400' : 'text-blue-600'
            }`}>
              {highlightMatch(suggestion.identifier, query)}
            </div>
            {suggestion.organism && (
              <div className={`text-xs ${
                isDarkMode ? 'text-gray-400' : 'text-gray-600'
              }`}>
                {highlightMatch(suggestion.organism, query)}
              </div>
            )}
          </div>
        </button>
      ))}
    </div>
  );
};
