// frontend/src/app/positions/positions.component.ts
import { CommonModule } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { CurrencyPipe, PercentPipe } from '@angular/common';
import { PortfolioDataService, WatchlistSymbol } from '../portfolio-data.service';
import { Router, RouterLink } from '@angular/router';

type ViewMode = 'daily_pnl' | 'unrealized_pnl' | 'market_value';
type SortKey = 'alphabet' | 'share_price' | 'change_pct' | 'position';

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
  readonly sortBy = signal<Record<ViewMode, SortKey>>({
    daily_pnl: 'alphabet',
    unrealized_pnl: 'alphabet',
    market_value: 'alphabet'
  });
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

  readonly currentSortKey = computed(() => this.sortBy()[this.view()]);

  readonly sortedWatchlist = computed(() => {
    const items = [...this.watchlist()];
    const key = this.currentSortKey();
    if (key === 'alphabet') {
      return items.sort((a, b) => a.symbol.localeCompare(b.symbol));
    }
    return items.sort((a, b) => this.sortValue(b, key) - this.sortValue(a, key));
  });

  readonly metricScale = computed(() => {
    const values = this.watchlist().map((row) => this.metricValue(row));
    const maxAbs = Math.max(1, ...values.map((v) => Math.abs(v)));
    const max = Math.max(1, ...values.map((v) => v));
    return { maxAbs, max };
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

  setSort(key: SortKey): void {
    const view = this.view();
    this.sortBy.update((current) => ({ ...current, [view]: key }));
  }

  rowBackground(row: WatchlistSymbol): string {
    const value = this.metricValue(row);
    const scale = this.metricScale();
    if (this.view() === 'market_value') {
      const t = this.clamp(value / scale.max, 0, 1);
      const start = this.hexToRgb('#DBEAFE');
      const end = this.hexToRgb('#2563EB');
      const color = this.interpolateColor(start, end, t);
      return `linear-gradient(90deg, ${this.toRgba(color, 0.35)} 0%, ${this.toRgba(color, 0.08)} 70%, rgba(0,0,0,0) 100%), var(--color-surface)`;
    }

    const t = this.clamp(value / scale.maxAbs, -1, 1);
    const neutral = this.hexToRgb('#FFF8F2');
    const neg = this.hexToRgb('#E74C3C');
    const pos = this.hexToRgb('#27AE60');
    const color = t >= 0 ? this.interpolateColor(neutral, pos, t) : this.interpolateColor(neutral, neg, -t);
    return `linear-gradient(90deg, ${this.toRgba(color, 0.32)} 0%, ${this.toRgba(color, 0.08)} 70%, rgba(0,0,0,0) 100%), var(--color-surface)`;
  }

  openDetails(symbol: string): void {
    void this.router.navigate(['/app/symbols', symbol]);
  }

  private sortValue(row: WatchlistSymbol, key: SortKey): number {
    if (key === 'share_price') {
      return row.latest_close ?? Number.NEGATIVE_INFINITY;
    }
    if (key === 'change_pct') {
      return row.day_change_percent ?? Number.NEGATIVE_INFINITY;
    }
    if (key === 'position') {
      return row.position_qty ?? Number.NEGATIVE_INFINITY;
    }
    return 0;
  }

  private clamp(value: number, min: number, max: number): number {
    return Math.min(max, Math.max(min, value));
  }

  private hexToRgb(hex: string): { r: number; g: number; b: number } {
    const normalized = hex.replace('#', '');
    const r = parseInt(normalized.slice(0, 2), 16);
    const g = parseInt(normalized.slice(2, 4), 16);
    const b = parseInt(normalized.slice(4, 6), 16);
    return { r, g, b };
  }

  private interpolateColor(
    from: { r: number; g: number; b: number },
    to: { r: number; g: number; b: number },
    t: number
  ): { r: number; g: number; b: number } {
    return {
      r: Math.round(from.r + (to.r - from.r) * t),
      g: Math.round(from.g + (to.g - from.g) * t),
      b: Math.round(from.b + (to.b - from.b) * t)
    };
  }

  private toRgba(color: { r: number; g: number; b: number }, alpha: number): string {
    return `rgba(${color.r}, ${color.g}, ${color.b}, ${alpha})`;
  }
}
