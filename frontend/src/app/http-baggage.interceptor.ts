import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { AuthService } from './auth.service';

type TelemetryUser = {
  id: string | number;
  email?: string | null;
  role?: string | null;
};

interface StoredAuthState {
  token: string;
  user: TelemetryUser & { name?: string };
}

function readUser(): TelemetryUser | null {
  try {
    const raw = localStorage.getItem('smart-advisor.userTelemetry');
    return raw ? (JSON.parse(raw) as TelemetryUser) : null;
  } catch {
    return null;
  }
}

function readAuthState(): StoredAuthState | null {
  try {
    const raw = localStorage.getItem('smart-advisor-auth');
    return raw ? (JSON.parse(raw) as StoredAuthState) : null;
  } catch {
    return null;
  }
}

function buildBaggage(user: TelemetryUser): string | null {
  const parts: string[] = [];
  const enc = encodeURIComponent;
  if (user.id !== undefined && user.id !== null && String(user.id).length) {
    parts.push(`enduser.id=${enc(String(user.id))}`);
  }
  if (user.email) {
    parts.push(`enduser.email=${enc(user.email)}`);
  }
  if (user.role) {
    parts.push(`enduser.role=${enc(user.role)}`);
  }
  return parts.length ? parts.join(',') : null;
}

export const userBaggageInterceptor: HttpInterceptorFn = (req, next) => {
  const headers: Record<string, string> = {};
  const authState = readAuthState();
  if (authState?.token) {
    headers['Authorization'] = `Bearer ${authState.token}`;
  }
  // Prefer live auth state; fallback to stored telemetry
  let user = readUser();
  try {
    const auth = inject(AuthService);
    const live = auth?.user?.();
    if (live) {
      user = { id: live.id, email: live.email, role: 'user' };
    }
  } catch {
    // ignore injection issues during bootstrap
  }
  if (user) {
    const baggage = buildBaggage(user);
    if (baggage) {
      headers['baggage'] = baggage;
    }
  }
  if (Object.keys(headers).length) {
    req = req.clone({ setHeaders: headers });
  }
  return next(req);
};
