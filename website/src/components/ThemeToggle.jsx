import React, { useEffect, useState } from 'react';

export default function ThemeToggle() {
  const [dark, setDark] = useState(false);
  useEffect(() => setDark(document.documentElement.classList.contains('dark')), []);
  function toggle() {
    const next = !dark;
    setDark(next);
    document.documentElement.classList.toggle('dark', next);
    localStorage.setItem('a2a-theme', next ? 'dark' : 'light');
  }
  return <button className="theme-toggle" type="button" onClick={toggle} aria-label={`Use ${dark ? 'light' : 'dark'} theme`}>{dark ? 'Light' : 'Dark'}</button>;
}
