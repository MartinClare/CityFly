"use client";

import { useEffect, useState } from "react";

export type ThemeMode = "night" | "day";

const STORAGE_KEY = "citysight-theme";

function applyTheme(mode: ThemeMode) {
  document.documentElement.setAttribute("data-theme", mode);
}

export function ThemeToggle() {
  const [mode, setMode] = useState<ThemeMode>("night");
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const saved = window.localStorage.getItem(STORAGE_KEY);
    const next: ThemeMode = saved === "day" || saved === "night" ? saved : "night";
    applyTheme(next);
    setMode(next);
    setReady(true);
  }, []);

  function toggle() {
    const next: ThemeMode = mode === "night" ? "day" : "night";
    applyTheme(next);
    setMode(next);
    window.localStorage.setItem(STORAGE_KEY, next);
  }

  return (
    <button
      type="button"
      className="theme-toggle"
      onClick={toggle}
      aria-label={mode === "night" ? "切換日間模式" : "切換夜間模式"}
      title={mode === "night" ? "日間模式" : "夜間模式"}
      data-ready={ready ? "true" : "false"}
    >
      <span className="theme-toggle-track" aria-hidden="true">
        <span className="theme-toggle-knob" data-mode={mode} />
      </span>
      <span className="theme-toggle-label">{mode === "night" ? "日間" : "夜間"}</span>
    </button>
  );
}
