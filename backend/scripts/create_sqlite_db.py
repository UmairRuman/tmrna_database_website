# ============================================
# FILE: backend/scripts/create_sqlite_db.py
# ============================================
"""
Create SQLite database from CSV file with FTS5 full-text search
Run this script once to generate tmrna.db
"""

import sqlite3
import csv
import os
import sys

def create_database(csv_file_path, db_file_path='tmrna.db'):
    """
    Create SQLite database from CSV file
    
    Args:
        csv_file_path: Path to the CSV file with tmRNA data
        db_file_path: Output database file path
    """
    
    print("🚀 Starting SQLite database creation...")
    print(f"📁 Input CSV: {csv_file_path}")
    print(f"💾 Output DB: {db_file_path}")
    
    # Remove existing database if it exists
    if os.path.exists(db_file_path):
        os.remove(db_file_path)
        print("🗑️  Removed existing database")
    
    # Create connection
    conn = sqlite3.connect(db_file_path)
    cursor = conn.cursor()
    
    # Create main table
    print("📊 Creating main table...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tmrna_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            identifier TEXT NOT NULL UNIQUE,
            tag_peptide TEXT NOT NULL,
            codons TEXT NOT NULL,
            tmrna_sequence TEXT NOT NULL,
            organism_name TEXT,
            accession TEXT,
            peptide_length INTEGER,
            sequence_length INTEGER
        )
    ''')
    
    # Create indexes for fast lookups
    print("🔍 Creating indexes...")
    cursor.execute('CREATE INDEX idx_identifier ON tmrna_data(identifier)')
    cursor.execute('CREATE INDEX idx_organism ON tmrna_data(organism_name)')
    cursor.execute('CREATE INDEX idx_accession ON tmrna_data(accession)')
    
    # Create FTS5 virtual table for full-text search (SUPER FAST!)
    print("⚡ Creating FTS5 full-text search index...")
    cursor.execute('''
        CREATE VIRTUAL TABLE IF NOT EXISTS tmrna_fts USING fts5(
            identifier,
            organism_name,
            accession,
            content='tmrna_data',
            content_rowid='id'
        )
    ''')
    
    # Import CSV data
    print("📥 Importing CSV data...")
    
    try:
        with open(csv_file_path, 'r', encoding='utf-8') as f:
            # Try to detect the delimiter
            sample = f.read(1024)
            f.seek(0)
            
            # Detect if comma or tab separated
            if '\t' in sample:
                reader = csv.DictReader(f, delimiter='\t')
            else:
                reader = csv.DictReader(f)
            
            # Get field names
            fieldnames = reader.fieldnames
            print(f"📋 CSV columns detected: {fieldnames}")
            
            # Map common column name variations
            col_mapping = {
                'identifier': ['Identifier', 'identifier', 'ID', 'id'],
                'tag_peptide': ['Tag Peptide', 'tag_peptide', 'TagPeptide', 'peptide'],
                'codons': ['Codons', 'codons', 'codon'],
                'tmrna_sequence': ['tmRNA Sequence', 'tmrna_sequence', 'sequence', 'tmRNA_Sequence']
            }
            
            # Find actual column names
            actual_cols = {}
            for target, variations in col_mapping.items():
                for var in variations:
                    if var in fieldnames:
                        actual_cols[target] = var
                        break
            
            if len(actual_cols) < 4:
                print(f"❌ Error: Could not find all required columns!")
                print(f"   Found: {actual_cols}")
                print(f"   Expected: identifier, tag_peptide, codons, tmrna_sequence")
                sys.exit(1)
            
            print(f"✅ Column mapping: {actual_cols}")
            
            # Reset file pointer
            f.seek(0)
            if '\t' in sample:
                reader = csv.DictReader(f, delimiter='\t')
            else:
                reader = csv.DictReader(f)
            
            count = 0
            batch = []
            batch_size = 1000
            
            for row in reader:
                try:
                    identifier = row[actual_cols['identifier']].strip()
                    tag_peptide = row[actual_cols['tag_peptide']].strip()
                    codons = row[actual_cols['codons']].strip()
                    tmrna_sequence = row[actual_cols['tmrna_sequence']].strip()
                    
                    # Extract organism name (usually last word in identifier)
                    parts = identifier.split()
                    organism = parts[-1] if len(parts) > 1 else ''
                    
                    # Extract accession (usually first part before _)
                    accession = identifier.split('_')[0] if '_' in identifier else identifier
                    
                    # Calculate lengths
                    peptide_length = len(tag_peptide.replace('?', '').replace('*', ''))
                    sequence_length = len(tmrna_sequence)
                    
                    batch.append((
                        identifier,
                        tag_peptide,
                        codons,
                        tmrna_sequence,
                        organism,
                        accession,
                        peptide_length,
                        sequence_length
                    ))
                    
                    count += 1
                    
                    # Insert in batches for performance
                    if len(batch) >= batch_size:
                        cursor.executemany('''
                            INSERT INTO tmrna_data 
                            (identifier, tag_peptide, codons, tmrna_sequence, 
                             organism_name, accession, peptide_length, sequence_length)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ''', batch)
                        conn.commit()
                        batch = []
                        print(f"   Imported {count} records...", end='\r')
                
                except KeyError as e:
                    print(f"\n⚠️  Warning: Skipping row due to missing column: {e}")
                    continue
                except Exception as e:
                    print(f"\n⚠️  Warning: Error processing row: {e}")
                    continue
            
            # Insert remaining batch
            if batch:
                cursor.executemany('''
                    INSERT INTO tmrna_data 
                    (identifier, tag_peptide, codons, tmrna_sequence, 
                     organism_name, accession, peptide_length, sequence_length)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', batch)
                conn.commit()
            
            print(f"\n✅ Successfully imported {count} records!")
    
    except FileNotFoundError:
        print(f"❌ Error: CSV file not found: {csv_file_path}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error reading CSV: {e}")
        sys.exit(1)
    
    # Populate FTS5 index
    print("🔍 Populating full-text search index...")
    cursor.execute('''
        INSERT INTO tmrna_fts(rowid, identifier, organism_name, accession)
        SELECT id, identifier, organism_name, accession FROM tmrna_data
    ''')
    conn.commit()
    
    # Get statistics
    cursor.execute('SELECT COUNT(*) FROM tmrna_data')
    total_records = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(DISTINCT organism_name) FROM tmrna_data WHERE organism_name != ""')
    unique_organisms = cursor.fetchone()[0]
    
    # Get database file size
    db_size = os.path.getsize(db_file_path) / (1024 * 1024)  # MB
    
    # Close connection
    conn.close()
    
    print("\n" + "="*50)
    print("✅ DATABASE CREATED SUCCESSFULLY!")
    print("="*50)
    print(f"📊 Total Records: {total_records:,}")
    print(f"🧬 Unique Organisms: {unique_organisms:,}")
    print(f"💾 Database Size: {db_size:.2f} MB")
    print(f"📁 Location: {os.path.abspath(db_file_path)}")
    print("="*50)
    
    # Test query
    print("\n🧪 Testing database with sample query...")
    conn = sqlite3.connect(db_file_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT identifier, organism_name FROM tmrna_data LIMIT 5")
    print("\nSample records:")
    for row in cursor.fetchall():
        print(f"  • {row[0]}")
    
    conn.close()
    
    print("\n✨ Database is ready to use!")
    print(f"📝 You can now:")
    print(f"   1. Copy {db_file_path} to your frontend/public/ folder")
    print(f"   2. Use it with sql.js in the browser")
    print(f"   3. Query it directly with SQLite tools")

if __name__ == '__main__':
    # Check command line arguments
    if len(sys.argv) > 1:
        csv_file = sys.argv[1]
    else:
        # Look for common CSV file names
        possible_files = [
            'tmrna_data.csv',
            'data.csv',
            '../data/tmrna_data.csv',
            '../../data/tmrna_data.csv'
        ]
        
        csv_file = None
        for f in possible_files:
            if os.path.exists(f):
                csv_file = f
                break
        
        if not csv_file:
            print("❌ Error: CSV file not found!")
            print("\nUsage:")
            print("  python create_sqlite_db.py <path_to_csv_file>")
            print("\nOr place your CSV file in one of these locations:")
            for f in possible_files:
                print(f"  • {f}")
            sys.exit(1)
    
    # Create database
    create_database(csv_file)