import { Component, HostListener, computed, effect, inject, signal } from '@angular/core';
import { NgFor, NgIf } from '@angular/common';
import { Router, RouterLink, RouterLinkActive, RouterOutlet, NavigationEnd } from '@angular/router';
import { AuthService } from './auth.service';
import { setUserTelemetry } from './telemetry-user';
import { DebugService } from './debug.service';
import { environment } from '../environments/environment';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive, NgIf, NgFor],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss']
})
export class AppComponent {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly debug = inject(DebugService);
  private readonly navStorageKey = 'smart-advisor.nav-selection';
  private readonly hasStorage = typeof window !== 'undefined' && !!window.localStorage;
  private readonly themeStorageKey = 'smart-advisor.theme';

  readonly brand = 'Smart Advisor';
  readonly isAuthenticated = this.auth.isAuthenticated;
  readonly user = this.auth.user;
  readonly allNavLinks = [
    { path: '/app/overview', label: 'Overview' },
    { path: '/app/stocks', label: 'My Stocks' },
    { path: '/app/transactions', label: 'Transactions' },
    { path: '/app/timeline', label: 'Timeline' },
    { path: '/app/opportunities', label: 'Opportunities' },
    { path: '/app/signals', label: 'Signals' },
    { path: '/app/sentiment', label: 'Sentiment' },
    { path: '/app/forecast', label: 'Forecast' },
    { path: '/app/simulator', label: 'Simulator' },
    { path: '/app/macro', label: 'Macro' },
    { path: '/app/alerts', label: 'Alerts' }
  ];

  readonly menuOpen = signal(false);
  readonly sidebarOpen = signal(false);
  readonly selectedPaths = signal<string[]>(this.loadSelections());
  readonly navLinks = computed(() =>
    this.allNavLinks.filter((link) => this.selectedPaths().includes(link.path))
  );
  readonly brandTarget = computed(() => (this.isAuthenticated() ? '/app/overview' : '/login'));
  readonly currentYear = new Date().getFullYear();
  readonly isDarkTheme = signal(this.restoreTheme());
  readonly isDev = !environment.production;
  readonly debugOutput = signal<string | null>(null);

  constructor() {
    effect(() => {
      if (!this.hasStorage) {
        return;
      }
      const selections = this.selectedPaths();
      localStorage.setItem(this.navStorageKey, JSON.stringify(selections));
    });

    // Close sidebar on navigation
    this.router.events.subscribe((evt) => {
      if (evt instanceof NavigationEnd) {
        this.sidebarOpen.set(false);
      }
    });

    // Apply theme on startup
    this.applyTheme(this.isDarkTheme());
    // Persist theme when it changes
    effect(() => {
      const dark = this.isDarkTheme();
      if (this.hasStorage) {
        localStorage.setItem(this.themeStorageKey, dark ? 'dark' : 'light');
      }
      this.applyTheme(dark);
    });

    // Keep telemetry user baggage in sync with auth state
    effect(() => {
      const u = this.user();
      if (u) {
        setUserTelemetry({ id: u.id, email: u.email, role: 'user' });
      } else {
        setUserTelemetry(null);
      }
    });
  }

  logout(): void {
    this.auth.logout();
    setUserTelemetry(null);
    void this.router.navigate(['/login']);
  }

  userInitials(): string {
    const name = this.user()?.name ?? '';
    if (!name.trim()) {
      return '•';
    }
    const parts = name.trim().split(/\s+/);
    if (parts.length === 1) {
      return parts[0].slice(0, 2).toUpperCase();
    }
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  }

  toggleMenu(event?: MouseEvent): void {
    event?.stopPropagation();
    this.menuOpen.update((open) => !open);
  }

  toggleSidebar(): void {
    this.sidebarOpen.update((open) => !open);
  }

  closeSidebar(): void {
    this.sidebarOpen.set(false);
  }

  debugTelemetry(): void {
    this.debugOutput.set(null);
    this.debug.corsTest().subscribe({
      next: (data) => {
        try {
          this.debugOutput.set(JSON.stringify(data));
          // eslint-disable-next-line no-console
          console.debug('[telemetry-debug]', data);
        } catch {
          this.debugOutput.set(String(data));
        }
      },
      error: (err) => {
        const message = err?.error ?? err?.message ?? 'Failed to call /debug/cors-test';
        this.debugOutput.set(typeof message === 'string' ? message : JSON.stringify(message));
      }
    });
  }

  keepMenuOpen(event: MouseEvent): void {
    event.stopPropagation();
  }

  toggleLink(path: string): void {
    this.selectedPaths.update((current) => {
      const next = current.includes(path)
        ? current.filter((item) => item !== path)
        : this.sortPaths([...current, path]);
      return next.length === 0 ? current : next;
    });
  }

  selectAll(): void {
    this.selectedPaths.set(this.sortPaths(this.allNavLinks.map((link) => link.path)));
  }

  resetDefaults(): void {
    this.selectedPaths.set(this.sortPaths(this.allNavLinks.map((link) => link.path)));
  }

  isLinkSelected(path: string): boolean {
    return this.selectedPaths().includes(path);
  }

  @HostListener('document:click')
  closeMenu(): void {
    this.menuOpen.set(false);
  }

  @HostListener('document:keydown.escape')
  onEscape(): void {
    this.closeSidebar();
  }

  private loadSelections(): string[] {
    try {
      if (!this.hasStorage) {
        return this.sortPaths(this.allNavLinks.map((link) => link.path));
      }
      const stored = localStorage.getItem(this.navStorageKey);
      if (!stored) {
        return this.sortPaths(this.allNavLinks.map((link) => link.path));
      }
      const parsed = JSON.parse(stored);
      if (Array.isArray(parsed) && parsed.every((value) => typeof value === 'string')) {
        const valid = parsed.filter((path) => this.allNavLinks.some((link) => link.path === path));
        if (valid.length > 0) {
          return this.sortPaths(valid);
        }
      }
    } catch {
      // ignore parsing errors and fall back to defaults
    }
    return this.sortPaths(this.allNavLinks.map((link) => link.path));
  }

  private sortPaths(paths: string[]): string[] {
    const order = this.allNavLinks.map((link) => link.path);
    return Array.from(new Set(paths)).sort(
      (a, b) => order.indexOf(a) - order.indexOf(b)
    );
  }

  toggleTheme(): void {
    this.isDarkTheme.update((v) => !v);
  }

  private applyTheme(dark: boolean): void {
    if (typeof document === 'undefined') return;
    const body = document.body;
    if (dark) {
      body.classList.add('theme-dark');
    } else {
      body.classList.remove('theme-dark');
    }
  }

  private restoreTheme(): boolean {
    try {
      if (!this.hasStorage) return false;
      const saved = localStorage.getItem(this.themeStorageKey);
      if (saved === 'dark') return true;
      if (saved === 'light') return false;
    } catch {}
    // Fallback: prefer system setting
    if (typeof window !== 'undefined' && window.matchMedia) {
      return window.matchMedia('(prefers-color-scheme: dark)').matches;
    }
    return false;
  }
}
