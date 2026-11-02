import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  // Relative asset URLs: the static export opens from a subdirectory or file://.
  base: "./",
  plugins: [react()],
  build: {
    outDir: "dist",
    sourcemap: false,
    // Keep the local font inside the classic-script export. A module script
    // has no document.currentScript, so relative CSS asset URLs lose /assets/.
    assetsInlineLimit: (filePath) => filePath.endsWith(".woff2") ? true : undefined,
    // A single classic script so the export opens straight from file://
    // (browsers block ES modules on the file: scheme).
    rolldownOptions: {
      output: { format: "iife", inlineDynamicImports: true },
    },
  },
});
