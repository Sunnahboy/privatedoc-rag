import Link from "next/link";
import { HeroPreview } from "./HeroPreview";
import { FloatingBook } from "./FloatingBook";

export function Hero({ hasSession }: { hasSession: boolean }) {
  return (
    <section id="overview" className="relative pt-24 pb-16 md:pt-32 md:pb-24 overflow-hidden">
      <div className="max-w-[1200px] mx-auto px-6 md:px-12 flex flex-col items-center text-center">
        <h1 className="font-serif text-5xl md:text-7xl font-semibold tracking-tight text-foreground max-w-4xl mb-6 leading-[1.1]">
          Read deeper. <br className="hidden md:block" /> Understand more.
        </h1>
        <p className="text-xl md:text-2xl text-muted max-w-2xl mb-8 font-sans">
          Your private workspace for reading, searching, and understanding documents.
        </p>

        <div className="flex items-center gap-4 mb-16">
          {hasSession ? (
            <Link
              href="/library"
              className="px-6 py-3 bg-primary text-on-primary rounded-full font-medium hover:opacity-90 transition-opacity"
            >
              Go to Workspace
            </Link>
          ) : (
            <>
              <Link
                href="/signup"
                className="px-6 py-3 bg-primary text-on-primary rounded-full font-medium hover:opacity-90 transition-opacity"
              >
                Get Started
              </Link>
              <Link
                href="/login"
                className="px-6 py-3 bg-surface-container text-foreground rounded-full font-medium hover:bg-surface-container-low transition-colors border border-outline-variant"
              >
                Sign In
              </Link>
            </>
          )}
        </div>

        {/* Hero Visual: A mock representation of the app */}
        <div className="w-full max-w-5xl relative min-h-[400px] md:min-h-[600px] flex perspective-1000 z-10">
          <HeroPreview />
        </div>
      </div>

      {/* Decorative 3D Books */}
      <FloatingBook position="left" delay={0} />
      <FloatingBook position="right" delay={1.5} />
    </section>
  );
}

