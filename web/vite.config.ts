import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  // Relative asset URLs: the static export opens from a subdirectory or file://.
  base: "./",
  plugins: [react()],
  build: {
    outDir: "dist",
    sourcemap: false,
    // A single classic script so the export opens straight from file://
    // (browsers block ES modules on the file: scheme).
    rolldownOptions: {
      output: { format: "iife", inlineDynamicImports: true },
    },
  },
});
