import { useState, useEffect } from 'react';

const setCookie = (name: string, value: string) => {
  document.cookie = `${name}=${value};path=/`;
};
const getCookie = (name: string) => {
  const v = document.cookie.match('(^|;) ?' + name + '=([^;]*)(;|$)');
  return v ? v[2] : null;
};

export function usePreferences() {
  const [lang, setLangState] = useState<'en' | 'hi'>(() => (getCookie('mnit_lang') as 'en' | 'hi') || 'en');
  const [fontSize, setFontSizeState] = useState<number>(() => parseInt(getCookie('mnit_fontSize') || '0', 10));

  const setLang = (l: 'en' | 'hi') => {
    setLangState(l);
    setCookie('mnit_lang', l);
  };

  const setFontSize = (val: number | 'reset' | 'inc' | 'dec') => {
    let newVal = fontSize;
    if (val === 'reset') newVal = 0;
    else if (val === 'inc') newVal = Math.min(2, fontSize + 1);
    else if (val === 'dec') newVal = Math.max(-2, fontSize - 1);
    else newVal = val;
    
    setFontSizeState(newVal);
    setCookie('mnit_fontSize', newVal.toString());
  };

  useEffect(() => {
    const root = document.documentElement;
    root.style.fontSize = `${16 + (fontSize * 2)}px`;
  }, [fontSize]);

  // Sync across tabs/ports
  useEffect(() => {
    const interval = setInterval(() => {
      const cLang = (getCookie('mnit_lang') as 'en' | 'hi') || 'en';
      const cFont = parseInt(getCookie('mnit_fontSize') || '0', 10);
      if (cLang !== lang) setLangState(cLang);
      if (cFont !== fontSize) setFontSizeState(cFont);
    }, 1000);
    return () => clearInterval(interval);
  }, [lang, fontSize]);

  return { lang, setLang, fontSize, setFontSize };
}
