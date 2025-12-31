// frontend/src/app/positions/positions.component.ts
import { CommonModule } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { CurrencyPipe, PercentPipe } from '@angular/common';
import { PortfolioDataService, WatchlistSymbol } from '../portfolio-data.service';
import { Router, RouterLink } from '@angular/router';

type ViewMode = 'daily_pnl' | 'unrealized_pnl' | 'market_value';

@Component({
  selector: 'app-positions',
  standalone: true,
  imports: [CommonModule, CurrencyPipe, PercentPipe, RouterLink],
  templateUrl: './positions.component.html',
  styleUrls: ['./positions.component.scss']
})
export class PositionsComponent implements OnInit {
  private readonly dataService = inject(PortfolioDataService);
  private readonly router = inject(Router);

  readonly view = signal<ViewMode>('market_value');
  readonly isLoading = signal<boolean>(true);
  readonly loadError = signal<string | null>(null);
  readonly watchlist = signal<WatchlistSymbol[]>([]);

  readonly totals = computed(() => {
    const items = this.watchlist();
    const marketValue = items.reduce((s, it) => s + ((it.position_qty ?? 0) * (it.latest_close ?? 0)), 0);
    const unrealized = items.reduce((s, it) => s + (it.unrealized_pl ?? 0), 0);
    const daily = items.reduce((s, it) => s + ((it.day_change ?? 0) * (it.position_qty ?? 0)), 0);
    return { marketValue, unrealized, daily };
  });

  ngOnInit(): void {
    this.load();
  }

  load(force = false): void {
    this.isLoading.set(true);
    this.loadError.set(null);
    this.dataService.getWatchlist().subscribe({
      next: (items) => {
        this.watchlist.set(items);
        this.isLoading.set(false);
      },
      error: () => {
        this.loadError.set('Unable to load positions. Try again.');
        this.isLoading.set(false);
        this.watchlist.set([]);
      }
    });
  }

  metricValue(row: WatchlistSymbol): number {
    const qty = row.position_qty ?? 0;
    if (this.view() === 'daily_pnl') {
      const dayChange = row.day_change ?? 0;
      return dayChange * qty;
    } else if (this.view() === 'unrealized_pnl') {
      return row.unrealized_pl ?? 0;
    } else {
      return qty * (row.latest_close ?? 0);
    }
  }

  metricSignClass(v: number): string {
    if (v > 0) return 'metric--positive';
    if (v < 0) return 'metric--negative';
    return 'metric--neutral';
  }

  percentClass(pct?: number | null): string {
    if ((pct ?? 0) >= 0) return 'pct--positive';
    return 'pct--negative';
  }

  openDetails(symbol: string): void {
    void this.router.navigate(['/app/symbols', symbol]);
  }
}

