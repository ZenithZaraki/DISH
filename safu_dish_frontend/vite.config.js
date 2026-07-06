import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import { fileURLToPath, URL } from 'node:url';
import { execSync } from 'child_process';

try {
  console.log("[+] Building component map...");
  execSync('node ./src/tools/buildComponentMap.cjs', { stdio: 'inherit' });
} catch (err) {
  console.error("[X] Failed to build component map:", err);
}

export default defineConfig({
  plugins: [svelte()],
  resolve: {
    alias: {
      $components: fileURLToPath(new URL('./src/lib/components', import.meta.url)),
      $stores: fileURLToPath(new URL('./src/stores', import.meta.url)),
      $lib: fileURLToPath(new URL('./src/lib', import.meta.url)),
      $assets: fileURLToPath(new URL('./src/assets', import.meta.url))
    }
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false
      }
    }
  }
});
