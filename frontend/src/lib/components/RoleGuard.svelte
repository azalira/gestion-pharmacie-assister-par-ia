<script lang="ts">
	import { browser } from '$app/environment';
	import { auth } from '$lib/stores/auth';
	import type { Role } from '$lib/api/types';
	import type { Snippet } from 'svelte';

	let { roles, children }: { roles: Role[]; children: Snippet } = $props();

	$effect(() => {
		if (browser && !auth.ready) {
			auth.init();
		}
	});

	let allowed = $derived(
		auth.isAuthenticated && auth.role !== null && roles.includes(auth.role as Role)
	);
</script>

{#if !auth.ready}
	<p class="muted">Chargement…</p>
{:else if !auth.isAuthenticated}
	<div class="card">
		<h1>Accès refusé</h1>
		<p>Vous devez être connecté pour accéder à cette page.</p>
		<p><a href="/login">Aller à la connexion</a></p>
	</div>
{:else if !allowed}
	<div class="card">
		<h1>Accès refusé</h1>
		<p>Votre rôle (<code>{auth.role}</code>) ne vous permet pas d'accéder à cette page.</p>
	</div>
{:else}
	{@render children()}
{/if}

<style>
	.muted {
		color: #777;
	}
</style>
