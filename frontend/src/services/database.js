// ============================================
// FILE: frontend/src/services/database.js
// ============================================
import initSqlJs from 'sql.js';

class DatabaseService {
  constructor() {
    this.db = null;
    this.loading = false;
    this.error = null;
  }

  async initialize() {
    if (this.db) {
      return this.db;
    }

    if (this.loading) {
      while (this.loading) {
        await new Promise(resolve => setTimeout(resolve, 100));
      }
      return this.db;
    }

    this.loading = true;
    this.error = null;

    try {
      console.log('🚀 Initializing SQL.js...');
      
      const SQL = await initSqlJs({
        locateFile: file => `https://sql.js.org/dist/${file}`
      });

      console.log('📥 Loading database file...');
      
      const response = await fetch('/tmrna.db');
      
      if (!response.ok) {
        throw new Error(`Failed to load database: ${response.statusText}`);
      }

      const arrayBuffer = await response.arrayBuffer();
      const uintArray = new Uint8Array(arrayBuffer);

      console.log(`✅ Database loaded: ${(arrayBuffer.byteLength / 1024 / 1024).toFixed(2)} MB`);

      this.db = new SQL.Database(uintArray);

      const testResult = this.db.exec('SELECT COUNT(*) as count FROM tmrna_data');
      const count = testResult[0].values[0][0];
      console.log(`✅ Database ready with ${count.toLocaleString()} records`);

      this.loading = false;
      return this.db;

    } catch (error) {
      this.error = error.message;
      this.loading = false;
      console.error('❌ Database initialization failed:', error);
      throw error;
    }
  }

  searchKeyword(query, limit = 500) {
    if (!this.db) {
      throw new Error('Database not initialized');
    }

    const cleanQuery = query.trim();
    if (!cleanQuery) {
      return { results: [], total: 0 };
    }

    try {
      const sqlQuery = `
        SELECT * FROM tmrna_data
        WHERE identifier LIKE ?
           OR organism_name LIKE ?
        LIMIT ${limit}
      `;

      const result = this.db.exec(sqlQuery, [
        `%${cleanQuery}%`,
        `%${cleanQuery}%`
      ]);

      if (!result.length) {
        return { results: [], total: 0 };
      }

      const columns = result[0].columns;
      const values = result[0].values;

      const results = values.map(row => {
        const obj = {};
        columns.forEach((col, idx) => {
          obj[col] = row[idx];
        });
        return obj;
      });

      return {
        results,
        total: results.length
      };

    } catch (error) {
      console.error('Search error:', error);
      throw new Error(`Search failed: ${error.message}`);
    }
  }

  getAutocomplete(query, limit = 10) {
    if (!this.db) {
      throw new Error('Database not initialized');
    }

    const cleanQuery = query.trim();
    if (!cleanQuery || cleanQuery.length < 2) {
      return [];
    }

    try {
      const sqlQuery = `
        SELECT DISTINCT organism_name
        FROM tmrna_data
        WHERE organism_name LIKE ?
          AND organism_name != ''
        LIMIT ${limit}
      `;

      const result = this.db.exec(sqlQuery, [`${cleanQuery}%`]);

      if (!result.length) {
        return [];
      }

      return result[0].values.map(row => row[0]);

    } catch (error) {
      console.error('Autocomplete error:', error);
      return [];
    }
  }

  getStats() {
    if (!this.db) {
      throw new Error('Database not initialized');
    }

    try {
      const totalResult = this.db.exec('SELECT COUNT(*) FROM tmrna_data');
      const total = totalResult[0].values[0][0];

      const orgResult = this.db.exec(
        "SELECT COUNT(DISTINCT organism_name) FROM tmrna_data WHERE organism_name != ''"
      );
      const uniqueOrganisms = orgResult[0].values[0][0];

      return {
        totalRecords: total,
        uniqueOrganisms
      };

    } catch (error) {
      console.error('Stats error:', error);
      return {
        totalRecords: 0,
        uniqueOrganisms: 0
      };
    }
  }
}

export const databaseService = new DatabaseService();
