<script lang="ts">
	import RoleGuard from '$lib/components/RoleGuard.svelte';
	import { iaApi, ApiError } from '$lib/api/client';
	import type { RecommandationResponse } from '$lib/api/types';

	let symptomes = $state('');
	let age = $state<number | null>(null);
	let allergies = $state('');
	let loading = $state(false);
	let error = $state('');
	let resultat: RecommandationResponse | null = $state(null);

	async function demander(event: SubmitEvent) {
		event.preventDefault();
		error = '';
		resultat = null;
		loading = true;
		try {
			const allergiesArray = allergies
				.split(',')
				.map((a) => a.trim())
				.filter((a) => a.length > 0);
			resultat = await iaApi.recommandations({
				symptomes,
				...(age ? { age } : {}),
				...(allergiesArray.length ? { allergies: allergiesArray } : {})
			});
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Erreur de connexion au service IA.';
		} finally {
			loading = false;
		}
	}

	function nbRecommandations() {
		return resultat?.recommandations.length ?? 0;
	}
</script>

<RoleGuard roles={['patient', 'pharmacien', 'admin']}>

	<div class="head">
		<h1>Recommandation IA</h1>
		<p class="subtitle">Décrivez vos symptômes — l'IA propose des médicaments disponibles en stock.</p>
	</div>

	<form class="card" onsubmit={demander}>
		<label>
			Symptômes
			<textarea
				bind:value={symptomes}
				rows="4"
				placeholder="Ex : fièvre, maux de tête, courbatures…"
				required
			></textarea>
		</label>
		<div class="row">
			<label>
				Âge
				<input type="number" bind:value={age} min="0" max="130" placeholder="(optionnel)" />
			</label>
			<label>
				Allergies (séparées par des virgules)
				<input type="text" bind:value={allergies} placeholder="Ex : pénicilline, aspirine" />
			</label>
		</div>
		<button type="submit" class="btn btn-primary" disabled={loading || symptomes.trim() === ''}>
			{loading ? 'Analyse en cours…' : 'Obtenir des recommandations'}
		</button>
	</form>

	{#if error}
		<div class="alert alert-error">{error}</div>
	{/if}

	{#if resultat}
		<div class="results">
			{#if resultat.alerte}
				<div class="alert alert-warn">{resultat.alerte}</div>
			{/if}

			{#if resultat.maladies_probables.length > 0}
				<div class="card">
					<h2>Maladies probables</h2>
					{#each resultat.maladies_probables as mp}
						<div class="maladie">
							<span>{mp.maladie}</span>
							<span class="prob">{(mp.probabilite * 100).toFixed(0)}%</span>
						</div>
					{/each}
				</div>
			{/if}

			<div class="card">
				<h2>Médicaments recommandés ({nbRecommandations()})</h2>
				{#if nbRecommandations() === 0}
					<p class="empty">Aucun médicament disponible en stock ne correspond. Contactez le Pharmacien.</p>
				{:else}
					<table>
						<thead>
							<tr>
								<th>Médicament</th>
								<th>Catégorie</th>
								<th>Prix</th>
								<th>Motif</th>
							</tr>
						</thead>
						<tbody>
							{#each resultat.recommandations as rec}
								<tr>
									<td>{rec.nom}</td>
									<td>{rec.categorie}</td>
									<td>{rec.prix.toLocaleString('fr-FR')} Ar</td>
									<td>{rec.motif}</td>
								</tr>
							{/each}
						</tbody>
					</table>
				{/if}
				<div class="note">
					ℹ️ Ces recommandations sont indicatives et ne remplacent pas un avis médical.
				</div>
			</div>
		</div>
	{/if}

</RoleGuard>

<style>
	.head {
		margin-bottom: 1.5rem;
	}
	.subtitle {
		color: #666;
	}
	form {
		display: flex;
		flex-direction: column;
		gap: 1rem;
		max-width: 720px;
	}
	.row {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 1rem;
	}
	.results {
		margin-top: 2rem;
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
		max-width: 720px;
	}
	.maladie {
		display: flex;
		justify-content: space-between;
		padding: 0.5rem 0;
		border-bottom: 1px solid #f0f0f0;
	}
	.prob {
		font-weight: 700;
		color: #0f4c81;
	}
	.note {
		margin-top: 1rem;
		font-size: 0.85rem;
		color: #888;
	}
	.empty {
		color: #888;
	}
</style>
