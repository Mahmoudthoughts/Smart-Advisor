export interface TelemetryUser {
  id: string | number;
  email?: string | null;
  role?: string | null;
}

/**
 * Persist user identity for telemetry propagation.
 * Call this after login and when user context changes.
 */
export function setUserTelemetry(user: TelemetryUser | null): void {
  try {
    const key = 'smart-advisor.userTelemetry';
    if (user) {
      localStorage.setItem(key, JSON.stringify(user));
    } else {
      localStorage.removeItem(key);
    }
  } catch {
    // ignore persistence errors
  }
}

