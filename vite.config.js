import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  css: {
    // This is the default—everything is treated as global CSS
    modules: {
      scopeBehaviour: 'global',
    }
  },
  root: path.resolve(__dirname, 'assets'),
  base: '/static/',
  build: {
    outDir: path.resolve(__dirname, 'static'),
    emptyOutDir: true,
    rollupOptions: {
      input: {
        app: path.resolve(__dirname, 'assets/js/app.js'),
        styles: path.resolve(__dirname, 'assets/css/input.css'),
        'react-app': path.resolve(__dirname, 'assets/js/react-app.tsx'),
      },
      output: {
        entryFileNames: '[name].js',
        chunkFileNames: '[name].js',
        assetFileNames: '[name].[ext]'
      }
    }
  }
})
