import { CommonModule } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { CurrencyPipe, PercentPipe } from '@angular/common';

import {
  PortfolioDataService,
  SymbolRefreshResponse,
  WatchlistSymbol
} from '../portfolio-data.service';

@Component({
  selector: 'app-my-stocks',
  standalone: true,
  imports: [CommonModule, RouterLink, CurrencyPipe, PercentPipe],
  templateUrl: './my-stocks.component.html',
  styleUrls: ['./my-stocks.component.scss']
})
export class MyStocksComponent implements OnInit {
  private readonly dataService = inject(PortfolioDataService);
  private readonly router = inject(Router);

  readonly isLoading = signal<boolean>(true);
  readonly loadError = signal<string | null>(null);
  readonly refreshStatus = signal<string | null>(null);
  readonly refreshError = signal<string | null>(null);
  readonly watchlist = signal<WatchlistSymbol[]>([]);

  readonly totalUnrealized = computed(() =>
    this.watchlist().reduce((acc, item) => acc + (item.unrealized_pl ?? 0), 0)
  );

  readonly investedSymbols = computed(() =>
    this.watchlist().filter((item) => (item.position_qty ?? 0) !== 0)
  );

  ngOnInit(): void {
    this.loadWatchlist();
  }

  loadWatchlist(): void {
    this.isLoading.set(true);
    this.loadError.set(null);
    this.dataService.getWatchlist().subscribe({
      next: (items) => {
        this.watchlist.set(items);
        this.isLoading.set(false);
      },
      error: () => {
        this.watchlist.set([]);
        this.isLoading.set(false);
        this.loadError.set('Unable to load your symbols. Please try refreshing.');
      }
    });
  }

  viewSymbol(symbol: string): void {
    void this.router.navigate(['/app/symbols', symbol]);
  }

  recordTransaction(symbol: string): void {
    void this.router.navigate(['/app/transactions'], { queryParams: { symbol } });
  }

  refreshSymbol(symbol: string): void {
    this.refreshStatus.set(null);
    this.refreshError.set(null);
    this.dataService.refreshSymbol(symbol).subscribe({
      next: (response: SymbolRefreshResponse) => {
        this.refreshStatus.set(
          `${response.symbol} updated (${response.prices_ingested} prices, ${response.snapshots_rebuilt} snapshots).`
        );
        this.loadWatchlist();
      },
      error: (err) => {
        const message = err?.error?.detail ?? 'Unable to refresh the selected symbol right now.';
        this.refreshError.set(message);
      }
    });
  }

  trackAnother(): void {
    void this.router.navigate(['/app/onboarding']);
  }
}
