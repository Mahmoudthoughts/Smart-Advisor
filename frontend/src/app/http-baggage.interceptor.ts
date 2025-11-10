import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { AuthService } from './auth.service';

type TelemetryUser = {
  id: string | number;
  email?: string | null;
  role?: string | null;
};

function readUser(): TelemetryUser | null {
  try {
    const raw = localStorage.getItem('smart-advisor.userTelemetry');
    return raw ? (JSON.parse(raw) as TelemetryUser) : null;
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
      req = req.clone({ setHeaders: { baggage } });
    }
  }
  return next(req);
};
