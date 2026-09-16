<script lang="ts">
	import { goto } from '$app/navigation';
	import { auth } from '$lib/stores/auth';
	import { ApiError } from '$lib/api/client';

	let username = $state('');
	let password = $state('');
	let error = $state('');
	let loading = $state(false);

	async function submit(event: SubmitEvent) {
		event.preventDefault();
		error = '';
		loading = true;
		try {
			const user = await auth.login(username, password);
			if (user.role === 'pharmacien' || user.role === 'admin') {
				goto('/pharmacien');
			} else {
				goto('/patient');
			}
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Erreur de connexion au serveur.';
		} finally {
			loading = false;
		}
	}
</script>

<div class="login-page">
	<div class="card login-card">
		<h1>Connexion</h1>
		<p class="subtitle">Gestion Pharmacie IA</p>

		{#if error}
			<div class="alert alert-error">{error}</div>
		{/if}

		<form onsubmit={submit}>
			<label>
				Identifiant
				<input type="text" bind:value={username} placeholder="pharmacien1" required />
			</label>
			<label>
				Mot de passe
				<input type="password" bind:value={password} placeholder="••••••••" required />
			</label>
			<button type="submit" class="btn btn-primary" disabled={loading}>
				{loading ? 'Connexion…' : 'Se connecter'}
			</button>
		</form>

		<div class="hint">
			<p>Comptes de démonstration (selon données seed du backend) :</p>
			<code>pharmacien1 / secret</code> · <code>patient1 / secret</code>
		</div>
	</div>
</div>

<style>
	.login-page {
		display: flex;
		justify-content: center;
		padding-top: 2rem;
	}
	.login-card {
		width: 100%;
		max-width: 380px;
	}
	.subtitle {
		color: #666;
		margin-top: -0.5rem;
	}
	form {
		display: flex;
		flex-direction: column;
		gap: 1rem;
		margin-top: 1rem;
	}
	.hint {
		margin-top: 1.5rem;
		font-size: 0.85rem;
		color: #888;
		background: #f5f5f5;
		padding: 0.75rem;
		border-radius: 8px;
		line-height: 1.6;
	}
	code {
		background: #eee;
		padding: 0 4px;
		border-radius: 4px;
	}
</style>
