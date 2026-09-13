import { createClient } from "@/lib/supabase/server";
import { Navigation } from "@/components/landing/Navigation";
import { Hero } from "@/components/landing/Hero";
import { Features } from "@/components/landing/Features";
import { Architecture } from "@/components/landing/Architecture";
import { Themes } from "@/components/landing/Themes";
import { FinalCta } from "@/components/landing/FinalCta";

export default async function HomePage() {
  const supabase = await createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();

  const hasSession = !!session;

  return (
    <div className="min-h-screen bg-background text-foreground selection:bg-primary/20">
      <Navigation hasSession={hasSession} />
      <main>
        <Hero hasSession={hasSession} />
        <Features />
        <Architecture />
        <Themes />
        <FinalCta hasSession={hasSession} />
      </main>
      
      <footer className="py-8 text-center text-sm text-muted bg-surface-container-low border-t border-outline-variant/20">
        <p>&copy; {new Date().getFullYear()} PrivateDoc. All rights reserved.</p>
      </footer>
    </div>
  );
}
