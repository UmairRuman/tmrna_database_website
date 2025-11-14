# ============================================
# FILE: backend/scripts/create_blat_db.py
# ============================================
"""
Create BLAT database for codon similarity search
BLAT uses FASTA files directly, no separate indexing needed
"""

import sqlite3
import os
import sys

def create_blat_database(db_file='tmrna.db', output_file='codons.fasta'):
    """
    Create FASTA file for BLAT codon similarity search
    
    Args:
        db_file: Path to SQLite database
        output_file: Output FASTA file
    """
    
    print("🚀 Creating BLAT database for codon similarity search...")
    
    # Check if SQLite database exists
    if not os.path.exists(db_file):
        print(f"❌ Error: SQLite database not found: {db_file}")
        print("   Please run create_sqlite_db.py first!")
        sys.exit(1)
    
    # Connect to SQLite database
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    # Fetch all codon sequences
    print("📥 Extracting codon sequences from database...")
    cursor.execute('''
        SELECT identifier, codons 
        FROM tmrna_data 
        ORDER BY id
    ''')
    
    sequences = cursor.fetchall()
    conn.close()
    
    print(f"✅ Found {len(sequences):,} codon sequences")
    
    # Create FASTA file
    print(f"📝 Writing FASTA file: {output_file}")
    
    with open(output_file, 'w') as f:
        for identifier, codons in sequences:
            # Clean codon sequence (remove hyphens and spaces)
            clean_codons = codons.replace('-', '').replace(' ', '').strip().lower()
            
            if clean_codons:  # Only write if sequence is not empty
                f.write(f">{identifier}\n{clean_codons}\n")
    
    file_size_mb = os.path.getsize(output_file) / (1024 * 1024)
    
    print("\n" + "="*50)
    print("✅ BLAT DATABASE CREATED SUCCESSFULLY!")
    print("="*50)
    print(f"📊 Sequences indexed: {len(sequences):,}")
    print(f"💾 File size: {file_size_mb:.2f} MB")
    print(f"📁 Location: {os.path.abspath(output_file)}")
    print("="*50)
    
    print("\n✨ BLAT setup complete!")
    print("📝 You can now use this file for codon similarity searches")
    print("\n💡 Note: BLAT uses FASTA files directly, no separate indexing needed")


if __name__ == '__main__':
    # Get database file from command line or use default
    if len(sys.argv) > 1:
        db_file = sys.argv[1]
    else:
        db_file = 'tmrna.db'
    
    # Get output file from command line or use default
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    else:
        output_file = 'codons.fasta'
    
    # Make sure we're using absolute paths
    db_file = os.path.abspath(db_file)
    
    create_blat_database(db_file, output_file)