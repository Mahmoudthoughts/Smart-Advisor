import { Component, computed, inject } from '@angular/core';
import { NgIf } from '@angular/common';
import { Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { AuthService } from './auth.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive, NgIf],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss']
})
export class AppComponent {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  readonly brand = 'Smart Advisor';
  readonly isAuthenticated = this.auth.isAuthenticated;
  readonly user = this.auth.user;
  readonly navLinks = [
    { path: '/app', label: 'Overview', fragment: 'overview' },
    { path: '/app', label: 'Performance', fragment: 'performance' },
    { path: '/app', label: 'Opportunities', fragment: 'opportunities' },
    { path: '/app', label: 'Alerts', fragment: 'alerts' },
    { path: '/app', label: 'Macro', fragment: 'macro' }
  ];

  readonly brandTarget = computed(() => (this.isAuthenticated() ? '/app' : '/login'));
  readonly currentYear = new Date().getFullYear();

  logout(): void {
    this.auth.logout();
    void this.router.navigate(['/login']);
  }
}
