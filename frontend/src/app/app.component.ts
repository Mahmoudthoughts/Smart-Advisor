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
    { path: '/app/overview', label: 'Overview' },
    { path: '/app/timeline', label: 'Timeline' },
    { path: '/app/opportunities', label: 'Opportunities' },
    { path: '/app/signals', label: 'Signals' },
    { path: '/app/sentiment', label: 'Sentiment' },
    { path: '/app/forecast', label: 'Forecast' },
    { path: '/app/simulator', label: 'Simulator' },
    { path: '/app/macro', label: 'Macro' },
    { path: '/app/alerts', label: 'Alerts' }
  ];

  readonly brandTarget = computed(() => (this.isAuthenticated() ? '/app/overview' : '/login'));
  readonly currentYear = new Date().getFullYear();

  logout(): void {
    this.auth.logout();
    void this.router.navigate(['/login']);
  }
}
