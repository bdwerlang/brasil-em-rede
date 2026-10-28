interface BraccRuntimeConfig {
  apiBaseUrl?: string;
  publicMode?: boolean;
  patternsEnabled?: boolean;
}

declare global {
  interface Window {
    __BRACC_CONFIG__?: BraccRuntimeConfig;
  }
}

export const IS_PUBLIC_MODE =
  window.__BRACC_CONFIG__?.publicMode ?? import.meta.env.VITE_PUBLIC_MODE === "true";
export const IS_PATTERNS_ENABLED =
  window.__BRACC_CONFIG__?.patternsEnabled ?? import.meta.env.VITE_PATTERNS_ENABLED === "true";
export const API_BASE_URL =
  window.__BRACC_CONFIG__?.apiBaseUrl ?? import.meta.env.VITE_API_URL ?? "";
