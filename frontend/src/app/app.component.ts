import { Component, HostListener, computed, effect, inject, signal } from '@angular/core';
import { NgFor, NgIf } from '@angular/common';
import { Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { AuthService } from './auth.service';

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
  private readonly navStorageKey = 'smart-advisor.nav-selection';
  private readonly hasStorage = typeof window !== 'undefined' && !!window.localStorage;

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
  readonly selectedPaths = signal<string[]>(this.loadSelections());
  readonly navLinks = computed(() =>
    this.allNavLinks.filter((link) => this.selectedPaths().includes(link.path))
  );
  readonly brandTarget = computed(() => (this.isAuthenticated() ? '/app/overview' : '/login'));
  readonly currentYear = new Date().getFullYear();

  constructor() {
    effect(() => {
      if (!this.hasStorage) {
        return;
      }
      const selections = this.selectedPaths();
      localStorage.setItem(this.navStorageKey, JSON.stringify(selections));
    });
  }

  logout(): void {
    this.auth.logout();
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
}
