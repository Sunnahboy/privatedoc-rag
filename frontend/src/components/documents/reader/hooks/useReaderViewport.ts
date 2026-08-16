"use client";

import { useEffect, useState, type RefObject } from "react";

export default function useReaderViewport({
  shellRef,
  viewportRef,
}: {
  shellRef: RefObject<HTMLDivElement | null>;
  viewportRef: RefObject<HTMLDivElement | null>;
}) {
  const [viewportWidth, setViewportWidth] = useState(0);
  const [viewportHeight, setViewportHeight] = useState(0);
  const [scrollTop, setScrollTop] = useState(0);

  useEffect(() => {
    if (!shellRef.current) {
      return;
    }

    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (!entry) {
        return;
      }

      setViewportWidth(entry.contentRect.width);
      setViewportHeight(entry.contentRect.height);
    });

    observer.observe(shellRef.current);
    return () => observer.disconnect();
  }, [shellRef]);

  useEffect(() => {
    const viewport = viewportRef.current;
    if (!viewport) {
      return;
    }

    const handleScroll = () => {
      setScrollTop(viewport.scrollTop);
    };

    handleScroll();
    viewport.addEventListener("scroll", handleScroll, { passive: true });
    return () => viewport.removeEventListener("scroll", handleScroll);
  }, [viewportRef]);

  return {
    viewportWidth,
    viewportHeight,
    scrollTop,
  };
}
