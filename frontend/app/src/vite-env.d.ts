/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_SUPPORT_DONATE_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
