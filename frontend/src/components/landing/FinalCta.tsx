import Link from "next/link";

export function FinalCta({ hasSession }: { hasSession: boolean }) {
  return (
    <section className="py-32 bg-primary text-on-primary text-center px-6">
      <div className="max-w-3xl mx-auto flex flex-col items-center">
        <h2 className="font-serif text-5xl md:text-6xl font-semibold tracking-tight mb-8">
          Your documents are waiting.
        </h2>
        <p className="text-xl opacity-80 font-sans mb-12">
          Read them. Question them. Understand them.
        </p>
        
        {hasSession ? (
          <Link
            href="/library"
            className="px-8 py-4 bg-on-primary text-primary rounded-full font-medium text-lg hover:opacity-90 transition-opacity flex items-center gap-2"
          >
            Go to Workspace
            <span className="material-symbols-outlined">arrow_forward</span>
          </Link>
        ) : (
          <div className="flex flex-col sm:flex-row gap-4">
            <Link
              href="/signup"
              className="px-8 py-4 bg-on-primary text-primary rounded-full font-medium text-lg hover:opacity-90 transition-opacity flex items-center justify-center gap-2"
            >
              Get Started
              <span className="material-symbols-outlined">arrow_forward</span>
            </Link>
            <Link
              href="/login"
              className="px-8 py-4 border border-on-primary/30 text-on-primary rounded-full font-medium text-lg hover:bg-on-primary/10 transition-colors flex items-center justify-center"
            >
              Sign In
            </Link>
          </div>
        )}
      </div>
    </section>
  );
}

