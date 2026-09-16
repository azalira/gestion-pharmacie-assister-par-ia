<script lang="ts">
	import RoleGuard from '$lib/components/RoleGuard.svelte';
	import { auth } from '$lib/stores/auth';
	import { stockApi, medicamentsApi, ApiError } from '$lib/api/client';
	import type { Medicament, StockRupture } from '$lib/api/types';

	let ruptures = $state<StockRupture[]>([]);
	let medicaments = $state<Medicament[]>([]);
	let loading = $state(true);
	let error = $state('');

	async function load() {
		loading = true;
		error = '';
		try {
			const [r, m] = await Promise.all([stockApi.ruptures(), medicamentsApi.list('', 1, 50)]);
			ruptures = r.items;
			medicaments = m.items;
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Impossible de charger les données.';
		} finally {
			loading = false;
		}
	}

	$effect(() => {
		if (auth.role === 'pharmacien' || auth.role === 'admin') {
			load();
		}
	});

	let totalStock = $derived(medicaments.reduce((s, m) => s + m.quantite_stock, 0));
	let alerteCount = $derived(ruptures.length);
	let ruptureCount = $derived(ruptures.filter((r) => r.etat === 'rupture').length);
	let stockValue = $derived(medicaments.reduce((s, m) => s + m.quantite_stock * m.prix, 0));
</script>

<RoleGuard roles={['pharmacien', 'admin']}>

	<div class="header">
		<h1>Dashboard Pharmacien</h1>
		<p>Bienvenue, {auth.user?.full_name ?? auth.user?.username}.</p>
	</div>

	{#if error}
		<div class="alert alert-error">{error}</div>
	{/if}

	<div class="stats">
		<div class="stat card">
			<div class="stat-value">{medicaments.length}</div>
			<div class="stat-label">Références</div>
		</div>
		<div class="stat card">
			<div class="stat-value">{totalStock}</div>
			<div class="stat-label">Unités en stock</div>
		</div>
		<div class="stat card">
			<div class="stat-value">{alerteCount}</div>
			<div class="stat-label">Sous seuil / rupture</div>
		</div>
		<div class="stat card">
			<div class="stat-value">{ruptureCount}</div>
			<div class="stat-label">Ruptures totales</div>
		</div>
		<div class="stat card">
			<div class="stat-value">{stockValue.toLocaleString('fr-FR')} Ar</div>
			<div class="stat-label">Valeur du stock</div>
		</div>
	</div>

	<div class="actions">
		<a href="/pharmacien/medicaments" class="btn btn-primary">Gérer le stock &amp; les médicaments</a>
		<a href="/patient" class="btn">Tester l'IA de recommandation</a>
	</div>

	{#if loading}
		<p>Chargement…</p>
	{:else if ruptures.length > 0}
		<div class="card">
			<h2>⚠️ Alertes de stock</h2>
			<table>
				<thead>
					<tr>
						<th>Médicament</th>
						<th>Quantité</th>
						<th>Seuil</th>
						<th>État</th>
					</tr>
				</thead>
				<tbody>
					{#each ruptures as r}
						<tr>
							<td>{r.nom}</td>
							<td>{r.quantite_stock}</td>
							<td>{r.seuil_alerte}</td>
							<td>
								<span class="badge {r.etat === 'rupture' ? 'badge-danger' : 'badge-warn'}">
									{r.etat === 'rupture' ? 'Rupture' : 'Alerte'}
								</span>
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	{:else}
		<div class="alert alert-info">Aucune alerte de stock. Tous les seuils sont respectés.</div>
	{/if}

</RoleGuard>

<style>
	.header {
		margin-bottom: 1.5rem;
	}
	.header p {
		color: #666;
		margin-top: 0.25rem;
	}
	.stats {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
		gap: 1rem;
		margin-bottom: 1.5rem;
	}
	.stat-value {
		font-size: 1.8rem;
		font-weight: 700;
		color: #0f4c81;
	}
	.stat-label {
		color: #777;
		font-size: 0.9rem;
		margin-top: 0.25rem;
	}
	.actions {
		display: flex;
		gap: 0.75rem;
		margin-bottom: 1.5rem;
		flex-wrap: wrap;
	}
	.badge {
		display: inline-block;
		padding: 0.2rem 0.6rem;
		border-radius: 20px;
		font-size: 0.8rem;
		font-weight: 600;
	}
	.badge-danger {
		background: #fdecea;
		color: #b71c1c;
	}
	.badge-warn {
		background: #fff4e5;
		color: #8a4a00;
	}
	:global(.btn) {
		text-decoration: none;
		display: inline-block;
	}
</style>
