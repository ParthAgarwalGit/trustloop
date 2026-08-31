/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_DATA_SINK?: string;
  readonly VITE_SUPABASE_URL?: string;
  readonly VITE_SUPABASE_ANON_KEY?: string;
  readonly VITE_SUPABASE_TABLE?: string;
  readonly VITE_POST_ENDPOINT?: string;
  readonly VITE_COMPLETION_URL?: string;
  readonly VITE_COMPLETION_CODE?: string;
  readonly VITE_RESEARCHER_NAME?: string;
  readonly VITE_RESEARCHER_EMAIL?: string;
  readonly VITE_INSTITUTION?: string;
  readonly VITE_ETHICS_REF?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
