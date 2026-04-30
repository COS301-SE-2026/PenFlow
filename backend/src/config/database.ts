import { createClient, SupabaseClient } from "@supabase/supabase-js";
import { Request } from "express";
import { env } from "./env";

export let supabase: SupabaseClient;

export function initializeDatabase(): void {
  if (!env.SUPABASE_URL || !env.SUPABASE_ANON_KEY) {
    console.warn("Supabase credentials not present. Database connection cannot be established.");
    return;
  }

  supabase = createClient(env.SUPABASE_URL, env.SUPABASE_ANON_KEY, {
    auth: {
      autoRefreshToken: false,
      persistSession: false,
    },
  });
}

export function getDatabase(): SupabaseClient {
  if (!supabase) {
    throw new Error("Database not initialized");
  }
  return supabase;
}

export function getSupabaseFromRequest(req?: Request): SupabaseClient {
  if (!env.SUPABASE_URL || !env.SUPABASE_ANON_KEY) {
    throw new Error("Supabase not configured");
  }

  const token = req?.headers.authorization?.replace("Bearer ", "");

  if (!token) {
    return getDatabase();
  }

  return createClient(env.SUPABASE_URL, env.SUPABASE_ANON_KEY, {
    global: {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    },
    auth: {
      autoRefreshToken: false,
      persistSession: false,
    },
  });
}
