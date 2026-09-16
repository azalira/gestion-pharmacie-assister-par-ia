import type { Role, User } from '../api/types';

const DEMO_USER: User = {
	id: 1,
	username: 'pharmacien1',
	full_name: 'Pharmacien Démo',
	role: 'pharmacien'
};

class AuthStore {
	user = $state<User | null>(DEMO_USER);
	ready = $state(true);

	get isAuthenticated(): boolean {
		return this.user !== null;
	}

	get role(): Role | null {
		return this.user?.role ?? null;
	}

	async init(): Promise<void> {
		this.ready = true;
	}

	async login(username: string, password: string): Promise<User> {
		this.user = DEMO_USER;
		return DEMO_USER;
	}

	logout(): void {
		this.user = null;
	}
}

export const auth = new AuthStore();
