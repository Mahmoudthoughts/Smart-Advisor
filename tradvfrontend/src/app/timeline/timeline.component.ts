import { CommonModule } from '@angular/common';

import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { parseDateString } from '../shared/chart-utils';
import { TvChartComponent, TvLegendItem, TvSeries } from '../shared/tv-chart/tv-chart.component';
import { SeriesMarker, Time } from 'lightweight-charts';

import {
  PortfolioDataService,
  TimelinePricePoint,
  TimelineResponse,
  TimelineSnapshot,
  TimelineTransaction,
  WatchlistSymbol
} from '../portfolio-data.service';

@Component({
  selector: 'app-timeline-page',
  standalone: true,
  imports: [CommonModule, FormsModule, TvChartComponent],
  templateUrl: './timeline.component.html',
  styleUrls: ['./timeline.component.scss']
})
export class TimelineComponent implements OnInit {
  private readonly dataService = inject(PortfolioDataService);

  readonly watchlist = signal<WatchlistSymbol[]>([]);
  readonly selectedSymbol = signal<string>('');
  readonly fromDate = signal<string>('');
  readonly toDate = signal<string>('');
  readonly selectedPreset = signal<string | null>(null);
  readonly snapshots = signal<TimelineSnapshot[]>([]);
  readonly prices = signal<TimelinePricePoint[]>([]);
  readonly transactions = signal<TimelineTransaction[]>([]);
  readonly isLoading = signal<boolean>(false);
  readonly loadError = signal<string | null>(null);

  readonly tableRows = computed(() => {
    const priceLookup = new Map(this.prices().map((point) => [point.date, point.adj_close]));
    return this.snapshots().map((snapshot) => ({
      date: snapshot.date,
      price: priceLookup.get(snapshot.date) ?? null,
      hypoPnl: snapshot.hypo_liquidation_pl_base,
      unrealizedPnl: snapshot.unrealized_pl_base,
      dayOpportunity: snapshot.day_opportunity_base,
    }));
  });

  readonly hasData = computed(() => this.snapshots().length > 0 || this.prices().length > 0);

  readonly timelineSeries = signal<TvSeries[]>([]);
  readonly timelineLegend: TvLegendItem[] = [
    { label: 'Hypo P&L', color: '#38bdf8' },
    { label: 'Realized P&L', color: '#22c55e' },
    { label: 'Unrealized P&L', color: '#6366f1' },
    { label: 'Price', color: '#f97316' },
    { label: 'Average Cost', color: '#f59e0b' }
  ];

  ngOnInit(): void {
    this.loadWatchlist();
  }

  loadWatchlist(): void {
    this.dataService.getWatchlist().subscribe({
      next: (symbols) => {
        this.loadError.set(null);
        this.watchlist.set(symbols);
        if (!this.selectedSymbol() && symbols.length > 0) {
          this.selectedSymbol.set(symbols[0].symbol);
          this.loadTimeline();
        }
      },
      error: () => {
        this.loadError.set('Unable to load watchlist. Add a symbol to begin tracking.');
      }
    });
  }

  loadTimeline(): void {
    const symbol = this.selectedSymbol();
    if (!symbol) {
      return;
    }
    this.isLoading.set(true);
    this.loadError.set(null);
    this.dataService
      .getTimeline(symbol, this.fromDate() || undefined, this.toDate() || undefined)
      .subscribe({
        next: (response: TimelineResponse) => {
          this.snapshots.set(response.snapshots);
          this.prices.set(response.prices);
          this.transactions.set(response.transactions);
          this.updateChart();
          this.isLoading.set(false);
        },
        error: () => {
          this.snapshots.set([]);
          this.prices.set([]);
          this.transactions.set([]);
          this.updateChart();
          this.isLoading.set(false);
          this.loadError.set('Unable to load timeline data for the selected symbol.');
        }
      });
  }

  // Quick date range presets
  applyPreset(preset: 'WTD' | 'MTD' | 'LAST_WEEK' | 'LAST_MONTH' | 'LAST_3M'): void {
    const today = this.atMidnight(new Date());
    let from: Date;
    let to: Date = today;

    switch (preset) {
      case 'WTD': {
        from = this.startOfWeek(today);
        break;
      }
      case 'MTD': {
        from = this.startOfMonth(today);
        break;
      }
      case 'LAST_WEEK': {
        const lastWeekEnd = this.addDays(this.startOfWeek(today), -1);
        const lastWeekStart = this.addDays(this.startOfWeek(today), -7);
        from = lastWeekStart;
        to = lastWeekEnd;
        break;
      }
      case 'LAST_MONTH': {
        const firstOfThisMonth = this.startOfMonth(today);
        const lastOfLastMonth = this.addDays(firstOfThisMonth, -1);
        from = this.startOfMonth(lastOfLastMonth);
        to = lastOfLastMonth;
        break;
      }
      case 'LAST_3M': {
        from = this.addMonths(today, -3);
        break;
      }
    }

    this.selectedPreset.set(preset);
    this.fromDate.set(this.formatDate(from));
    this.toDate.set(this.formatDate(to));
    this.loadTimeline();
  }

  // When user changes dates manually, clear preset selection
  onFromChange(value: string): void {
    this.selectedPreset.set(null);
    this.fromDate.set(value);
  }

  onToChange(value: string): void {
    this.selectedPreset.set(null);
    this.toDate.set(value);
  }

  private atMidnight(d: Date): Date {
    return new Date(d.getFullYear(), d.getMonth(), d.getDate());
  }

  private startOfWeek(d: Date): Date {
    // Monday as start of week
    const day = d.getDay(); // 0 (Sun) .. 6 (Sat)
    const diff = (day + 6) % 7; // days since Monday
    return this.atMidnight(this.addDays(d, -diff));
  }

  private startOfMonth(d: Date): Date {
    return new Date(d.getFullYear(), d.getMonth(), 1);
  }

  private addDays(d: Date, days: number): Date {
    const result = new Date(d);
    result.setDate(result.getDate() + days);
    return this.atMidnight(result);
  }

  private addMonths(d: Date, months: number): Date {
    const year = d.getFullYear();
    const month = d.getMonth();
    const day = d.getDate();
    const result = new Date(year, month + months, day);
    return this.atMidnight(result);
  }

  private formatDate(d: Date): string {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
  }

  onSymbolChange(symbol: string): void {
    this.selectedSymbol.set(symbol);
    this.loadTimeline();
  }

  updateChart(): void {
    const snapshots = this.snapshots();
    const prices = this.prices();
    const transactions = this.transactions();
    if (!snapshots.length && !prices.length) {
      this.timelineSeries.set([]);
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
    const tradeMarkers: SeriesMarker<Time>[] = transactions.map((tx) => {
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

    this.timelineSeries.set(series);
  }
}
