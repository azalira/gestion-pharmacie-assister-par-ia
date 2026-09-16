// Definition des types selon le contrat d'API (docs/api-contrat.md)

export type Role = 'admin' | 'pharmacien' | 'patient';

export interface User {
	id: number;
	username: string;
	full_name: string;
	role: Role;
}

export interface LoginResponse {
	access_token: string;
	token_type: string;
	user: User;
}

export interface Medicament {
	id: number;
	nom: string;
	categorie: string;
	prix: number;
	quantite_stock: number;
	seuil_alerte: number;
	date_expiration: string;
	fournisseur_id: number;
}

export interface MedicamentList {
	items: Medicament[];
	total: number;
	page: number;
}

export interface StockRupture {
	id: number;
	nom: string;
	quantite_stock: number;
	seuil_alerte: number;
	etat: 'alerte' | 'rupture';
}

export interface RupturesList {
	items: StockRupture[];
}

export interface StockUpdateResponse {
	id: number;
	quantite_stock: number;
	message: string;
}

export interface VenteResponse {
	id: number;
	quantite_stock: number;
	vente_id: number;
}

export interface RecommandationRequest {
	symptomes: string;
	age?: number;
	allergies?: string[];
}

export interface MaladieProbable {
	maladie: string;
	probabilite: number;
}

export interface RecommandationMedicament {
	medicament_id: number;
	nom: string;
	categorie: string;
	prix: number;
	disponible: boolean;
	motif: string;
}

export interface RecommandationResponse {
	maladies_probables: MaladieProbable[];
	recommandations: RecommandationMedicament[];
	alerte?: string;
}
