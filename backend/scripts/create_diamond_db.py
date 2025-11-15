# ============================================
# FILE: backend/scripts/create_diamond_db.py
# FIXED VERSION - Validates protein sequences
# ============================================
"""
Create DIAMOND database for peptide similarity search
Requires: DIAMOND installed (download from https://github.com/bbuchfink/diamond)
"""

import sqlite3
import subprocess
import os
import sys
import re

def is_valid_protein_sequence(seq):
    """
    Check if sequence contains only valid amino acid letters
    Valid: ACDEFGHIKLMNPQRSTVWY
    """
    # Standard 20 amino acids
    valid_aa = set('ACDEFGHIKLMNPQRSTVWY')
    seq_upper = seq.upper()
    
    # Check if all characters are valid amino acids
    return all(c in valid_aa for c in seq_upper) and len(seq_upper) > 0


def clean_peptide_sequence(sequence):
    """
    Clean peptide sequence by removing invalid characters
    """
    # Remove common special characters
    cleaned = sequence.replace('?', '').replace('*', '').replace('-', '').replace(' ', '').strip()
    
    # Convert to uppercase
    cleaned = cleaned.upper()
    
    # Remove any remaining non-amino acid characters
    cleaned = re.sub(r'[^ACDEFGHIKLMNPQRSTVWY]', '', cleaned)
    
    return cleaned


def create_diamond_database(db_file='tmrna.db', output_prefix='peptide_db'):
    """
    Create DIAMOND database from SQLite peptide sequences
    
    Args:
        db_file: Path to SQLite database
        output_prefix: Output database prefix (will create peptide_db.dmnd)
    """
    
    print("🚀 Creating DIAMOND database for peptide similarity search...")
    
    # Check if SQLite database exists
    if not os.path.exists(db_file):
        print(f"❌ Error: SQLite database not found: {db_file}")
        print("   Please run create_sqlite_db.py first!")
        sys.exit(1)
    
    # Check if DIAMOND is installed
    try:
        result = subprocess.run(['diamond', 'version'], 
                              capture_output=True, 
                              text=True, 
                              timeout=5)
        print(f"✅ DIAMOND found: {result.stdout.strip()}")
    except FileNotFoundError:
        print("❌ Error: DIAMOND not found!")
        print("\n📥 Please install DIAMOND:")
        print("   Windows: Download from https://github.com/bbuchfink/diamond/releases")
        print("   Linux: wget http://github.com/bbuchfink/diamond/releases/download/v2.1.9/diamond-linux64.tar.gz")
        print("   Mac: brew install diamond")
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print("⚠️  Warning: DIAMOND command timed out, but may be installed")
    
    # Connect to SQLite database
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    # Fetch all peptide sequences
    print("📥 Extracting peptide sequences from database...")
    cursor.execute('''
        SELECT identifier, tag_peptide 
        FROM tmrna_data 
        ORDER BY id
    ''')
    
    sequences = cursor.fetchall()
    conn.close()
    
    print(f"✅ Found {len(sequences):,} peptide sequences")
    
    # Create FASTA file with validation
    fasta_file = f"{output_prefix}.fasta"
    print(f"📝 Writing FASTA file: {fasta_file}")
    
    valid_count = 0
    invalid_count = 0
    too_short_count = 0
    
    with open(fasta_file, 'w') as f:
        for identifier, peptide in sequences:
            # Clean peptide sequence
            clean_peptide = clean_peptide_sequence(peptide)
            
            # Validate
            if len(clean_peptide) < 3:
                too_short_count += 1
                continue
            
            if not is_valid_protein_sequence(clean_peptide):
                invalid_count += 1
                print(f"⚠️  Invalid sequence for {identifier}: {peptide[:20]}...")
                continue
            
            # Write valid sequence
            f.write(f">{identifier}\n{clean_peptide}\n")
            valid_count += 1
    
    print(f"✅ FASTA file created with {valid_count:,} valid sequences")
    if invalid_count > 0:
        print(f"⚠️  Skipped {invalid_count} invalid sequences")
    if too_short_count > 0:
        print(f"⚠️  Skipped {too_short_count} sequences that were too short")
    
    # Verify FASTA file
    print("\n🔍 Verifying FASTA file...")
    with open(fasta_file, 'r') as f:
        lines = f.readlines()
        if len(lines) < 2:
            print("❌ Error: FASTA file is empty or invalid!")
            sys.exit(1)
        
        # Show first few sequences
        print("📄 First sequence in FASTA:")
        for i, line in enumerate(lines[:4]):
            print(f"   {line.strip()}")
    
    # Create DIAMOND database
    print("\n🔨 Building DIAMOND database (this may take 1-2 minutes)...")
    
    try:
        result = subprocess.run([
            'diamond', 'makedb',
            '--in', fasta_file,
            '--db', output_prefix
        ], capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            dmnd_file = f"{output_prefix}.dmnd"
            if os.path.exists(dmnd_file):
                size_mb = os.path.getsize(dmnd_file) / (1024 * 1024)
                print("\n" + "="*50)
                print("✅ DIAMOND DATABASE CREATED SUCCESSFULLY!")
                print("="*50)
                print(f"📊 Sequences indexed: {valid_count:,}")
                print(f"💾 Database size: {size_mb:.2f} MB")
                print(f"📁 Location: {os.path.abspath(dmnd_file)}")
                print("="*50)
                
                # Test the database with a real sequence
                print("\n🧪 Testing DIAMOND database with real sequence...")
                
                # Get a sample sequence from the FASTA
                with open(fasta_file, 'r') as f:
                    lines = f.readlines()
                    # Find first sequence (skip header)
                    test_seq = None
                    for line in lines[1:]:
                        if not line.startswith('>'):
                            test_seq = line.strip()
                            break
                
                if test_seq and len(test_seq) >= 5:
                    # Use first 10 characters or full sequence
                    test_query = test_seq[:min(10, len(test_seq))]
                    print(f"🧪 Test query: {test_query}")
                    
                    test_file = "test_query.fasta"
                    with open(test_file, 'w') as f:
                        f.write(f">test\n{test_query}\n")
                    
                    test_result = subprocess.run([
                        'diamond', 'blastp',
                        '--query', test_file,
                        '--db', output_prefix,
                        '--outfmt', '6',
                        '--max-target-seqs', '5',
                        '--id', '30'
                    ], capture_output=True, text=True, timeout=30)
                    
                    if test_result.returncode == 0 and test_result.stdout:
                        matches = len(test_result.stdout.strip().split('\n'))
                        print(f"✅ DIAMOND test successful! Found {matches} matches")
                        print(f"📊 Sample output:\n{test_result.stdout[:200]}")
                    else:
                        print("⚠️  DIAMOND test returned no matches")
                        if test_result.stderr:
                            print(f"   Error: {test_result.stderr}")
                    
                    # Cleanup
                    if os.path.exists(test_file):
                        os.remove(test_file)
                
                print("\n✨ DIAMOND setup complete!")
                print("📝 You can now use this database for peptide similarity searches")
            else:
                print("❌ Error: DIAMOND database file was not created")
                print(result.stderr)
        else:
            print("❌ Error creating DIAMOND database:")
            print(result.stderr)
    
    except subprocess.TimeoutExpired:
        print("❌ Error: DIAMOND makedb command timed out")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    # Get database file from command line or use default
    if len(sys.argv) > 1:
        db_file = sys.argv[1]
    else:
        db_file = 'tmrna.db'
    
    # Get output prefix from command line or use default
    if len(sys.argv) > 2:
        output_prefix = sys.argv[2]
    else:
        output_prefix = 'peptide_db'
    
    # Make sure we're using absolute paths
    db_file = os.path.abspath(db_file)
    
    create_diamond_database(db_file, output_prefix)