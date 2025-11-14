# ============================================
# FILE: backend/scripts/create_diamond_db.py
# ============================================
"""
Create DIAMOND database for peptide similarity search
Requires: DIAMOND installed (download from https://github.com/bbuchfink/diamond)
"""

import sqlite3
import subprocess
import os
import sys

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
    
    # Create FASTA file
    fasta_file = f"{output_prefix}.fasta"
    print(f"📝 Writing FASTA file: {fasta_file}")
    
    with open(fasta_file, 'w') as f:
        for identifier, peptide in sequences:
            # Clean peptide sequence (remove ? and *)
            clean_peptide = peptide.replace('?', '').replace('*', '').strip()
            
            if clean_peptide:  # Only write if sequence is not empty
                f.write(f">{identifier}\n{clean_peptide}\n")
    
    print(f"✅ FASTA file created: {fasta_file}")
    
    # Create DIAMOND database
    print("🔨 Building DIAMOND database (this may take 1-2 minutes)...")
    
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
                print(f"📊 Sequences indexed: {len(sequences):,}")
                print(f"💾 Database size: {size_mb:.2f} MB")
                print(f"📁 Location: {os.path.abspath(dmnd_file)}")
                print("="*50)
                
                # Test the database
                print("\n🧪 Testing DIAMOND database...")
                test_query = ">test\nANDNYAPVRAAA\n"
                test_file = "test_query.fasta"
                
                with open(test_file, 'w') as f:
                    f.write(test_query)
                
                test_result = subprocess.run([
                    'diamond', 'blastp',
                    '--query', test_file,
                    '--db', output_prefix,
                    '--out', 'test_output.txt',
                    '--outfmt', '6',
                    '--max-target-seqs', '5'
                ], capture_output=True, text=True, timeout=30)
                
                if test_result.returncode == 0:
                    print("✅ DIAMOND database test successful!")
                    
                    # Show sample results
                    if os.path.exists('test_output.txt'):
                        with open('test_output.txt', 'r') as f:
                            lines = f.readlines()
                            if lines:
                                print(f"📊 Sample search found {len(lines)} matches")
                        os.remove('test_output.txt')
                else:
                    print("⚠️  Warning: DIAMOND test search failed")
                    print(test_result.stderr)
                
                # Cleanup test files
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