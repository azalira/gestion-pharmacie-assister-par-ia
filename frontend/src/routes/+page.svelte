<script lang="ts">
	import { goto } from '$app/navigation';
	import { browser } from '$app/environment';
	import { auth } from '$lib/stores/auth';

	$effect(() => {
		if (!auth.ready) return;
		if (!auth.isAuthenticated) {
			if (browser) goto('/login');
			return;
		}
		const role = auth.role;
		if (role === 'pharmacien' || role === 'admin') {
			goto('/pharmacien');
		} else if (role === 'patient') {
			goto('/patient');
		} else {
			goto('/login');
		}
	});
</script>

<div class="loading">
	<p>Chargement…</p>
</div>

<style>
	.loading {
		text-align: center;
		padding: 3rem;
		color: #666;
	}
</style>
