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

# CRITICAL: Configure CORS properly for Vercel
CORS(app, 
     resources={r"/api/*": {"origins": "*"}},
     methods=["GET", "POST", "OPTIONS"],
     allow_headers=["Content-Type", "Authorization"],
     expose_headers=["Content-Type"],
     supports_credentials=False,
     max_age=3600)

@app.after_request
def add_cors_headers(response):
    """Add CORS headers to every response"""
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Max-Age"] = "3600"
    return response

@app.before_request
def handle_preflight():
    """Handle OPTIONS preflight requests"""
    if request.method == "OPTIONS":
        response = jsonify({"status": "ok"})
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Max-Age"] = "3600"
        return response, 200

# Configuration
DB_PATH = os.environ.get('DB_PATH', '../tmrna.db')
DIAMOND_DB = os.environ.get('DIAMOND_DB', 'peptide_db')
BLAT_DB = os.environ.get('BLAT_DB', 'codons.fasta')
CACHE_DIR = 'cache'

# Create cache directory
os.makedirs(CACHE_DIR, exist_ok=True)


# ============================================
# Utility Functions
# ============================================

BLOSUM62 = {
    ('A', 'A'): 4,  ('A', 'R'): -1, ('A', 'N'): -2, ('A', 'D'): -2, ('A', 'C'): 0,
    ('A', 'Q'): -1, ('A', 'E'): -1, ('A', 'G'): 0,  ('A', 'H'): -2, ('A', 'I'): -1,
    ('A', 'L'): -1, ('A', 'K'): -1, ('A', 'M'): -1, ('A', 'F'): -2, ('A', 'P'): -1,
    ('A', 'S'): 1,  ('A', 'T'): 0,  ('A', 'W'): -3, ('A', 'Y'): -2, ('A', 'V'): 0,
    ('R', 'R'): 5,  ('R', 'N'): 0,  ('R', 'D'): -2, ('R', 'C'): -3, ('R', 'Q'): 1,
    ('R', 'E'): 0,  ('R', 'G'): -2, ('R', 'H'): 0,  ('R', 'I'): -3, ('R', 'L'): -2,
    ('R', 'K'): 2,  ('R', 'M'): -1, ('R', 'F'): -3, ('R', 'P'): -2, ('R', 'S'): -1,
    ('R', 'T'): -1, ('R', 'W'): -3, ('R', 'Y'): -2, ('R', 'V'): -3, ('N', 'N'): 6,
    ('N', 'D'): 1,  ('N', 'C'): -3, ('N', 'Q'): 0,  ('N', 'E'): 0,  ('N', 'G'): 0,
    ('N', 'H'): 1,  ('N', 'I'): -3, ('N', 'L'): -3, ('N', 'K'): 0,  ('N', 'M'): -2,
    ('N', 'F'): -3, ('N', 'P'): -2, ('N', 'S'): 1,  ('N', 'T'): 0,  ('N', 'W'): -4,
    ('N', 'Y'): -2, ('N', 'V'): -3, ('D', 'D'): 6,  ('D', 'C'): -3, ('D', 'Q'): 0,
    ('D', 'E'): 2,  ('D', 'G'): -1, ('D', 'H'): -1, ('D', 'I'): -3, ('D', 'L'): -4,
    ('D', 'K'): -1, ('D', 'M'): -3, ('D', 'F'): -3, ('D', 'P'): -1, ('D', 'S'): 0,
    ('D', 'T'): -1, ('D', 'W'): -4, ('D', 'Y'): -3, ('D', 'V'): -3, ('C', 'C'): 9,
    ('C', 'Q'): -3, ('C', 'E'): -4, ('C', 'G'): -3, ('C', 'H'): -3, ('C', 'I'): -1,
    ('C', 'L'): -1, ('C', 'K'): -3, ('C', 'M'): -1, ('C', 'F'): -2, ('C', 'P'): -3,
    ('C', 'S'): -1, ('C', 'T'): -1, ('C', 'W'): -2, ('C', 'Y'): -2, ('C', 'V'): -1,
    ('Q', 'Q'): 5,  ('Q', 'E'): 2,  ('Q', 'G'): -2, ('Q', 'H'): 0,  ('Q', 'I'): -3,
    ('Q', 'L'): -2, ('Q', 'K'): 1,  ('Q', 'M'): 0,  ('Q', 'F'): -3, ('Q', 'P'): -1,
    ('Q', 'S'): 0,  ('Q', 'T'): -1, ('Q', 'W'): -2, ('Q', 'Y'): -1, ('Q', 'V'): -2,
    ('E', 'E'): 5,  ('E', 'G'): -2, ('E', 'H'): 0,  ('E', 'I'): -3, ('E', 'L'): -3,
    ('E', 'K'): 1,  ('E', 'M'): -2, ('E', 'F'): -3, ('E', 'P'): -1, ('E', 'S'): 0,
    ('E', 'T'): -1, ('E', 'W'): -3, ('E', 'Y'): -2, ('E', 'V'): -2, ('G', 'G'): 6,
    ('G', 'H'): -2, ('G', 'I'): -4, ('G', 'L'): -4, ('G', 'K'): -2, ('G', 'M'): -3,
    ('G', 'F'): -3, ('G', 'P'): -2, ('G', 'S'): 0,  ('G', 'T'): -2, ('G', 'W'): -2,
    ('G', 'Y'): -3, ('G', 'V'): -3, ('H', 'H'): 8,  ('H', 'I'): -3, ('H', 'L'): -3,
    ('H', 'K'): -1, ('H', 'M'): -2, ('H', 'F'): -1, ('H', 'P'): -2, ('H', 'S'): -1,
    ('H', 'T'): -2, ('H', 'W'): -2, ('H', 'Y'): 2,  ('H', 'V'): -3, ('I', 'I'): 4,
    ('I', 'L'): 2,  ('I', 'K'): -3, ('I', 'M'): 1,  ('I', 'F'): 0,  ('I', 'P'): -3,
    ('I', 'S'): -2, ('I', 'T'): -1, ('I', 'W'): -3, ('I', 'Y'): -1, ('I', 'V'): 3,
    ('L', 'L'): 4,  ('L', 'K'): -2, ('L', 'M'): 2,  ('L', 'F'): 0,  ('L', 'P'): -3,
    ('L', 'S'): -2, ('L', 'T'): -1, ('L', 'W'): -2, ('L', 'Y'): -1, ('L', 'V'): 1,
    ('K', 'K'): 5,  ('K', 'M'): -1, ('K', 'F'): -3, ('K', 'P'): -1, ('K', 'S'): 0,
    ('K', 'T'): -1, ('K', 'W'): -3, ('K', 'Y'): -2, ('K', 'V'): -2, ('M', 'M'): 5,
    ('M', 'F'): 0,  ('M', 'P'): -2, ('M', 'S'): -1, ('M', 'T'): -1, ('M', 'W'): -1,
    ('M', 'Y'): -1, ('M', 'V'): 1,  ('F', 'F'): 6,  ('F', 'P'): -4, ('F', 'S'): -2,
    ('F', 'T'): -2, ('F', 'W'): 1,  ('F', 'Y'): 3,  ('F', 'V'): -1, ('P', 'P'): 7,
    ('P', 'S'): -1, ('P', 'T'): -1, ('P', 'W'): -4, ('P', 'Y'): -3, ('P', 'V'): -2,
    ('S', 'S'): 4,  ('S', 'T'): 1,  ('S', 'W'): -3, ('S', 'Y'): -2, ('S', 'V'): -2,
    ('T', 'T'): 5,  ('T', 'W'): -2, ('T', 'Y'): -2, ('T', 'V'): 0,  ('W', 'W'): 11,
    ('W', 'Y'): 2,  ('W', 'V'): -3, ('Y', 'Y'): 7,  ('Y', 'V'): -1, ('V', 'V'): 4
}


def get_db_connection():
    """Create SQLite database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def cache_result(timeout=3600):
    """Decorator to cache API results"""
    os.makedirs(CACHE_DIR, exist_ok=True)
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            cache_key = hashlib.md5(
                f"{f.__name__}:{json.dumps(request.get_json(), sort_keys=True)}".encode()
            ).hexdigest()
            cache_file = os.path.join(CACHE_DIR, f"{cache_key}.json")
            
            if os.path.exists(cache_file):
                cache_age = time.time() - os.path.getmtime(cache_file)
                if cache_age < timeout:
                    with open(cache_file, 'r') as file_handle:
                        print("✅ Returning response from FILE CACHE")
                        return jsonify(json.load(file_handle))
            
            result = f(*args, **kwargs)
            
            if result.status_code == 200 and result.is_json:
                with open(cache_file, 'w') as file_handle:
                    json.dump(result.get_json(), file_handle)
            
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

@app.route('/api/health', methods=['GET', 'OPTIONS'])
def health_check():
    """Health check endpoint"""
    if request.method == 'OPTIONS':
        return '', 204
    
    return jsonify({
        'status': 'healthy',
        'database': os.path.exists(DB_PATH),
        'diamond': os.path.exists(f"{DIAMOND_DB}.dmnd"),
        'blat': os.path.exists(BLAT_DB)
    })


# ============================================
# Database Info Endpoint
# ============================================

@app.route('/api/info', methods=['GET', 'OPTIONS'])
def database_info():
    """Get database statistics"""
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM tmrna_data')
        total_records = cursor.fetchone()[0]
        
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
# Peptide Similarity Search
# ============================================

def get_blosum_score(aa1, aa2):
    """Get BLOSUM62 score for two amino acids"""
    aa1, aa2 = aa1.upper(), aa2.upper()
    if (aa1, aa2) in BLOSUM62:
        return BLOSUM62[(aa1, aa2)]
    elif (aa2, aa1) in BLOSUM62:
        return BLOSUM62[(aa2, aa1)]
    else:
        return -4


def calculate_peptide_similarity_blosum(seq1, seq2):
    """Calculate peptide similarity using BLOSUM62 matrix"""
    min_len = min(len(seq1), len(seq2))
    max_len = max(len(seq1), len(seq2))
    
    if min_len == 0:
        return 0.0
    
    score = 0
    max_possible_score = 0
    
    for i in range(min_len):
        blosum_score = get_blosum_score(seq1[i], seq2[i])
        score += blosum_score
        max_possible_score += get_blosum_score(seq1[i], seq1[i])
    
    length_penalty = min_len / max_len
    
    if max_possible_score > 0:
        similarity = (score / max_possible_score) * 100 * length_penalty
    else:
        similarity = 0.0
    
    return max(0.0, similarity)


@app.route('/api/search/peptide', methods=['POST', 'OPTIONS'])
@cache_result(timeout=3600)
def search_peptide():
    """Peptide similarity search using BLOSUM62"""
    if request.method == 'OPTIONS':
        return '', 204
    
    start_time = time.time()
    
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400

        sequence = data.get('sequence', '')
        threshold = float(data.get('threshold', 50.0))

        if not sequence:
            return jsonify({'error': 'Sequence is required'}), 400

        clean_seq = sequence.replace('?', '').replace('*', '').replace(' ', '').replace('\n', '').strip().upper()
        
        print(f"🔍 Input sequence: {sequence}")
        print(f"🧹 Cleaned sequence: {clean_seq}")
        print(f"📏 Length: {len(clean_seq)} amino acids")
        print(f"🎯 Threshold: {threshold}%")

        if len(clean_seq) < 3:
            return jsonify({'error': 'Sequence too short (minimum 3 amino acids)'}), 400

        print(f"🔍 Searching database with BLOSUM62 algorithm...")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT identifier, tag_peptide FROM tmrna_data')
        all_sequences = cursor.fetchall()
        
        results = []
        processed = 0
        
        for row in all_sequences:
            identifier = row['identifier']
            peptide = row['tag_peptide']
            
            db_seq = peptide.replace('?', '').replace('*', '').strip().upper()
            
            if len(db_seq) < 3:
                continue
            
            similarity = calculate_peptide_similarity_blosum(clean_seq, db_seq)
            
            if similarity >= threshold:
                cursor.execute('SELECT * FROM tmrna_data WHERE identifier = ?', (identifier,))
                full_row = cursor.fetchone()
                
                if full_row:
                    result_dict = dict(full_row)
                    result_dict['similarity'] = round(similarity, 2)
                    result_dict['e_value'] = 'N/A'
                    result_dict['algorithm'] = 'BLOSUM62'
                    results.append(result_dict)
            
            processed += 1
            if processed % 10000 == 0:
                print(f"   Processed {processed:,} sequences...")
        
        conn.close()
        
        results.sort(key=lambda x: x['similarity'], reverse=True)
        results = results[:500]
        
        search_time = time.time() - start_time
        
        print(f"✅ Found {len(results)} matches in {search_time:.2f}s")
        
        return jsonify({
            'results': results,
            'total': len(results),
            'search_time': round(search_time, 2),
            'query_length': len(clean_seq),
            'threshold': threshold,
            'algorithm': 'Python BLOSUM62'
        })
    
    except Exception as e:
        import traceback
        print(f"❌ Error in peptide search: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


# ============================================
# Codon Similarity Search
# ============================================

def calculate_nucleotide_similarity(seq1, seq2):
    """Calculate simple nucleotide similarity"""
    min_len = min(len(seq1), len(seq2))
    
    if min_len == 0:
        return 0.0
    
    matches = sum(1 for i in range(min_len) if seq1[i].lower() == seq2[i].lower())
    similarity = (matches / min_len) * 100
    
    return similarity


@app.route('/api/search/codon', methods=['POST', 'OPTIONS'])
@cache_result(timeout=3600)
def search_codon():
    """Codon similarity search using simple nucleotide alignment"""
    if request.method == 'OPTIONS':
        return '', 204
    
    start_time = time.time()
    
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        sequence = data.get('sequence', '')
        threshold = float(data.get('threshold', 50.0))
        
        if not sequence:
            return jsonify({'error': 'Sequence is required'}), 400
        
        clean_seq = clean_codon_sequence(sequence)
        
        if len(clean_seq) < 15:
            return jsonify({'error': 'Sequence too short (minimum 15 nucleotides)'}), 400
        
        print(f"🔍 Searching for codon similarity with threshold {threshold}%...")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT identifier, codons FROM tmrna_data')
        all_sequences = cursor.fetchall()
        
        results = []
        
        for row in all_sequences:
            identifier = row['identifier']
            codons = row['codons']
            
            db_seq = clean_codon_sequence(codons)
            similarity = calculate_nucleotide_similarity(clean_seq, db_seq)
            
            if similarity >= threshold:
                cursor.execute('SELECT * FROM tmrna_data WHERE identifier = ?', (identifier,))
                full_row = cursor.fetchone()
                
                if full_row:
                    result_dict = dict(full_row)
                    result_dict['similarity'] = round(similarity, 2)
                    result_dict['e_value'] = 'N/A'
                    results.append(result_dict)
        
        conn.close()
        
        results.sort(key=lambda x: x['similarity'], reverse=True)
        results = results[:500]
        
        search_time = time.time() - start_time
        
        print(f"✅ Found {len(results)} matches in {search_time:.2f}s")
        
        return jsonify({
            'results': results,
            'total': len(results),
            'search_time': round(search_time, 2),
            'query_length': len(clean_seq),
            'threshold': threshold,
            'algorithm': 'Simple Nucleotide Alignment'
        })
    
    except Exception as e:
        print(f"❌ Error in codon search: {e}")
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
    
    app.run(host='0.0.0.0', port=8000, debug=True)