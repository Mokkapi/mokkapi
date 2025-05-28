import { defineConfig } from 'vite'
import path from 'path'

export default defineConfig({
  root: path.resolve(__dirname, 'assets'),
  base: '/static/',
  build: {
    outDir: path.resolve(__dirname, 'static'),
    emptyOutDir: true,
    rollupOptions: {
      input: {
        app: path.resolve(__dirname, 'assets/js/app.js'),
        styles: path.resolve(__dirname, 'assets/css/input.css'),
      },
      output: {
        entryFileNames: '[name].js',
        chunkFileNames: '[name].js',
        assetFileNames: '[name].[ext]'
      }
    }
  }
})
