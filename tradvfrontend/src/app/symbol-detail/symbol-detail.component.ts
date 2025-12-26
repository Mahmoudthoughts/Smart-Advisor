import { CommonModule } from '@angular/common';
import { Component, OnDestroy, OnInit, computed, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { CurrencyPipe, PercentPipe } from '@angular/common';
import { Subscription } from 'rxjs';
import { parseDateString } from '../shared/chart-utils';
import { TvChartComponent, TvLegendItem, TvSeries } from '../shared/tv-chart/tv-chart.component';
import { SeriesMarker, Time } from 'lightweight-charts';

import {
  PortfolioDataService,
  IntradayBar,
  SymbolRefreshResponse,
  TimelinePricePoint,
  TimelineSnapshot,
  TimelineTransaction,
  WatchlistSymbol,
  SymbolSearchResult
} from '../portfolio-data.service';

interface SymbolSummary {
  readonly lastPrice: number | null;
  readonly change: number | null;
  readonly changePercent: number | null;
  readonly positionQty: number | null;
  readonly averageCost: number | null;
  readonly unrealized: number | null;
  readonly realized: number | null;
  readonly hypo: number | null;
}

interface QuickTradePlan {
  readonly status: 'ready' | 'insufficient';
  readonly sessions: number;
  readonly middayDrawdownPct: number | null;
  readonly closeLiftPct: number | null;
  readonly helper: string;
  readonly fallback: string;
}

@Component({
  selector: 'app-symbol-detail',
  standalone: true,
  imports: [CommonModule, RouterLink, CurrencyPipe, PercentPipe, TvChartComponent],
  templateUrl: './symbol-detail.component.html',
  styleUrls: ['./symbol-detail.component.scss']
})
export class SymbolDetailComponent implements OnInit, OnDestroy {
  private readonly route = inject(ActivatedRoute);
  private readonly dataService = inject(PortfolioDataService);
  private readonly intradayBarSize = '15 mins';
  private readonly intradayDurationDays = 5;
  private readonly intradayMinSessions = 3;
  private readonly middayStartHour = 11;
  private readonly middayEndHour = 13.5;

  private paramSub: Subscription | null = null;

  readonly symbol = signal<string>('');
  readonly isLoading = signal<boolean>(false);
  readonly loadError = signal<string | null>(null);
  readonly refreshStatus = signal<string | null>(null);
  readonly refreshError = signal<string | null>(null);
  readonly watchlistEntry = signal<WatchlistSymbol | null>(null);
  readonly snapshots = signal<TimelineSnapshot[]>([]);
  readonly prices = signal<TimelinePricePoint[]>([]);
  readonly transactions = signal<TimelineTransaction[]>([]);
  readonly intradayBars = signal<IntradayBar[]>([]);
  readonly symbolMeta = signal<SymbolSearchResult | null>(null);
  readonly fromDate = signal<string>('');
  readonly toDate = signal<string>('');
  readonly selectedRange = signal<'1D' | '1W' | '1M' | '3M' | '6M' | '1Y' | '5Y' | null>(null);

  readonly chartSeries = signal<TvSeries[]>([]);
  readonly chartLegend: TvLegendItem[] = [
    { label: 'Hypo P&L', color: '#38bdf8' },
    { label: 'Realized P&L', color: '#22c55e' },
    { label: 'Unrealized P&L', color: '#6366f1' },
    { label: 'Price', color: '#f97316' },
    { label: 'Average Cost', color: '#f59e0b' }
  ];

  readonly summary = computed<SymbolSummary>(() => {
    const entry = this.watchlistEntry();
    const snaps = this.snapshots();
    const lastSnapshot = snaps.length ? snaps[snaps.length - 1] : null;
    return {
      lastPrice: entry?.latest_close ?? null,
      change: entry?.day_change ?? null,
      changePercent: entry?.day_change_percent ?? null,
      positionQty: lastSnapshot ? Number(lastSnapshot.shares_open) : entry?.position_qty ?? null,
      averageCost:
        lastSnapshot && lastSnapshot.shares_open > 0
          ? Number(lastSnapshot.cost_basis_open_base) / Number(lastSnapshot.shares_open)
          : entry?.average_cost ?? null,
      unrealized: lastSnapshot ? Number(lastSnapshot.unrealized_pl_base) : entry?.unrealized_pl ?? null,
      realized: lastSnapshot ? Number(lastSnapshot.realized_pl_to_date_base) : null,
      hypo: lastSnapshot ? Number(lastSnapshot.hypo_liquidation_pl_base) : null
    };
  });

  readonly quickTradePlan = computed<QuickTradePlan>(() => {
    const bars = this.intradayBars();
    const windowLabel = `${this.intradayDurationDays}d`;
    const intervalLabel = this.intradayBarSize;
    if (!bars.length) {
      return {
        status: 'insufficient',
        sessions: 0,
        middayDrawdownPct: null,
        closeLiftPct: null,
        helper: `Scanning ${windowLabel} of ${intervalLabel} bars for midday dips and late-day recoveries (ET).`,
        fallback: `Need at least ${this.intradayMinSessions} recent intraday sessions to estimate the noon drawdown and close lift.`
      };
    }

    type DatedBar = { bar: IntradayBar; timestamp: Date };
    const sessions = new Map<string, DatedBar[]>();
    bars.forEach((bar) => {
      const key = this.getIsoDatePart(bar.date);
      if (!key) {
        return;
      }
      const timestamp = new Date(bar.date);
      if (Number.isNaN(timestamp.getTime())) {
        return;
      }
      const list = sessions.get(key) ?? [];
      list.push({ bar, timestamp });
      sessions.set(key, list);
    });

    const drawdowns: number[] = [];
    const lifts: number[] = [];
    sessions.forEach((items) => {
      const sorted = items.sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime());
      const open = sorted[0]?.bar.open ?? 0;
      const close = sorted[sorted.length - 1]?.bar.close ?? 0;
      const midday = sorted.filter((item) => {
        const hour = this.getIsoHourFraction(item.bar.date);
        if (hour === null) {
          return false;
        }
        return hour >= this.middayStartHour && hour <= this.middayEndHour;
      });
      if (!midday.length || open <= 0 || close <= 0) {
        return;
      }
      const middayLow = Math.min(...midday.map((item) => item.bar.low));
      if (!Number.isFinite(middayLow) || middayLow <= 0) {
        return;
      }
      drawdowns.push((middayLow - open) / open);
      lifts.push((close - middayLow) / middayLow);
    });

    const sessionsUsed = Math.min(drawdowns.length, lifts.length);
    if (sessionsUsed < this.intradayMinSessions) {
      return {
        status: 'insufficient',
        sessions: sessionsUsed,
        middayDrawdownPct: null,
        closeLiftPct: null,
        helper: `Scanning ${windowLabel} of ${intervalLabel} bars for midday dips and late-day recoveries (ET).`,
        fallback: `Only ${sessionsUsed} intraday session${sessionsUsed === 1 ? '' : 's'} found. Need ${this.intradayMinSessions} to estimate the noon drawdown and close lift.`
      };
    }

    return {
      status: 'ready',
      sessions: sessionsUsed,
      middayDrawdownPct: this.median(drawdowns),
      closeLiftPct: this.average(lifts),
      helper: `Based on ${sessionsUsed} sessions in the last ${windowLabel} (${intervalLabel} bars, ET).`,
      fallback: ''
    };
  });

  ngOnInit(): void {
    this.paramSub = this.route.paramMap.subscribe((params) => {
      const symbol = (params.get('symbol') ?? '').toUpperCase();
      this.symbol.set(symbol);
      this.loadWatchlist();
      this.loadTimeline();
      this.loadIntradayBars();
      this.fetchSymbolMeta();
    });
  }

  ngOnDestroy(): void {
    this.paramSub?.unsubscribe();
  }

  loadWatchlist(): void {
    this.dataService.getWatchlist().subscribe({
      next: (items) => {
        const entry = items.find((item) => item.symbol === this.symbol());
        this.watchlistEntry.set(entry ?? null);
      },
      error: () => this.watchlistEntry.set(null)
    });
  }

  loadTimeline(): void {
    const ticker = this.symbol();
    if (!ticker) {
      return;
    }
    this.isLoading.set(true);
    this.loadError.set(null);
    this.dataService.getTimeline(ticker, this.fromDate() || undefined, this.toDate() || undefined).subscribe({
      next: (response) => {
        this.snapshots.set(response.snapshots);
        this.prices.set(response.prices);
        this.transactions.set(response.transactions);
        const firstTxDate = this.findFirstTransactionDate(response.transactions);
        if (!this.fromDate() && firstTxDate) {
          this.fromDate.set(firstTxDate);
        }
        if (!this.toDate()) {
          this.toDate.set(this.formatDate(this.atMidnight(new Date())));
        }
        this.updateChart();
        this.isLoading.set(false);
      },
      error: () => {
        this.snapshots.set([]);
        this.prices.set([]);
        this.transactions.set([]);
        this.updateChart();
        this.isLoading.set(false);
        this.loadError.set('Unable to load analytics for this symbol.');
      }
    });
  }

  loadIntradayBars(): void {
    const ticker = this.symbol();
    if (!ticker) {
      this.intradayBars.set([]);
      return;
    }
    this.dataService
      .getIntradayBars(ticker, {
        barSize: this.intradayBarSize,
        durationDays: this.intradayDurationDays,
        useRth: true
      })
      .subscribe({
        next: (bars) => this.intradayBars.set(bars),
        error: () => this.intradayBars.set([])
      });
  }

  private fetchSymbolMeta(): void {
    const ticker = this.symbol();
    if (!ticker) {
      this.symbolMeta.set(null);
      return;
    }
    this.dataService.searchSymbols(ticker).subscribe({
      next: (results) => {
        const exact = results.find((r) => r.symbol.toUpperCase() === ticker);
        const best = exact || results[0] || null;
        this.symbolMeta.set(best);
      },
      error: () => this.symbolMeta.set(null)
    });
  }

  applyRange(range: '1D' | '1W' | '1M' | '3M' | '6M' | '1Y' | '5Y'): void {
    const today = this.atMidnight(new Date());
    let from = new Date(today);
    let to = today;

    switch (range) {
      case '1D':
        from = this.addDays(today, -1);
        break;
      case '1W':
        from = this.addDays(today, -7);
        break;
      case '1M':
        from = this.addMonths(today, -1);
        break;
      case '3M':
        from = this.addMonths(today, -3);
        break;
      case '6M':
        from = this.addMonths(today, -6);
        break;
      case '1Y':
        from = this.addMonths(today, -12);
        break;
      case '5Y':
        from = this.addMonths(today, -60);
        break;
    }

    this.selectedRange.set(range);
    this.fromDate.set(this.formatDate(from));
    this.toDate.set(this.formatDate(to));
    this.loadTimeline();
  }

  private atMidnight(d: Date): Date {
    return new Date(d.getFullYear(), d.getMonth(), d.getDate());
  }

  private addDays(d: Date, days: number): Date {
    const result = new Date(d);
    result.setDate(result.getDate() + days);
    return this.atMidnight(result);
  }

  private addMonths(d: Date, months: number): Date {
    const y = d.getFullYear();
    const m = d.getMonth();
    const day = d.getDate();
    const result = new Date(y, m + months, day);
    return this.atMidnight(result);
  }

  private formatDate(d: Date): string {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
  }

  private getIsoDatePart(value: string): string | null {
    const [datePart] = value.split('T');
    return datePart || null;
  }

  private getIsoHourFraction(value: string): number | null {
    const [, timePart] = value.split('T');
    if (!timePart) {
      return null;
    }
    const parts = timePart.split(':');
    if (parts.length < 2) {
      return null;
    }
    const hour = Number(parts[0]);
    const minute = Number(parts[1]);
    if (Number.isNaN(hour) || Number.isNaN(minute)) {
      return null;
    }
    return hour + minute / 60;
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

  private findFirstTransactionDate(transactions: TimelineTransaction[]): string | null {
    if (!transactions.length) {
      return null;
    }
    return transactions
      .map((tx) => tx.trade_datetime.split('T')[0])
      .reduce((earliest, current) => (current < earliest ? current : earliest));
  }

  refresh(): void {
    const ticker = this.symbol();
    if (!ticker) {
      return;
    }
    this.refreshStatus.set(null);
    this.refreshError.set(null);
    this.dataService.refreshSymbol(ticker).subscribe({
      next: (response: SymbolRefreshResponse) => {
        this.refreshStatus.set(
          `${response.symbol} refreshed (${response.prices_ingested} prices, ${response.snapshots_rebuilt} snapshots).`
        );
        this.loadWatchlist();
        this.loadTimeline();
        this.loadIntradayBars();
      },
      error: (err) => {
        const message = err?.error?.detail ?? 'Unable to refresh market data for this symbol.';
        this.refreshError.set(message);
      }
    });
  }

  private updateChart(): void {
    const rangeStart = this.fromDate();
    const rangeEnd = this.toDate() || this.formatDate(this.atMidnight(new Date()));
    const snapshots = this.snapshots().filter((snapshot) => this.isWithinRange(snapshot.date, rangeStart, rangeEnd));
    const prices = this.prices().filter((price) => this.isWithinRange(price.date, rangeStart, rangeEnd));
    if (!snapshots.length && !prices.length) {
      this.chartSeries.set([]);
      return;
    }

    const axisDates = snapshots.length ? snapshots.map((snapshot) => snapshot.date) : prices.map((price) => price.date);
    const hypoSeries = snapshots.map((snapshot) => Number(snapshot.hypo_liquidation_pl_base));
    const realizedSeries = snapshots.map((snapshot) => Number(snapshot.realized_pl_to_date_base));
    const unrealizedSeries = snapshots.map((snapshot) => Number(snapshot.unrealized_pl_base));
    const priceSeries = prices.map((point) => Number(point.adj_close));
    const averageCostSeries = snapshots.length
      ? snapshots.map((snapshot) =>
          snapshot.shares_open > 0
            ? Number(snapshot.cost_basis_open_base) / Number(snapshot.shares_open)
            : null
        )
      : axisDates.map(() => null);

    const baseDates = axisDates.map((date) => parseDateString(date));
    const transactions = this.transactions();
    const tradeMarkers: SeriesMarker<Time>[] = transactions.map((tx: TimelineTransaction) => {
      const date = parseDateString(tx.trade_datetime.split('T')[0]);
      const isSell = tx.type === 'SELL';
      return {
        time: date,
        position: isSell ? 'aboveBar' : 'belowBar',
        color: isSell ? '#ef4444' : '#22c55e',
        shape: isSell ? 'arrowDown' : 'arrowUp',
        text: `${tx.type} ${tx.quantity}`
      };
    });
    const series: TvSeries[] = [
      {
        type: 'area',
        data: baseDates.map((date, idx) => ({ time: date, value: hypoSeries[idx] })),
        options: {
          lineWidth: 2,
          color: '#38bdf8',
          topColor: 'rgba(56, 189, 248, 0.35)',
          bottomColor: 'rgba(56, 189, 248, 0.05)'
        }
      },
      {
        type: 'line',
        data: baseDates.map((date, idx) => ({ time: date, value: realizedSeries[idx] })),
        options: {
          lineWidth: 2,
          color: '#22c55e'
        }
      },
      {
        type: 'line',
        data: baseDates.map((date, idx) => ({ time: date, value: unrealizedSeries[idx] })),
        options: {
          lineWidth: 2,
          color: '#6366f1'
        }
      },
      {
        type: 'line',
        data: baseDates.map((date, idx) => ({ time: date, value: priceSeries[idx] })),
        options: {
          lineWidth: 2,
          color: '#f97316'
        },
        markers: tradeMarkers
      },
      {
        type: 'line',
        data: baseDates.map((date, idx) =>
          averageCostSeries[idx] === null
            ? { time: date }
            : { time: date, value: averageCostSeries[idx] }
        ),
        options: {
          lineWidth: 1,
          color: '#f59e0b'
        }
      }
    ];

    this.chartSeries.set(series);
  }

  private isWithinRange(date: string, start?: string | null, end?: string | null): boolean {
    if (start && date < start) {
      return false;
    }
    if (end && date > end) {
      return false;
    }
    return true;
  }
}
