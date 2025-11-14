# ============================================
# FILE: backend/app.py
# ============================================
"""
Minimal Flask API for tmRNA Database
Only handles DIAMOND (peptide) and BLAT (codon) similarity searches
Keyword search handled by frontend using sql.js
"""

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import subprocess
import tempfile
import os
import sqlite3
import hashlib
import json
from functools import wraps
import time

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend

# Configuration
DB_PATH = os.environ.get('DB_PATH', 'tmrna.db')
DIAMOND_DB = os.environ.get('DIAMOND_DB', 'peptide_db')
BLAT_DB = os.environ.get('BLAT_DB', 'codons.fasta')
CACHE_DIR = 'cache'

# Create cache directory
os.makedirs(CACHE_DIR, exist_ok=True)


# ============================================
# Utility Functions
# ============================================

def get_db_connection():
    """Create SQLite database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def cache_result(timeout=3600):
    """Decorator to cache API results"""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # Create cache key from request data
            cache_key = hashlib.md5(
                f"{f.__name__}:{json.dumps(request.get_json(), sort_keys=True)}".encode()
            ).hexdigest()
            cache_file = os.path.join(CACHE_DIR, f"{cache_key}.json")
            
            # Check if cache exists and is fresh
            if os.path.exists(cache_file):
                cache_age = time.time() - os.path.getmtime(cache_file)
                if cache_age < timeout:
                    with open(cache_file, 'r') as f:
                        return jsonify(json.load(f))
            
            # Execute function and cache result
            result = f(*args, **kwargs)
            with open(cache_file, 'w') as f:
                json.dump(result.get_json(), f)
            
            return result
        return wrapper
    return decorator


def clean_peptide_sequence(sequence):
    """Clean peptide sequence by removing special characters"""
    return sequence.replace('?', '').replace('*', '').replace(' ', '').replace('\n', '').strip().upper()


def clean_codon_sequence(sequence):
    """Clean codon sequence by removing hyphens and spaces"""
    return sequence.replace('-', '').replace(' ', '').replace('\n', '').strip().lower()


# ============================================
# Health Check Endpoint
# ============================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'database': os.path.exists(DB_PATH),
        'diamond': os.path.exists(f"{DIAMOND_DB}.dmnd"),
        'blat': os.path.exists(BLAT_DB)
    })


# ============================================
# Database Info Endpoint (for frontend initialization)
# ============================================

@app.route('/api/info', methods=['GET'])
def database_info():
    """Get database statistics"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get total records
        cursor.execute('SELECT COUNT(*) FROM tmrna_data')
        total_records = cursor.fetchone()[0]
        
        # Get unique organisms
        cursor.execute('SELECT COUNT(DISTINCT organism_name) FROM tmrna_data WHERE organism_name != ""')
        unique_organisms = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'total_records': total_records,
            'unique_organisms': unique_organisms,
            'database_size_mb': os.path.getsize(DB_PATH) / (1024 * 1024)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================
# Peptide Similarity Search (DIAMOND)
# ============================================

@app.route('/api/search/peptide', methods=['POST'])
@cache_result(timeout=3600)  # Cache for 1 hour
def search_peptide():
    """
    Peptide similarity search using DIAMOND
    
    Request JSON:
    {
        "sequence": "ANDNYAPVRAAA",
        "threshold": 75.0  (optional, default 50)
    }
    
    Response JSON:
    {
        "results": [
            {
                "identifier": "...",
                "tag_peptide": "...",
                "similarity": 95.5,
                "e_value": "1.2e-5",
                "bit_score": 42.8,
                ...
            }
        ],
        "total": 150,
        "search_time": 1.23
    }
    """
    start_time = time.time()
    
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        sequence = data.get('sequence', '')
        threshold = float(data.get('threshold', 50.0))
        
        if not sequence:
            return jsonify({'error': 'Sequence is required'}), 400
        
        # Clean sequence
        clean_seq = clean_peptide_sequence(sequence)
        
        if len(clean_seq) < 3:
            return jsonify({'error': 'Sequence too short (minimum 3 amino acids)'}), 400
        
        # Check if DIAMOND database exists
        if not os.path.exists(f"{DIAMOND_DB}.dmnd"):
            return jsonify({'error': 'DIAMOND database not found'}), 500
        
        # Create temporary query file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.fasta', delete=False) as query_file:
            query_file.write(f">query\n{clean_seq}\n")
            query_path = query_file.name
        
        # Create temporary output file
        output_path = tempfile.mktemp(suffix='.tsv')
        
        try:
            # Run DIAMOND blastp
            cmd = [
                'diamond', 'blastp',
                '--query', query_path,
                '--db', DIAMOND_DB,
                '--out', output_path,
                '--outfmt', '6', 'sseqid', 'pident', 'evalue', 'bitscore', 'length', 'qlen',
                '--id', str(threshold),
                '--threads', '2',
                '--max-target-seqs', '500',
                '--sensitive'  # More sensitive search
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60  # 60 second timeout
            )
            
            if result.returncode != 0:
                return jsonify({
                    'error': 'DIAMOND search failed',
                    'details': result.stderr
                }), 500
            
            # Parse DIAMOND output
            results = []
            
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                conn = get_db_connection()
                cursor = conn.cursor()
                
                with open(output_path, 'r') as f:
                    for line in f:
                        fields = line.strip().split('\t')
                        if len(fields) >= 4:
                            identifier = fields[0]
                            similarity = float(fields[1])
                            evalue = float(fields[2])
                            bitscore = float(fields[3])
                            
                            # Fetch full record from database
                            cursor.execute('''
                                SELECT * FROM tmrna_data 
                                WHERE identifier = ?
                            ''', (identifier,))
                            
                            row = cursor.fetchone()
                            if row:
                                result_dict = dict(row)
                                result_dict['similarity'] = round(similarity, 2)
                                result_dict['e_value'] = f"{evalue:.2e}"
                                result_dict['bit_score'] = round(bitscore, 2)
                                results.append(result_dict)
                
                conn.close()
            
            # Sort by similarity (highest first)
            results.sort(key=lambda x: x['similarity'], reverse=True)
            
            search_time = time.time() - start_time
            
            return jsonify({
                'results': results,
                'total': len(results),
                'search_time': round(search_time, 2),
                'query_length': len(clean_seq),
                'threshold': threshold
            })
        
        finally:
            # Cleanup temporary files
            if os.path.exists(query_path):
                os.unlink(query_path)
            if os.path.exists(output_path):
                os.unlink(output_path)
    
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Search timeout (>60 seconds)'}), 504
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================
# Codon Similarity Search (BLAT)
# ============================================

@app.route('/api/search/codon', methods=['POST'])
@cache_result(timeout=3600)  # Cache for 1 hour
def search_codon():
    """
    Codon similarity search using BLAT
    
    Request JSON:
    {
        "sequence": "aacgacaactatgctccg",
        "threshold": 75.0  (optional, default 50)
    }
    
    Response JSON:
    {
        "results": [...],
        "total": 120,
        "search_time": 0.85
    }
    """
    start_time = time.time()
    
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        sequence = data.get('sequence', '')
        threshold = float(data.get('threshold', 50.0))
        
        if not sequence:
            return jsonify({'error': 'Sequence is required'}), 400
        
        # Clean sequence
        clean_seq = clean_codon_sequence(sequence)
        
        if len(clean_seq) < 15:
            return jsonify({'error': 'Sequence too short (minimum 15 nucleotides)'}), 400
        
        # Check if BLAT database exists
        if not os.path.exists(BLAT_DB):
            return jsonify({'error': 'BLAT database not found'}), 500
        
        # Create temporary query file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.fasta', delete=False) as query_file:
            query_file.write(f">query\n{clean_seq}\n")
            query_path = query_file.name
        
        # Create temporary output file
        output_path = tempfile.mktemp(suffix='.psl')
        
        try:
            # Run BLAT
            cmd = [
                'blat',
                BLAT_DB,
                query_path,
                output_path,
                f'-minIdentity={int(threshold)}',
                '-out=blast8',  # BLAST-like tabular output
                '-noHead'  # No header
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60  # 60 second timeout
            )
            
            if result.returncode != 0:
                return jsonify({
                    'error': 'BLAT search failed',
                    'details': result.stderr
                }), 500
            
            # Parse BLAT output
            results = []
            
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                conn = get_db_connection()
                cursor = conn.cursor()
                
                with open(output_path, 'r') as f:
                    for line in f:
                        if line.startswith('#'):
                            continue
                        
                        fields = line.strip().split('\t')
                        if len(fields) >= 11:
                            identifier = fields[1]
                            similarity = float(fields[2])
                            evalue = float(fields[10])
                            
                            # Fetch full record from database
                            cursor.execute('''
                                SELECT * FROM tmrna_data 
                                WHERE identifier = ?
                            ''', (identifier,))
                            
                            row = cursor.fetchone()
                            if row:
                                result_dict = dict(row)
                                result_dict['similarity'] = round(similarity, 2)
                                result_dict['e_value'] = f"{evalue:.2e}"
                                results.append(result_dict)
                
                conn.close()
            
            # Sort by similarity (highest first)
            results.sort(key=lambda x: x['similarity'], reverse=True)
            
            search_time = time.time() - start_time
            
            return jsonify({
                'results': results,
                'total': len(results),
                'search_time': round(search_time, 2),
                'query_length': len(clean_seq),
                'threshold': threshold
            })
        
        finally:
            # Cleanup temporary files
            if os.path.exists(query_path):
                os.unlink(query_path)
            if os.path.exists(output_path):
                os.unlink(output_path)
    
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Search timeout (>60 seconds)'}), 504
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================
# Error Handlers
# ============================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500


# ============================================
# Main
# ============================================

if __name__ == '__main__':
    # Check if required files exist
    if not os.path.exists(DB_PATH):
        print(f"⚠️  Warning: Database file not found: {DB_PATH}")
    
    if not os.path.exists(f"{DIAMOND_DB}.dmnd"):
        print(f"⚠️  Warning: DIAMOND database not found: {DIAMOND_DB}.dmnd")
    
    if not os.path.exists(BLAT_DB):
        print(f"⚠️  Warning: BLAT database not found: {BLAT_DB}")
    
    print("\n🚀 Starting tmRNA Database API Server")
    print("="*50)
    print(f"📊 Database: {DB_PATH}")
    print(f"🧬 DIAMOND DB: {DIAMOND_DB}.dmnd")
    print(f"🧬 BLAT DB: {BLAT_DB}")
    print(f"🌐 Server: http://localhost:8000")
    print("="*50)
    print("\nAPI Endpoints:")
    print("  GET  /api/health         - Health check")
    print("  GET  /api/info           - Database info")
    print("  POST /api/search/peptide - Peptide similarity")
    print("  POST /api/search/codon   - Codon similarity")
    print("\n✨ Server ready! Press Ctrl+C to stop.\n")
    
    app.run(debug=True, host='0.0.0.0', port=8000)