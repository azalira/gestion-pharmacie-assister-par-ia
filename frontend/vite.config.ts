import adapter from '@sveltejs/adapter-static';
import { sveltekit } from '@sveltejs/kit/vite';
import { fileURLToPath, URL } from 'node:url';
import { defineConfig } from 'vite';

export default defineConfig({
	resolve: {
		alias: {
			$lib: fileURLToPath(new URL('./src/lib', import.meta.url))
		},
		extensions: ['.svelte.ts', '.svelte.js', '.mjs', '.js', '.mts', '.ts', '.jsx', '.tsx', '.json']
	},
	plugins: [
		sveltekit({
			files: {
				lib: 'src/lib'
			},
			compilerOptions: {
				// Force runes mode for the project, except for libraries. Can be removed in svelte 6.
				runes: ({ filename }) =>
					filename.split(/[/\\]/).includes('node_modules') ? undefined : true
			},

			// Frontend compilé en statique, servi par le backend FastAPI (voir docs/api-contrat.md).
			adapter: adapter({
				fallback: 'index.html'
			})
		})
	]
});
