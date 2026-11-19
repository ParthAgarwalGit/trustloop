import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// `base` is set from BASE_PATH so the same build works on Vercel/Netlify (root)
// and on GitHub Pages (served from /<repo>/).
export default defineConfig({
  plugins: [react()],
  base: process.env.BASE_PATH ?? "/",
  // Honour PORT when the host assigns one. Without this Vite silently picks the
  // next free port, and anything expecting it on the assigned port fails to connect.
  server: process.env.PORT
    ? { port: Number(process.env.PORT), strictPort: true }
    : undefined,
  // SOURCEMAP=false for public hosting: maps expose the commented source, which
  // explains the planted errors to anyone who opens devtools.
  build: { outDir: "dist", sourcemap: process.env.SOURCEMAP !== "false" },
});
