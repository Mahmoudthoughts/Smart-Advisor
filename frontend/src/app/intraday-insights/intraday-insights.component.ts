import { CommonModule } from '@angular/common';
import { Component, OnDestroy, OnInit, computed, inject, signal } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { CurrencyPipe, PercentPipe } from '@angular/common';
import { Subscription } from 'rxjs';

import { IntradayBar, PortfolioDataService, WatchlistSymbol } from '../portfolio-data.service';

type SessionSummary = {
  readonly date: string;
  readonly bars: number;
  readonly open: number | null;
  readonly middayLow: number | null;
  readonly close: number | null;
  readonly drawdownPct: number | null;
  readonly recoveryPct: number | null;
};

type IntradaySummary = {
  readonly status: 'ready' | 'insufficient';
  readonly sessions: number;
  readonly middayDrawdownPct: number | null;
  readonly closeLiftPct: number | null;
  readonly helper: string;
  readonly fallback: string;
};

@Component({
  selector: 'app-intraday-insights',
  standalone: true,
  imports: [CommonModule, RouterLink, CurrencyPipe, PercentPipe],
  templateUrl: './intraday-insights.component.html',
  styleUrls: ['./intraday-insights.component.scss']
})
export class IntradayInsightsComponent implements OnInit, OnDestroy {
  private readonly dataService = inject(PortfolioDataService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private querySub: Subscription | null = null;

  private readonly intradayMinSessions = 3;
  private readonly middayStartHour = 11;
  private readonly middayEndHour = 13.5;

  readonly watchlist = signal<WatchlistSymbol[]>([]);
  readonly selectedSymbol = signal<string>('');
  readonly bars = signal<IntradayBar[]>([]);
  readonly isLoading = signal<boolean>(false);
  readonly loadError = signal<string | null>(null);
  readonly lastUpdated = signal<string | null>(null);

  readonly barSize = signal<string>('15 mins');
  readonly durationDays = signal<number>(5);
  readonly useRth = signal<boolean>(true);
  readonly barSizeOptions = ['5 mins', '15 mins', '30 mins', '1 hour'];

  readonly sortedBars = computed(() => {
    return [...this.bars()].sort((a, b) => this.parseBarDate(a.date) - this.parseBarDate(b.date));
  });

  readonly sessionSummaries = computed<SessionSummary[]>(() => {
    const grouped = new Map<string, IntradayBar[]>();
    this.sortedBars().forEach((bar) => {
      const timestamp = new Date(bar.date);
      if (Number.isNaN(timestamp.getTime())) {
        return;
      }
      const key = this.formatDayKey(timestamp);
      const list = grouped.get(key) ?? [];
      list.push(bar);
      grouped.set(key, list);
    });

    const summaries: SessionSummary[] = [];
    grouped.forEach((items, date) => {
      const sorted = [...items].sort((a, b) => this.parseBarDate(a.date) - this.parseBarDate(b.date));
      const open = sorted[0]?.open ?? null;
      const close = sorted[sorted.length - 1]?.close ?? null;
      const midday = sorted.filter((bar) => {
        const timestamp = new Date(bar.date);
        const hour = this.getHourFraction(timestamp);
        return hour >= this.middayStartHour && hour <= this.middayEndHour;
      });
      const middayLow = midday.length ? Math.min(...midday.map((bar) => bar.low)) : null;
      const drawdownPct =
        open && middayLow ? (middayLow - open) / open : null;
      const recoveryPct =
        middayLow && close ? (close - middayLow) / middayLow : null;

      summaries.push({
        date,
        bars: sorted.length,
        open,
        middayLow,
        close,
        drawdownPct,
        recoveryPct
      });
    });
    return summaries.sort((a, b) => (a.date < b.date ? 1 : -1));
  });

  readonly intradaySummary = computed<IntradaySummary>(() => {
    const summaries = this.sessionSummaries();
    const drawdowns = summaries
      .map((summary) => summary.drawdownPct)
      .filter((value): value is number => value !== null && Number.isFinite(value));
    const lifts = summaries
      .map((summary) => summary.recoveryPct)
      .filter((value): value is number => value !== null && Number.isFinite(value));
    const sessionsUsed = Math.min(drawdowns.length, lifts.length);
    const windowLabel = `${this.durationDays()}d`;
    const intervalLabel = this.barSize();
    if (sessionsUsed < this.intradayMinSessions) {
      return {
        status: 'insufficient',
        sessions: sessionsUsed,
        middayDrawdownPct: null,
        closeLiftPct: null,
        helper: `Scanning ${windowLabel} of ${intervalLabel} bars for midday dips and late-day recoveries.`,
        fallback: `Only ${sessionsUsed} intraday session${sessionsUsed === 1 ? '' : 's'} found. Need ${this.intradayMinSessions} to estimate the noon drawdown and close lift.`
      };
    }
    return {
      status: 'ready',
      sessions: sessionsUsed,
      middayDrawdownPct: this.median(drawdowns),
      closeLiftPct: this.average(lifts),
      helper: `Based on ${sessionsUsed} sessions in the last ${windowLabel} (${intervalLabel} bars).`,
      fallback: ''
    };
  });

  ngOnInit(): void {
    this.loadWatchlist();
    this.querySub = this.route.queryParamMap.subscribe((params) => {
      const symbol = (params.get('symbol') ?? '').toUpperCase();
      if (symbol && symbol !== this.selectedSymbol()) {
        this.selectedSymbol.set(symbol);
        this.loadBars();
      }
    });
  }

  ngOnDestroy(): void {
    this.querySub?.unsubscribe();
  }

  loadWatchlist(): void {
    this.dataService.getWatchlist().subscribe({
      next: (items) => {
        this.watchlist.set(items);
        if (!this.selectedSymbol() && items.length) {
          const first = items[0].symbol;
          this.selectedSymbol.set(first);
          void this.router.navigate(['/app/intraday-insights'], { queryParams: { symbol: first } });
          this.loadBars();
        }
      },
      error: () => this.watchlist.set([])
    });
  }

  onSymbolChange(symbol: string): void {
    if (!symbol || symbol === this.selectedSymbol()) {
      return;
    }
    this.selectedSymbol.set(symbol);
    void this.router.navigate(['/app/intraday-insights'], { queryParams: { symbol } });
    this.loadBars();
  }

  applyOptions(): void {
    this.loadBars();
  }

  loadBars(): void {
    const symbol = this.selectedSymbol();
    if (!symbol) {
      this.bars.set([]);
      this.isLoading.set(false);
      return;
    }
    this.isLoading.set(true);
    this.loadError.set(null);
    this.dataService
      .getIntradayBars(symbol, {
        barSize: this.barSize(),
        durationDays: this.durationDays(),
        useRth: this.useRth()
      })
      .subscribe({
        next: (bars) => {
          this.bars.set(bars);
          this.isLoading.set(false);
          this.lastUpdated.set(new Date().toLocaleString());
        },
        error: () => {
          this.bars.set([]);
          this.isLoading.set(false);
          this.loadError.set('Unable to load intraday bars right now.');
        }
      });
  }

  viewSymbolDetail(): void {
    const symbol = this.selectedSymbol();
    if (!symbol) {
      return;
    }
    void this.router.navigate(['/app/symbols', symbol]);
  }

  private parseBarDate(value: string): number {
    return new Date(value).getTime();
  }

  private formatDayKey(d: Date): string {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
  }

  private getHourFraction(d: Date): number {
    return d.getHours() + d.getMinutes() / 60;
  }

  private average(values: number[]): number {
    if (!values.length) {
      return 0;
    }
    const total = values.reduce((sum, value) => sum + value, 0);
    return total / values.length;
  }

  private median(values: number[]): number {
    if (!values.length) {
      return 0;
    }
    const sorted = [...values].sort((a, b) => a - b);
    const mid = Math.floor(sorted.length / 2);
    if (sorted.length % 2 === 0) {
      return (sorted[mid - 1] + sorted[mid]) / 2;
    }
    return sorted[mid];
  }
}
