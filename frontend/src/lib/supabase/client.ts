import { createBrowserClient } from "@supabase/ssr";

function getSupabaseBrowserConfig() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const publishableKey = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;

  if (!url || !publishableKey) {
    throw new Error(
      "Missing NEXT_PUBLIC_SUPABASE_URL or NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY.",
    );
  }

  return { url, publishableKey };
}

/** Creates the cookie-backed Supabase browser client used by client components. */
export function createClient() {
  const { url, publishableKey } = getSupabaseBrowserConfig();
  return createBrowserClient(url, publishableKey);
}
