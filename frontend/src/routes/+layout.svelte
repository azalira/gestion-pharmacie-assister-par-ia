<script lang="ts">
	import { browser } from '$app/environment';
	import { auth } from '$lib/stores/auth';
	import favicon from '$lib/assets/favicon.svg';

	let { children } = $props();

	$effect(() => {
		if (browser && !auth.ready) {
			auth.init();
		}
	});

	async function handleLogout() {
		auth.logout();
		window.location.href = '/';
	}
</script>

<svelte:head>
	<title>Gestion Pharmacie IA</title>
	<link rel="icon" href={favicon} />
</svelte:head>

<nav>
	<div class="nav-brand">
		<a href="/">💊 Gestion Pharmacie IA</a>
	</div>
	{#if auth.isAuthenticated}
		<div class="nav-links">
			{#if auth.role === 'pharmacien' || auth.role === 'admin'}
				<a href="/pharmacien">Dashboard</a>
				<a href="/pharmacien/medicaments">Médicaments</a>
			{/if}
			{#if auth.role === 'patient' || auth.role === 'pharmacien'}
				<a href="/patient">Recommandations IA</a>
			{/if}
		</div>
		<div class="nav-user">
			<span>{auth.user?.full_name ?? auth.user?.username}</span>
			<button onclick={handleLogout} class="btn-outline">Déconnexion</button>
		</div>
	{:else}
		<div class="nav-links">
			<a href="/login">Connexion</a>
		</div>
	{/if}
</nav>

<main>
	{@render children()}
</main>

<style>
	:global(*) {
		box-sizing: border-box;
	}
	:global(body) {
		margin: 0;
		font-family: system-ui, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
		background: #f4f6f8;
		color: #222;
	}
	:global(.card) {
		background: white;
		border: 1px solid #e2e6ea;
		border-radius: 10px;
		padding: 1.5rem;
		box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
	}
	:global(.alert) {
		padding: 0.75rem 1rem;
		border-radius: 8px;
		margin: 0.5rem 0;
	}
	:global(.alert-error) {
		background: #fdecea;
		color: #b71c1c;
		border: 1px solid #f5c6c2;
	}
	:global(.alert-info) {
		background: #e8f0fe;
		color: #1a3a6e;
		border: 1px solid #c1d4f5;
	}
	:global(.alert-warn) {
		background: #fff4e5;
		color: #8a4a00;
		border: 1px solid #ffd9a3;
	}
	:global(.btn) {
		border: none;
		border-radius: 8px;
		padding: 0.6rem 1.2rem;
		cursor: pointer;
		font-size: 0.95rem;
	}
	:global(.btn-primary) {
		background: #0f4c81;
		color: white;
	}
	:global(.btn-primary:hover:not(:disabled)) {
		background: #0d3f6b;
	}
	:global(.btn-danger) {
		background: #d32f2f;
		color: white;
	}
	:global(.btn:disabled) {
		opacity: 0.6;
		cursor: not-allowed;
	}
	:global(.btn-sm) {
		padding: 0.3rem 0.7rem;
		font-size: 0.85rem;
	}
	:global(input),
	:global(select),
	:global(textarea) {
		width: 100%;
		padding: 0.55rem 0.75rem;
		border: 1px solid #ccd1d6;
		border-radius: 8px;
		font-size: 0.95rem;
	}
	:global(label) {
		display: flex;
		flex-direction: column;
		gap: 0.35rem;
		font-size: 0.9rem;
		font-weight: 600;
	}
	:global(h1) {
		font-size: 1.6rem;
	}
	:global(table) {
		width: 100%;
		border-collapse: collapse;
		background: white;
	}
	:global(th),
	:global(td) {
		padding: 0.6rem 0.75rem;
		text-align: left;
		border-bottom: 1px solid #eef0f2;
		font-size: 0.92rem;
	}
	:global(th) {
		background: #f7f9fb;
		font-weight: 600;
	}
	nav {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 1rem;
		padding: 0.75rem 1.5rem;
		background: #0f4c81;
		color: white;
		flex-wrap: wrap;
	}
	.nav-brand a {
		color: white;
		text-decoration: none;
		font-weight: 700;
		font-size: 1.1rem;
	}
	.nav-links {
		display: flex;
		gap: 1.25rem;
		align-items: center;
	}
	.nav-links a {
		color: #dfe9f5;
		text-decoration: none;
	}
	.nav-links a:hover {
		color: white;
		text-decoration: underline;
	}
	.nav-user {
		display: flex;
		align-items: center;
		gap: 0.75rem;
	}
	:global(.btn-outline) {
		background: transparent;
		color: white;
		border: 1px solid rgba(255, 255, 255, 0.6);
		border-radius: 6px;
		padding: 0.35rem 0.8rem;
		font-size: 0.85rem;
		cursor: pointer;
	}
	main {
		max-width: 1100px;
		margin: 2rem auto;
		padding: 0 1.5rem;
	}
</style>
