import { browser } from '$app/environment';
import type {
	LoginResponse,
	Medicament,
	MedicamentList,
	RupturesList,
	RecommandationResponse,
	VenteResponse,
	StockUpdateResponse,
	User
} from './types';

const TOKEN_KEY = 'auth_token';
const DEMO_TOKEN = 'token-1-demo';

export function getToken(): string | null {
	if (!browser) return null;
	return localStorage.getItem(TOKEN_KEY) ?? DEMO_TOKEN;
}

export function setToken(token: string | null): void {
	if (!browser) return;
	if (token) localStorage.setItem(TOKEN_KEY, token);
	else localStorage.removeItem(TOKEN_KEY);
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
	const token = getToken();
	const res = await fetch(`http://localhost:8000${path}`, {
		...options,
		headers: {
			'Content-Type': 'application/json',
			...(token ? { Authorization: `Bearer ${token}` } : {}),
			...(options.headers || {})
		}
	});

	if (!res.ok) {
		let detail = `Erreur ${res.status}`;
		try {
			const body = await res.json();
			if (typeof body.detail === 'string') detail = body.detail;
			else if (body.detail && typeof body.detail[0]?.msg === 'string') {
				detail = body.detail[0].msg;
			}
		} catch {
			/* ignore */
		}
		if (res.status === 401) {
			setToken(null);
		}
		throw new ApiError(res.status, detail);
	}

	if (res.status === 204) {
		return undefined as T;
	}
	return (await res.json()) as T;
}

export class ApiError extends Error {
	status: number;
	constructor(status: number, message: string) {
		super(message);
		this.name = 'ApiError';
		this.status = status;
	}
}

export const authApi = {
	login: (username: string, password: string) =>
		api<LoginResponse>('/auth/login', {
			method: 'POST',
			body: JSON.stringify({ username, password })
		}),
	me: () => api<User>('/auth/me')
};

export const medicamentsApi = {
	list: (search = '', page = 1, limit = 50) =>
		api<MedicamentList>(
			`/medicaments?search=${encodeURIComponent(search)}&page=${page}&limit=${limit}`
		),
	create: (data: Omit<Medicament, 'id'>) =>
		api<Medicament>('/medicaments', { method: 'POST', body: JSON.stringify(data) }),
	update: (id: number, data: Partial<Medicament>) =>
		api<Medicament>(`/medicaments/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
	remove: (id: number) => api<void>(`/medicaments/${id}`, { method: 'DELETE' })
};

export const stockApi = {
	ruptures: () => api<RupturesList>('/stock/ruptures'),
	ajout: (medicament_id: number, quantite: number) =>
		api<StockUpdateResponse>('/stock/ajout', {
			method: 'POST',
			body: JSON.stringify({ medicament_id, quantite })
		}),
	vente: (medicament_id: number, quantite: number, client = '') =>
		api<VenteResponse>('/stock/vente', {
			method: 'POST',
			body: JSON.stringify({ medicament_id, quantite, client })
		})
};

export const iaApi = {
	recommandations: (data: { symptomes: string; age?: number; allergies?: string[] }) =>
		api<RecommandationResponse>('/ia/recommandations', { method: 'POST', body: JSON.stringify(data) })
};
