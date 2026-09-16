<script lang="ts">
	import RoleGuard from '$lib/components/RoleGuard.svelte';
	import { medicamentsApi, stockApi, ApiError } from '$lib/api/client';
	import type { Medicament } from '$lib/api/types';

	let medicaments = $state<Medicament[]>([]);
	let loading = $state(true);
	let error = $state('');
	let search = $state('');
	let notice = $state('');

	let showForm = $state(false);
	let editingId = $state<number | null>(null);
	let form = $state({
		nom: '',
		categorie: '',
		prix: 0,
		quantite_stock: 0,
		seuil_alerte: 10,
		date_expiration: '',
		fournisseur_id: 1
	});

	const qteAjout = $state({ id: 0, quantite: 1 });

	async function load() {
		loading = true;
		error = '';
		try {
			const res = await medicamentsApi.list(search);
			medicaments = res.items;
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Erreur de chargement.';
		} finally {
			loading = false;
		}
	}

	$effect(() => {
		load();
	});

	async function resetForm() {
		form = {
			nom: '',
			categorie: '',
			prix: 0,
			quantite_stock: 0,
			seuil_alerte: 10,
			date_expiration: '',
			fournisseur_id: 1
		};
		editingId = null;
		showForm = false;
	}

	function editMed(m: Medicament) {
		editingId = m.id;
		form = {
			nom: m.nom,
			categorie: m.categorie,
			prix: m.prix,
			quantite_stock: m.quantite_stock,
			seuil_alerte: m.seuil_alerte,
			date_expiration: m.date_expiration,
			fournisseur_id: m.fournisseur_id
		};
		showForm = true;
	}

	async function submitForm(event: SubmitEvent) {
		event.preventDefault();
		notice = '';
		try {
			if (editingId !== null) {
				await medicamentsApi.update(editingId, { ...form });
				notice = 'Médicament mis à jour.';
			} else {
				await medicamentsApi.create({ ...form });
				notice = 'Médicament ajouté.';
			}
			await resetForm();
			await load();
		} catch (e) {
			notice = e instanceof ApiError ? e.message : 'Erreur lors de la sauvegarde.';
		}
	}

	async function removeMed(id: number, nom: string) {
		if (!confirm(`Supprimer « ${nom} » ?`)) return;
		try {
			await medicamentsApi.remove(id);
			notice = 'Médicament supprimé.';
			await load();
		} catch (e) {
			notice = e instanceof ApiError ? e.message : 'Erreur lors de la suppression.';
		}
	}

	async function ajouterStock(m: Medicament) {
		qteAjout.id = m.id;
		const qte = prompt(`Quantité à ajouter pour « ${m.nom} » (valeur actuelle : ${m.quantite_stock}) :`, '50');
		if (qte === null) return;
		const n = parseInt(qte, 10);
		if (isNaN(n) || n <= 0) return;
		try {
			const res = await stockApi.ajout(m.id, n);
			notice = res.message ?? 'Stock mis à jour.';
			await load();
		} catch (e) {
			notice = e instanceof ApiError ? e.message : 'Erreur.';
		}
	}

	async function vente(m: Medicament) {
		const qte = prompt(`Quantité vendue pour « ${m.nom} » :`, '1');
		if (qte === null) return;
		const n = parseInt(qte, 10);
		if (isNaN(n) || n <= 0) return;
		try {
			const res = await stockApi.vente(m.id, n);
			notice = `Vente enregistrée. Stock restant : ${res.quantite_stock}.`;
			await load();
		} catch (e) {
			notice = e instanceof ApiError ? e.message : 'Erreur.';
		}
	}
</script>

<RoleGuard roles={['pharmacien', 'admin']}>

	<div class="head">
		<h1>Médicaments &amp; Stock</h1>
		<button class="btn btn-primary" onclick={() => (showForm = !showForm)}>
			{showForm ? 'Fermer le formulaire' : 'Ajouter un médicament'}
		</button>
	</div>

	{#if notice}
		<div class="alert alert-info">{notice}</div>
	{/if}

	{#if showForm}
		<div class="card form-card">
			<h2>{editingId !== null ? `Modifier : ${form.nom}` : 'Nouveau médicament'}</h2>
			<form onsubmit={submitForm}>
				<div class="grid">
					<label>
						Nom
						<input type="text" bind:value={form.nom} required />
					</label>
					<label>
						Catégorie
						<input type="text" bind:value={form.categorie} placeholder="Antalgique" required />
					</label>
					<label>
						Prix (Ar)
						<input type="number" bind:value={form.prix} min="0" required />
					</label>
					<label>
						Quantité initiale
						<input type="number" bind:value={form.quantite_stock} min="0" required />
					</label>
					<label>
						Seuil d'alerte
						<input type="number" bind:value={form.seuil_alerte} min="0" required />
					</label>
					<label>
						Date d'expiration
						<input type="date" bind:value={form.date_expiration} />
					</label>
					<label>
						Fournisseur (ID)
						<input type="number" bind:value={form.fournisseur_id} min="1" required />
					</label>
				</div>
				<div class="form-actions">
					<button type="submit" class="btn btn-primary">Enregistrer</button>
					<button type="button" class="btn" onclick={resetForm}>Annuler</button>
				</div>
			</form>
		</div>
	{/if}

	<div class="toolbar">
		<label class="search">
			<span>Rechercher</span>
			<input
				type="text"
				bind:value={search}
				placeholder="Nom ou composition…"
				oninput={() => load()}
			/>
		</label>
	</div>

	{#if error}
		<div class="alert alert-error">{error}</div>
	{/if}

	{#if loading}
		<p>Chargement…</p>
	{:else}
		<table>
			<thead>
				<tr>
					<th>Nom</th>
					<th>Catégorie</th>
					<th>Prix</th>
					<th>Stock</th>
					<th>Seuil</th>
					<th>Expiration</th>
					<th>Actions</th>
				</tr>
			</thead>
			<tbody>
				{#each medicaments as m}
					<tr>
						<td>{m.nom}</td>
						<td>{m.categorie}</td>
						<td>{m.prix.toLocaleString('fr-FR')} Ar</td>
						<td>
							<span
								class={m.quantite_stock <= m.seuil_alerte ? 'stock-low' : ''}
							>{m.quantite_stock}</span
							>
						</td>
						<td>{m.seuil_alerte}</td>
						<td>{m.date_expiration}</td>
						<td>
							<div class="row-actions">
								<button class="btn btn-sm" onclick={() => editMed(m)}>Modifier</button>
								<button class="btn btn-sm" onclick={() => ajouterStock(m)}>+ Stock</button>
								<button class="btn btn-sm" onclick={() => vente(m)}>Vente</button>
								<button class="btn btn-sm btn-danger" onclick={() => removeMed(m.id, m.nom)}
									>Suppr.</button
								>
							</div>
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
		{#if medicaments.length === 0}
			<p class="empty">Aucun médicament trouvé.</p>
		{/if}
	{/if}

</RoleGuard>

<style>
	.head {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 1.25rem;
		flex-wrap: wrap;
		gap: 1rem;
	}
	.form-card {
		margin-bottom: 1.5rem;
	}
	.grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
		gap: 1rem;
		margin-top: 1rem;
	}
	.form-actions {
		display: flex;
		gap: 0.75rem;
		margin-top: 1.25rem;
	}
	.toolbar {
		margin-bottom: 1rem;
	}
	.search {
		max-width: 340px;
	}
	.stock-low {
		color: #d32f2f;
		font-weight: 700;
	}
	.row-actions {
		display: flex;
		gap: 0.35rem;
		flex-wrap: wrap;
	}
	.empty {
		color: #888;
		text-align: center;
		padding: 1.5rem;
	}
</style>
