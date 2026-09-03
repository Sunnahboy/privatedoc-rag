"use client";

import { useEffect, useState } from "react";

type Theme = "light" | "dark" | "oled" | "sepia" | "matcha";

const STORAGE_KEY = "privatedoc.theme";

export default function ThemeSwitcher() {
  const [theme, setTheme] = useState<Theme>("light");

  useEffect(() => {
    const saved = window.localStorage.getItem(STORAGE_KEY);
    if (saved === "matcha" || saved === "dark" || saved === "oled" || saved === "sepia" || saved === "light") {
      setTheme(saved);
      document.documentElement.dataset.theme = saved;
    }
  }, []);

  const changeTheme = (nextTheme: Theme) => {
    setTheme(nextTheme);
    document.documentElement.dataset.theme = nextTheme;
    window.localStorage.setItem(STORAGE_KEY, nextTheme);
  };

  return (
    <label className="inline-flex items-center gap-2 rounded-md border border-outline-variant/30 bg-surface px-2.5 py-1.5 text-xs text-on-surface-variant">
      <span className="material-symbols-outlined text-[16px]" aria-hidden="true">palette</span>
      <span className="sr-only">Theme</span>
      <select aria-label="Theme" value={theme} onChange={(event) => changeTheme(event.target.value as Theme)} className="theme-select bg-transparent text-xs text-on-surface outline-none">
        <option value="light">Light</option>
        <option value="dark">Dark</option>
        <option value="oled">OLED Black</option>
        <option value="sepia">Sepia</option>
        <option value="matcha">Matcha</option>
      </select>
    </label>
  );
}
