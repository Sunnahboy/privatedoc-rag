"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { LogoutButton } from "@/components/auth/LogoutButton";

type Theme = "light" | "sepia" | "matcha" | "dark" | "oled";

const STORAGE_KEY = "privatedoc.theme";

const THEMES: { id: Theme; label: string }[] = [
  { id: "light", label: "Light" },
  { id: "sepia", label: "Sepia" },
  { id: "matcha", label: "Matcha" },
  { id: "dark", label: "Dark" },
  { id: "oled", label: "OLED" },
];

const ANCHORS = [
  { id: "overview", label: "OVERVIEW" },
  { id: "read", label: "READ" },
  { id: "ask", label: "ASK" },
  { id: "connect", label: "CONNECT" },
  { id: "memory", label: "MEMORY" },
  { id: "privacy", label: "PRIVACY" },
  { id: "themes", label: "THEMES" },
];

export function Navigation({ hasSession }: { hasSession: boolean }) {
  const [activeTheme, setActiveTheme] = useState<Theme>("light");

  useEffect(() => {
    const saved = window.localStorage.getItem(STORAGE_KEY) as Theme | null;
    if (saved && THEMES.some((t) => t.id === saved)) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setActiveTheme(saved);
      document.documentElement.dataset.theme = saved;
    }
  }, []);

  const changeTheme = (nextTheme: Theme) => {
    setActiveTheme(nextTheme);
    // eslint-disable-next-line
    document.documentElement.dataset.theme = nextTheme;
    window.localStorage.setItem(STORAGE_KEY, nextTheme);
  };

  const scrollToTop = (e: React.MouseEvent) => {
    e.preventDefault();
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <nav className="fixed top-0 left-0 right-0 h-16 border-b border-outline-variant/20 bg-surface/80 backdrop-blur-md z-50 flex items-center justify-between px-6">
      {/* Left: Brand mark */}
      <div className="flex items-center">
        <a
          href="#"
          onClick={scrollToTop}
          className="flex items-center gap-2 group transition-opacity hover:opacity-80"
        >
          <div className="w-8 h-8 bg-primary text-on-primary rounded flex items-center justify-center font-serif font-bold">
            P
          </div>
          <span className="font-serif font-semibold text-lg text-foreground tracking-wide">
            PrivateDoc
          </span>
        </a>
      </div>

      {/* Center: Section Anchors */}
      <div className="hidden lg:flex items-center gap-6">
        {ANCHORS.map((anchor) => (
          <a
            key={anchor.id}
            href={`#${anchor.id}`}
            className="text-xs tracking-wider font-medium text-muted hover:text-foreground transition"
          >
            {anchor.label}
          </a>
        ))}
      </div>

      {/* Right: Theme Switcher & CTAs */}
      <div className="flex items-center gap-4">
        <div className="hidden md:flex items-center bg-surface-elevated border border-outline-variant/30 rounded-full p-1 shadow-sm">
          {THEMES.map((t) => (
            <button
              key={t.id}
              onClick={() => changeTheme(t.id)}
              className={`px-3 py-1 text-xs font-medium rounded-full transition-colors ${
                activeTheme === t.id
                  ? "bg-primary text-on-primary shadow-sm"
                  : "text-muted hover:text-foreground"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {hasSession ? (
          <>
            <Link
              href="/library"
              className="px-4 py-2 bg-primary text-on-primary rounded-md text-sm font-medium hover:opacity-90 transition-opacity flex items-center gap-1.5"
            >
              Open Library <span aria-hidden="true">&rarr;</span>
            </Link>
            <LogoutButton />
          </>
        ) : (
          <>
            <Link
              href="/login"
              className="text-sm font-medium text-muted hover:text-foreground transition-colors px-3 py-2"
            >
              Sign In
            </Link>
            <Link
              href="/signup"
              className="px-4 py-2 bg-primary text-on-primary rounded-md text-sm font-medium hover:opacity-90 transition-opacity flex items-center gap-1.5"
            >
              Get Started <span aria-hidden="true">&rarr;</span>
            </Link>
          </>
        )}
      </div>
    </nav>
  );
}
