import { defineConfig } from "vite";

export default defineConfig({
  server: { port: 5178, strictPort: true },
  preview: { port: 4178, strictPort: true },
});
