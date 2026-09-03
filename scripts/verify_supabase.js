/**
 * SIH 26124 — Supabase Connection Diagnostic & Verifier
 * Run with: node scripts/verify_supabase.js
 */

const https = require('https');
const fs = require('fs');
const path = require('path');

// 1. Read .env
const envPath = path.resolve(__dirname, '..', '.env');
let supabaseUrl = '';
let supabaseKey = '';

if (fs.existsSync(envPath)) {
  const envContent = fs.readFileSync(envPath, 'utf8');
  for (const line of envContent.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (trimmed.startsWith('VITE_SUPABASE_URL=')) {
      supabaseUrl = trimmed.split('=')[1].trim();
    } else if (trimmed.startsWith('VITE_SUPABASE_ANON_KEY=')) {
      supabaseKey = trimmed.split('=')[1].trim();
    }
  }
}

console.log('=' .repeat(65));
console.log(' SIH 26124 — Supabase Connection & Schema Diagnostic');
console.log('=' .repeat(65));
console.log(`Supabase URL: ${supabaseUrl || 'NOT FOUND'}`);
console.log(`Anon Key:     ${supabaseKey ? supabaseKey.slice(0, 20) + '...' : 'NOT FOUND'}\n`);

if (!supabaseUrl || !supabaseKey) {
  console.error('[!] Error: Supabase credentials missing in .env');
  process.exit(1);
}

function checkTable(tableName) {
  return new Promise((resolve) => {
    const parsed = new URL(`${supabaseUrl}/rest/v1/${tableName}?select=*&limit=1`);
    const options = {
      hostname: parsed.hostname,
      port: 443,
      path: parsed.pathname + parsed.search,
      method: 'GET',
      headers: {
        'apikey': supabaseKey,
        'Authorization': `Bearer ${supabaseKey}`,
      },
    };

    const startTime = Date.now();
    const req = https.request(options, (res) => {
      let data = '';
      res.on('data', (d) => (data += d));
      res.on('end', () => {
        const latency = Date.now() - startTime;
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve({ table: tableName, ok: true, status: res.statusCode, latency, message: 'Active & Accessible' });
        } else {
          resolve({ table: tableName, ok: false, status: res.statusCode, latency, message: data });
        }
      });
    });

    req.on('error', (e) => {
      resolve({ table: tableName, ok: false, status: 0, latency: 0, message: e.message });
    });
    req.end();
  });
}

async function run() {
  const tables = ['gps_records', 'observations', 'incidents', 'road_segments'];
  console.log('[*] Testing Supabase REST API tables...\n');

  for (const table of tables) {
    const res = await checkTable(table);
    const badge = res.ok ? '[OK]    ' : '[NOTICE]';
    console.log(`${badge} ${table.padEnd(16)} | Status: ${res.status} | Latency: ${res.latency}ms | ${res.message}`);
  }

  console.log('\n' + '=' .repeat(65));
  console.log(' Diagnostic Complete.');
  console.log('=' .repeat(65));
}

run();
