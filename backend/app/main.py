if __name__ == '__main__':
    import sys
    
    # Determine which script to run based on filename
    script_name = os.path.basename(__file__)
    
    if 'diamond' in script_name.lower():
        # Get database file from command line or use default
        db_file = sys.argv[1] if len(sys.argv) > 1 else 'tmrna.db'
        create_diamond_database(db_file)
    elif 'blat' in script_name.lower():
        # Get database file from command line or use default
        db_file = sys.argv[1] if len(sys.argv) > 1 else 'tmrna.db'
        create_blat_database(db_file)
    else:
        print("Run this as either:")
        print("  python create_diamond_db.py [tmrna.db]")
        print("  python create_blat_db.py [tmrna.db]")



# ============================================
# Main
# ============================================

if __name__ == '__main__':
    import os
    
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