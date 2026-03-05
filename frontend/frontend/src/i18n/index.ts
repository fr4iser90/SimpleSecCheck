import { useState, useEffect } from 'react'
import en from './locales/en.json'
import zh from './locales/zh.json'
import de from './locales/de.json'

export type Language = 'en' | 'zh' | 'de'

export const languages: Record<Language, { name: string; flag: string }> = {
  en: { name: 'English', flag: '🇬🇧' },
  zh: { name: '中文', flag: '🇨🇳' },
  de: { name: 'Deutsch', flag: '🇩🇪' },
}

const translations = {
  en,
  zh,
  de,
}

function getLanguage(): Language {
  const saved = localStorage.getItem('i18n_language') as Language
  if (saved && saved in translations) {
    return saved
  }
  // Detect browser language
  if (typeof window !== 'undefined') {
    const browserLang = navigator.language.split('-')[0]
    if (browserLang === 'zh') return 'zh'
    if (browserLang === 'de') return 'de'
  }
  return 'en'
}

export function t(key: string, params?: Record<string, string | number>, lang?: Language): string {
  const language = lang || getLanguage()
  const keys = key.split('.')
  let value: any = translations[language]
  
  for (const k of keys) {
    if (value && typeof value === 'object' && k in value) {
      value = value[k]
    } else {
      // Fallback to English
      value = translations.en
      for (const fallbackKey of keys) {
        if (value && typeof value === 'object' && fallbackKey in value) {
          value = value[fallbackKey]
        } else {
          return key // Return key if not found
        }
      }
      break
    }
  }
  
  if (typeof value !== 'string') {
    return key
  }
  
  // Replace placeholders
  if (params) {
    return value.replace(/\{\{(\w+)\}\}/g, (match, paramKey) => {
      return params[paramKey]?.toString() || match
    })
  }
  
  return value
}

export function useTranslation() {
  const [language, setLanguageState] = useState<Language>(getLanguage)

  useEffect(() => {
    // Listen for language changes in other tabs/windows
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === 'i18n_language' && e.newValue && e.newValue in translations) {
        setLanguageState(e.newValue as Language)
      }
    }
    window.addEventListener('storage', handleStorageChange)
    return () => window.removeEventListener('storage', handleStorageChange)
  }, [])

  const setLanguage = (lang: Language) => {
    if (lang in translations) {
      setLanguageState(lang)
      localStorage.setItem('i18n_language', lang)
    }
  }

  return {
    t: (key: string, params?: Record<string, string | number>) => t(key, params, language),
    language,
    setLanguage,
    languages,
  }
}
