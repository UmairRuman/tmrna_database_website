import React, { useState, useMemo, useEffect } from 'react';
import { Search, Dna, Sparkles, Database, Download, ArrowRight, Zap, Loader2, AlertCircle } from 'lucide-react';
import { useDatabase } from './hooks/useDatabase';
import { useSearch } from './hooks/useSearch';
import { exportToCSV } from './services/export';
import { AutocompleteDropdown } from './components/Autocomplete';

export default function App() {
  const [activeTab, setActiveTab] = useState('keyword');
  const [keywordQuery, setKeywordQuery] = useState('');
  const [autocompleteSuggestions, setAutocompleteSuggestions] = useState([]);
  const [peptideQuery, setPeptideQuery] = useState('');
  const [codonQuery, setCodonQuery] = useState('');
  const [peptideThreshold, setPeptideThreshold] = useState(50);
  const [codonThreshold, setCodonThreshold] = useState(50);
  const [showAutocomplete, setShowAutocomplete] = useState(false);
  const [isDarkMode, setIsDarkMode] = useState(true);

  // Database hook (for local keyword search)
  const { isInitialized, isLoading: dbLoading, error: dbError, progress, db } = useDatabase();

  // Search hook
  const {
    isSearching,
    results,
    error: searchError,
    searchTime,
    searchKeyword,
    searchPeptideSimilarity,
    searchCodonSimilarity,
    clearResults
  } = useSearch();

  // Real-time autocomplete with debouncing
  useEffect(() => {
  console.log('🔍 useEffect triggered', { 
    isInitialized, 
    keywordQuery, 
    queryLength: keywordQuery.length 
  });

  if (!isInitialized || !keywordQuery || keywordQuery.length < 3) {
    console.log('⏸️ Skipping autocomplete - conditions not met');
    setAutocompleteSuggestions([]);
    setShowAutocomplete(false);
    return;
  }

  // Debounce: wait 200ms after user stops typing
  const timeoutId = setTimeout(() => {
    try {
      console.log('🚀 Fetching suggestions for:', keywordQuery);
      const suggestions = db.getIdentifierSuggestions(keywordQuery, 10);
      console.log('✅ Got suggestions:', suggestions);
      setAutocompleteSuggestions(suggestions);
      setShowAutocomplete(suggestions.length > 0);
    } catch (error) {
      console.error('❌ Autocomplete error:', error);
      setAutocompleteSuggestions([]);
    }
  }, 200);

  return () => clearTimeout(timeoutId);
}, [keywordQuery, isInitialized, db]);

  const handleAutocompleteSelect = (identifier) => {
    setKeywordQuery(identifier);
    setShowAutocomplete(false);
    // Optionally auto-search
    setTimeout(() => handleSearch(), 100);
  };

  // Filter results by threshold (client-side filtering)
  const filteredResults = useMemo(() => {
    const threshold = activeTab === 'peptide' ? peptideThreshold : codonThreshold;
    return results.filter(r => !r.similarity || r.similarity >= threshold);
  }, [results, peptideThreshold, codonThreshold, activeTab]);

  // Clear results when switching tabs
  useEffect(() => {
    clearResults();
    setKeywordQuery('');
    setPeptideQuery('');
    setCodonQuery('');
    setShowAutocomplete(false);
    setAutocompleteSuggestions([]);
  }, [activeTab]);

  const handleSearch = async () => {
    try {
      if (activeTab === 'keyword') {
        await searchKeyword(keywordQuery);
      } else if (activeTab === 'peptide') {
        await searchPeptideSimilarity(peptideQuery, peptideThreshold);
      } else if (activeTab === 'codon') {
        await searchCodonSimilarity(codonQuery, codonThreshold);
      }
      setShowAutocomplete(false);
    } catch (error) {
      console.error('Search error:', error);
    }
  };

  const handleExport = () => {
    exportToCSV(filteredResults, `tmrna_results_${Date.now()}.csv`);
  };

  const getSimilarityColor = (similarity) => {
    if (similarity >= 95) return 'text-green-400';
    if (similarity >= 85) return 'text-blue-400';
    if (similarity >= 75) return 'text-yellow-400';
    return 'text-orange-400';
  };

  const getThresholdLabel = (value) => {
    if (value >= 90) return 'Very Strict';
    if (value >= 75) return 'Strict';
    if (value >= 60) return 'Medium';
    return 'Loose';
  };

  // Database loading screen
  if (dbLoading) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 mx-auto mb-4 relative">
            <Loader2 className="w-16 h-16 text-blue-500 animate-spin" />
            <Database className="w-8 h-8 text-white absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2" />
          </div>
          <h2 className="text-2xl font-bold text-white mb-2">Loading Database...</h2>
          <p className="text-gray-400 mb-4">Downloading tmRNA database (~54 MB)</p>
          <div className="w-64 mx-auto bg-gray-800 rounded-full h-2 overflow-hidden">
            <div 
              className="bg-gradient-to-r from-blue-600 to-purple-600 h-full transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
          <p className="text-gray-500 mt-2 text-sm">{progress}%</p>
        </div>
      </div>
    );
  }

  // Database error screen
  if (dbError) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-center max-w-md">
          <AlertCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-white mb-2">Database Load Failed</h2>
          <p className="text-gray-400 mb-4">{dbError}</p>
          <button
            onClick={() => window.location.reload()}
            className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={`min-h-screen ${isDarkMode ? 'bg-gray-900' : 'bg-gray-50'} transition-colors duration-300`}>
      {/* Header */}
      <header className={`${isDarkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'} border-b`}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="bg-gradient-to-br from-blue-500 to-purple-600 p-3 rounded-xl">
                <Database className="w-8 h-8 text-white" />
              </div>
              <div>
                <h1 className={`text-2xl font-bold ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
                  tmRNA Database
                </h1>
                <p className={`text-sm ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                  67,383 sequences • Powered by BLOSUM62 & Simple Alignment
                </p>
              </div>
            </div>
            <button
              onClick={() => setIsDarkMode(!isDarkMode)}
              className={`px-4 py-2 rounded-lg ${
                isDarkMode 
                  ? 'bg-gray-700 text-gray-200 hover:bg-gray-600' 
                  : 'bg-gray-200 text-gray-800 hover:bg-gray-300'
              } transition-colors`}
            >
              {isDarkMode ? '☀️ Light' : '🌙 Dark'}
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Tab Navigation */}
        <div className="flex gap-2 mb-8">
          {[
            { id: 'keyword', label: 'Keyword Search', icon: Search, badge: 'Instant' },
            { id: 'peptide', label: 'Peptide Similarity', icon: Sparkles, badge: 'BLOSUM62' },
            { id: 'codon', label: 'Codon Similarity', icon: Dna, badge: 'Python' }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-6 py-3 rounded-lg font-medium transition-all relative ${
                activeTab === tab.id
                  ? isDarkMode
                    ? 'bg-gradient-to-r from-blue-600 to-purple-600 text-white shadow-lg shadow-blue-500/30'
                    : 'bg-gradient-to-r from-blue-500 to-purple-500 text-white shadow-lg'
                  : isDarkMode
                    ? 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                    : 'bg-white text-gray-600 hover:bg-gray-100'
              }`}
            >
              <tab.icon className="w-5 h-5" />
              {tab.label}
              {tab.badge && (
                <span className={`text-xs px-2 py-0.5 rounded ${
                  activeTab === tab.id
                    ? 'bg-white/20'
                    : isDarkMode ? 'bg-gray-700' : 'bg-gray-200'
                }`}>
                  {tab.badge}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Search Forms */}
        <div className={`${isDarkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'} rounded-xl border p-6 mb-8 shadow-xl`}>
          {/* Keyword Search */}
          {activeTab === 'keyword' && (
  <div className="space-y-4">
    <div>
      <label className={`block text-sm font-medium mb-2 ${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>
        Search by Identifier or Organism
      </label>
      <div className="relative">
        <input
          type="text"
          value={keywordQuery}
          onChange={(e) => {
            setKeywordQuery(e.target.value);
            setShowAutocomplete(true);
          }}
          onFocus={() => setShowAutocomplete(autocompleteSuggestions.length > 0)}
          onBlur={() => setTimeout(() => setShowAutocomplete(false), 200)}
          onKeyPress={(e) => {
            if (e.key === 'Enter') {
              setShowAutocomplete(false);
              handleSearch();
            }
          }}
          placeholder="e.g., Magnetovibrio, URS0000C900BF, Planctomycetes..."
          className={`w-full px-4 py-3 rounded-lg border ${
            isDarkMode 
              ? 'bg-gray-900 border-gray-600 text-white placeholder-gray-500' 
              : 'bg-gray-50 border-gray-300 text-gray-900 placeholder-gray-400'
          } focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all`}
        />
        
        {/* Real-time Autocomplete */}
        {showAutocomplete && autocompleteSuggestions.length > 0 && (
          <div className={`absolute z-50 w-full mt-2 ${
            isDarkMode ? 'bg-gray-700' : 'bg-white'
          } rounded-lg shadow-xl border ${
            isDarkMode ? 'border-gray-600' : 'border-gray-200'
          } max-h-96 overflow-y-auto`}>
            <div className={`px-3 py-2 text-xs ${
              isDarkMode ? 'text-gray-400 border-gray-600' : 'text-gray-500 border-gray-200'
            } border-b flex items-center gap-2`}>
              <Search className="w-3 h-3" />
              {autocompleteSuggestions.length} suggestion{autocompleteSuggestions.length !== 1 ? 's' : ''} found
            </div>
            
            {autocompleteSuggestions.map((suggestion, idx) => (
              <button
                key={idx}
                onClick={() => handleAutocompleteSelect(suggestion.identifier)}
                className={`w-full px-4 py-3 text-left transition-colors ${
                  isDarkMode 
                    ? 'hover:bg-gray-600 text-gray-200' 
                    : 'hover:bg-gray-50 text-gray-800'
                } ${idx === autocompleteSuggestions.length - 1 ? '' : 'border-b'} ${
                  isDarkMode ? 'border-gray-600' : 'border-gray-100'
                }`}
              >
                <div className="flex flex-col gap-1">
                  <div className={`text-sm font-mono ${
                    isDarkMode ? 'text-blue-400' : 'text-blue-600'
                  }`}>
                    {suggestion.identifier}
                  </div>
                  {suggestion.organism && (
                    <div className={`text-xs ${
                      isDarkMode ? 'text-gray-400' : 'text-gray-600'
                    }`}>
                      {suggestion.organism}
                    </div>
                  )}
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
      <p className={`text-xs mt-2 ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
        ⚡ Type at least 3 characters for real-time suggestions
      </p>
    </div>
  </div>
)}

          {/* Peptide Search */}
          {activeTab === 'peptide' && (
            <div className="space-y-6">
              <div>
                <label className={`block text-sm font-medium mb-2 ${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                  Tag Peptide Sequence
                </label>
                <textarea
                  value={peptideQuery}
                  onChange={(e) => setPeptideQuery(e.target.value)}
                  placeholder="e.g., ?NDNYAPVRAAA*"
                  rows={4}
                  className={`w-full px-4 py-3 rounded-lg border font-mono text-sm ${
                    isDarkMode 
                      ? 'bg-gray-900 border-gray-600 text-white placeholder-gray-500' 
                      : 'bg-gray-50 border-gray-300 text-gray-900 placeholder-gray-400'
                  } focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all`}
                />
                <p className={`text-xs mt-2 ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                  Special characters (?, *) will be automatically removed
                </p>
              </div>

              {/* Similarity Threshold Slider */}
              <div>
                <div className="flex items-center justify-between mb-3">
                  <label className={`text-sm font-medium ${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                    Minimum Similarity Threshold
                  </label>
                  <div className="flex items-center gap-2">
                    <span className={`text-2xl font-bold ${isDarkMode ? 'text-blue-400' : 'text-blue-600'}`}>
                      {peptideThreshold}%
                    </span>
                    <span className={`text-xs px-2 py-1 rounded ${
                      isDarkMode ? 'bg-gray-700 text-gray-300' : 'bg-gray-200 text-gray-700'
                    }`}>
                      {getThresholdLabel(peptideThreshold)}
                    </span>
                  </div>
                </div>
                
                <div className="relative">
                  <input
                    type="range"
                    min="50"
                    max="100"
                    value={peptideThreshold}
                    onChange={(e) => setPeptideThreshold(Number(e.target.value))}
                    className="w-full h-2 rounded-lg appearance-none cursor-pointer slider"
                  />
                  <div className="flex justify-between text-xs mt-2">
                    <span className={isDarkMode ? 'text-gray-400' : 'text-gray-600'}>50% (Loose)</span>
                    <span className={isDarkMode ? 'text-gray-400' : 'text-gray-600'}>100% (Exact)</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Codon Search */}
          {activeTab === 'codon' && (
            <div className="space-y-6">
              <div>
                <label className={`block text-sm font-medium mb-2 ${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                  Codon Sequence
                </label>
                <textarea
                  value={codonQuery}
                  onChange={(e) => setCodonQuery(e.target.value)}
                  placeholder="e.g., -aac-gac-aac-tat-gct-ccg-gtt-cgt-gcc-gct-gct-taa"
                  rows={4}
                  className={`w-full px-4 py-3 rounded-lg border font-mono text-sm ${
                    isDarkMode 
                      ? 'bg-gray-900 border-gray-600 text-white placeholder-gray-500' 
                      : 'bg-gray-50 border-gray-300 text-gray-900 placeholder-gray-400'
                  } focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all`}
                />
                <p className={`text-xs mt-2 ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                  Hyphens and spaces will be automatically removed
                </p>
              </div>

              {/* Similarity Threshold Slider */}
              <div>
                <div className="flex items-center justify-between mb-3">
                  <label className={`text-sm font-medium ${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                    Minimum Similarity Threshold
                  </label>
                  <div className="flex items-center gap-2">
                    <span className={`text-2xl font-bold ${isDarkMode ? 'text-purple-400' : 'text-purple-600'}`}>
                      {codonThreshold}%
                    </span>
                    <span className={`text-xs px-2 py-1 rounded ${
                      isDarkMode ? 'bg-gray-700 text-gray-300' : 'bg-gray-200 text-gray-700'
                    }`}>
                      {getThresholdLabel(codonThreshold)}
                    </span>
                  </div>
                </div>
                
                <input
                  type="range"
                  min="50"
                  max="100"
                  value={codonThreshold}
                  onChange={(e) => setCodonThreshold(Number(e.target.value))}
                  className="w-full h-2 rounded-lg appearance-none cursor-pointer slider"
                />
                <div className="flex justify-between text-xs mt-2">
                  <span className={isDarkMode ? 'text-gray-400' : 'text-gray-600'}>50% (Loose)</span>
                  <span className={isDarkMode ? 'text-gray-400' : 'text-gray-600'}>100% (Exact)</span>
                </div>
              </div>
            </div>
          )}

          {/* Search Button */}
          <button
            onClick={handleSearch}
            disabled={isSearching || 
                     (activeTab === 'keyword' && !keywordQuery) || 
                     (activeTab === 'peptide' && !peptideQuery) || 
                     (activeTab === 'codon' && !codonQuery)}
            className={`w-full mt-6 px-6 py-3 rounded-lg font-medium flex items-center justify-center gap-2 transition-all ${
              isSearching || (activeTab === 'keyword' && !keywordQuery) || 
              (activeTab === 'peptide' && !peptideQuery) || 
              (activeTab === 'codon' && !codonQuery)
                ? isDarkMode ? 'bg-gray-700 text-gray-500 cursor-not-allowed' : 'bg-gray-200 text-gray-400 cursor-not-allowed'
                : 'bg-gradient-to-r from-blue-600 to-purple-600 text-white hover:shadow-lg hover:shadow-blue-500/50 transform hover:-translate-y-0.5'
            }`}
          >
            {isSearching ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Searching...
              </>
            ) : (
              <>
                <Search className="w-5 h-5" />
                Search Database
                <ArrowRight className="w-5 h-5" />
              </>
            )}
          </button>

          {/* Search Error */}
          {searchError && (
            <div className="mt-4 p-4 bg-red-500/10 border border-red-500/50 rounded-lg">
              <p className="text-red-400 text-sm flex items-center gap-2">
                <AlertCircle className="w-4 h-4" />
                {searchError}
              </p>
            </div>
          )}
        </div>

        {/* Results Section */}
        {filteredResults.length > 0 && (
          <div className={`${isDarkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'} rounded-xl border p-6 shadow-xl animate-fade-in`}>
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className={`text-xl font-bold ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
                  Search Results
                </h2>
                <p className={`text-sm ${isDarkMode ? 'text-gray-400' : 'text-gray-600'} mt-1`}>
                  Found {filteredResults.length} result(s) {activeTab !== 'keyword' && `with ≥${activeTab === 'peptide' ? peptideThreshold : codonThreshold}% similarity`}
                  {searchTime > 0 && ` • ${searchTime.toFixed(2)}s`}
                </p>
              </div>
              <button
                onClick={handleExport}
                className={`px-4 py-2 rounded-lg flex items-center gap-2 ${
                  isDarkMode 
                    ? 'bg-green-600 hover:bg-green-700 text-white' 
                    : 'bg-green-500 hover:bg-green-600 text-white'
                } transition-colors`}
              >
                <Download className="w-4 h-4" />
                Export CSV
              </button>
            </div>

            {/* Results Table */}
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className={`${isDarkMode ? 'bg-gray-700' : 'bg-gray-50'}`}>
                    <th className={`px-4 py-3 text-left text-sm font-medium ${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                      Identifier
                    </th>
                    <th className={`px-4 py-3 text-left text-sm font-medium ${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                      Tag Peptide
                    </th>
                    {activeTab !== 'keyword' && (
                      <>
                        <th className={`px-4 py-3 text-left text-sm font-medium ${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                          Similarity
                        </th>
                        <th className={`px-4 py-3 text-left text-sm font-medium ${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                          E-value
                        </th>
                      </>
                    )}
                    <th className={`px-4 py-3 text-left text-sm font-medium ${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                      Codons
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {filteredResults.map((result, idx) => (
                    <tr
                      key={idx}
                      className={`${isDarkMode ? 'border-gray-700 hover:bg-gray-700/50' : 'border-gray-200 hover:bg-gray-50'} border-t transition-colors`}
                      style={{
                        animation: `fadeIn 0.3s ease-out ${idx * 0.05}s both`
                      }}
                    >
                      <td className={`px-4 py-3 text-sm ${isDarkMode ? 'text-gray-300' : 'text-gray-800'}`}>
                        {result.identifier}
                      </td>
                      <td className={`px-4 py-3 text-sm font-mono ${isDarkMode ? 'text-blue-400' : 'text-blue-600'}`}>
                        {result.tag_peptide}
                      </td>
                      {activeTab !== 'keyword' && result.similarity && (
                        <>
                          <td className={`px-4 py-3 text-sm font-bold ${getSimilarityColor(result.similarity)}`}>
                            {result.similarity}%
                          </td>
                          <td className={`px-4 py-3 text-sm ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                            {result.e_value}
                          </td>
                        </>
                      )}
                      <td className={`px-4 py-3 text-sm font-mono ${isDarkMode ? 'text-gray-400' : 'text-gray-600'} truncate max-w-xs`}>
                        {result.codons}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Empty State */}
        {!isSearching && filteredResults.length === 0 && (
          <div className={`${isDarkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'} rounded-xl border p-12 text-center animate-fade-in`}>
            <div className={`w-16 h-16 mx-auto mb-4 rounded-full ${isDarkMode ? 'bg-gray-700' : 'bg-gray-100'} flex items-center justify-center`}>
              <Database className={`w-8 h-8 ${isDarkMode ? 'text-gray-500' : 'text-gray-400'}`} />
            </div>
            <h3 className={`text-lg font-medium ${isDarkMode ? 'text-gray-300' : 'text-gray-700'} mb-2`}>
              No results yet
            </h3>
            <p className={`text-sm ${isDarkMode ? 'text-gray-500' : 'text-gray-600'}`}>
              Enter a search query above to find tmRNA sequences
            </p>
          </div>
        )}
      </main>

      <style>{`
        @keyframes fadeIn {
          from {
            opacity: 0;
            transform: translateY(10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        .slider {
          background: linear-gradient(to right, 
            rgb(239, 68, 68) 0%, 
            rgb(251, 191, 36) 25%, 
            rgb(59, 130, 246) 50%, 
            rgb(34, 197, 94) 100%
          );
        }

        .slider::-webkit-slider-thumb {
          -webkit-appearance: none;
          appearance: none;
          width: 20px;
          height: 20px;
          border-radius: 50%;
          background: white;
          cursor: pointer;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
          border: 3px solid ${isDarkMode ? 'rgb(59, 130, 246)' : 'rgb(37, 99, 235)'};
        }

        .slider::-moz-range-thumb {
          width: 20px;
          height: 20px;
          border-radius: 50%;
          background: white;
          cursor: pointer;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
          border: 3px solid ${isDarkMode ? 'rgb(59, 130, 246)' : 'rgb(37, 99, 235)'};
        }
      `}</style>
    </div>
  );
}