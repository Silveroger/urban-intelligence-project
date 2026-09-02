import { createClient, SupabaseClient } from '@supabase/supabase-js';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || '';
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || '';

export const isSupabaseConfigured = Boolean(
  supabaseUrl &&
  supabaseAnonKey &&
  supabaseUrl !== 'https://your-project.supabase.co' &&
  supabaseAnonKey !== 'your-supabase-anon-key'
);

// Graceful dummy fallback client if credentials are not configured yet
export const supabase: SupabaseClient = createClient(
  isSupabaseConfigured ? supabaseUrl : 'https://placeholder.supabase.co',
  isSupabaseConfigured ? supabaseAnonKey : 'placeholder-anon-key',
  {
    auth: {
      persistSession: false,
      autoRefreshToken: false,
    },
  }
);

export async function testSupabaseConnection(): Promise<{
  connected: boolean;
  message: string;
  latencyMs?: number;
}> {
  if (!isSupabaseConfigured) {
    return {
      connected: false,
      message: 'Supabase credentials not set in .env (VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY)',
    };
  }

  const start = performance.now();
  try {
    const { error } = await supabase.from('gps_records').select('id').limit(1);
    const latency = Math.round(performance.now() - start);

    if (error) {
      // If table doesn't exist yet, explain clearly
      if (error.code === '42P01' || error.message?.includes('relation "public.gps_records" does not exist') || error.message?.includes('not found')) {
        return {
          connected: true,
          message: 'Connected to Supabase! Table `gps_records` needs to be created (run migration SQL).',
          latencyMs: latency,
        };
      }
      return {
        connected: false,
        message: `Supabase Error (${error.code || 'UNKNOWN'}): ${error.message}`,
        latencyMs: latency,
      };
    }

    return {
      connected: true,
      message: 'Successfully connected to Supabase `gps_records` table.',
      latencyMs: latency,
    };
  } catch (err: unknown) {
    const errMsg = err instanceof Error ? err.message : 'Network error communicating with Supabase.';
    return {
      connected: false,
      message: errMsg,
    };
  }
}
