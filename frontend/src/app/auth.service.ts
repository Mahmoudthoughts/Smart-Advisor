import { Injectable, computed, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { tap } from 'rxjs';
import { environment } from '../environments/environment';
import { setUserTelemetry } from './telemetry-user';

export interface AuthUser {
  readonly id: string;
  readonly name: string;
  readonly email: string;
  readonly createdAt: string;
}

export interface AuthResponse {
  readonly access_token: string;
  readonly token_type: string;
  readonly user: {
    readonly id: string;
    readonly name: string;
    readonly email: string;
    readonly created_at: string;
  };
}

interface StoredAuthState {
  readonly token: string;
  readonly user: AuthUser;
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly storageKey = 'smart-advisor-auth';
  private readonly userState = signal<AuthUser | null>(this.restoreUser());

  readonly user = computed(() => this.userState());
  readonly isAuthenticated = computed(() => this.userState() !== null);

  login(email: string, password: string) {
    return this.http
      .post<AuthResponse>(`${environment.apiBaseUrl}/auth/login`, { email, password })
      .pipe(tap((response) => this.persistAuth(response)));
  }

  register(name: string, email: string, password: string) {
    return this.http
      .post<AuthResponse>(`${environment.apiBaseUrl}/auth/register`, { name, email, password })
      .pipe(tap((response) => this.persistAuth(response)));
  }

  logout(): void {
    this.userState.set(null);
    this.persistState(null);
  }

  private persistAuth(response: AuthResponse): void {
    const authUser: AuthUser = {
      id: response.user.id,
      name: response.user.name,
      email: response.user.email,
      createdAt: response.user.created_at
    };
    this.userState.set(authUser);
    this.persistState({ token: response.access_token, user: authUser });
    // Immediately expose user identity for telemetry baggage
    try {
      setUserTelemetry({ id: authUser.id, email: authUser.email, role: 'user' });
    } catch {}
  }

  private restoreUser(): AuthUser | null {
    if (typeof window === 'undefined') {
      return null;
    }
    try {
      const stored = window.localStorage.getItem(this.storageKey);
      if (!stored) {
        return null;
      }
      const parsed = JSON.parse(stored) as StoredAuthState;
      return parsed.user;
    } catch {
      return null;
    }
  }

  private persistState(state: StoredAuthState | null): void {
    if (typeof window === 'undefined') {
      return;
    }
    if (state) {
      window.localStorage.setItem(this.storageKey, JSON.stringify(state));
    } else {
      window.localStorage.removeItem(this.storageKey);
    }
  }
}
