import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// `base` is set from BASE_PATH so the same build works on Vercel/Netlify (root)
// and on GitHub Pages (served from /<repo>/).
export default defineConfig({
  plugins: [react()],
  base: process.env.BASE_PATH ?? "/",
  build: { outDir: "dist", sourcemap: true },
});
