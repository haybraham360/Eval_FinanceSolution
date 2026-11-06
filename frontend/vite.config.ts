import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// EXPLORER_BASE is "/<repo>/" on GitHub Pages project sites; "/" locally.
export default defineConfig({
  base: process.env.EXPLORER_BASE ?? "/",
  plugins: [react()],
  test: { environment: "jsdom" },
});
