import { CommonModule } from '@angular/common';
import { Component, OnDestroy, OnInit, computed, inject, signal } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { CurrencyPipe, PercentPipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Subscription } from 'rxjs';
import { SeriesMarker, Time } from 'lightweight-charts';

import { IntradayBar, PortfolioDataService, WatchlistSymbol } from '../portfolio-data.service';
import { AiTimingResponse, AiTimingService } from '../services/ai-timing.service';
import { createColumnVisibility } from '../shared/column-visibility';
import { TvChartComponent, TvLegendItem, TvSeries } from '../shared/tv-chart/tv-chart.component';

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
  imports: [CommonModule, FormsModule, RouterLink, CurrencyPipe, PercentPipe, TvChartComponent],
  templateUrl: './intraday-insights.component.html',
  styleUrls: ['./intraday-insights.component.scss']
})
export class IntradayInsightsComponent implements OnInit, OnDestroy {
  private readonly dataService = inject(PortfolioDataService);
  private readonly aiTiming = inject(AiTimingService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private querySub: Subscription | null = null;
  private readonly sessionColumnDefaults = {
    date: true,
    bars: true,
    open: true,
    middayLow: true,
    close: true,
    drawdownPct: true,
    recoveryPct: true
  };
  private readonly barColumnDefaults = {
    date: true,
    open: true,
    high: true,
    low: true,
    close: true,
    volume: true
  };
  private readonly sessionColumnState = createColumnVisibility(
    'smart-advisor.tradv.intraday.sessions.columns',
    this.sessionColumnDefaults
  );
  private readonly barColumnState = createColumnVisibility(
    'smart-advisor.tradv.intraday.bars.columns',
    this.barColumnDefaults
  );

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
  readonly aiTimezone = signal<string>('US/Eastern');
  readonly tableFirst = signal<boolean>(false);
  readonly rawBarsView = signal<'table' | 'chart'>('table');
  readonly sessionColumns = this.sessionColumnState.visibility;
  readonly setSessionColumnVisibility = this.sessionColumnState.setVisibility;
  readonly resetSessionColumns = this.sessionColumnState.resetVisibility;
  readonly barColumns = this.barColumnState.visibility;
  readonly setBarColumnVisibility = this.barColumnState.setVisibility;
  readonly resetBarColumns = this.barColumnState.resetVisibility;

  readonly sortedBars = computed(() => {
    return [...this.bars()].sort((a, b) => this.parseBarDate(a.date) - this.parseBarDate(b.date));
  });

  readonly rawBarSeries = computed<TvSeries[]>(() => {
    const bars = this.sortedBars();
    if (!bars.length) {
      return [];
    }
    const candleData = bars
      .map((bar) => {
        const timestamp = Math.floor(this.parseBarDate(bar.date) / 1000);
        if (!Number.isFinite(timestamp) || timestamp <= 0) {
          return null;
        }
        return {
          time: timestamp as Time,
          open: bar.open,
          high: bar.high,
          low: bar.low,
          close: bar.close
        };
      })
      .filter((entry) => entry !== null);

    if (!candleData.length) {
      return [];
    }

    const volumeData = bars
      .map((bar) => {
        const timestamp = Math.floor(this.parseBarDate(bar.date) / 1000);
        if (!Number.isFinite(timestamp) || timestamp <= 0) {
          return null;
        }
        const isUp = bar.close >= bar.open;
        return {
          time: timestamp as Time,
          value: bar.volume,
          color: isUp ? '#22c55e' : '#ef4444'
        };
      })
      .filter((entry) => entry !== null);

    return [
      {
        name: 'Price',
        type: 'candlestick',
        data: candleData,
        options: {
          upColor: '#22c55e',
          downColor: '#ef4444',
          borderVisible: false,
          wickUpColor: '#22c55e',
          wickDownColor: '#ef4444'
        }
      },
      {
        name: 'Volume',
        type: 'histogram',
        data: volumeData,
        options: {
          priceScaleId: 'volume',
          priceFormat: { type: 'volume' }
        }
      }
    ];
  });

  readonly sessionGroups = computed(() => {
    const grouped = new Map<string, IntradayBar[]>();
    this.sortedBars().forEach((bar) => {
      const key = this.getIsoDatePart(bar.date);
      if (!key) {
        return;
      }
      const list = grouped.get(key) ?? [];
      list.push(bar);
      grouped.set(key, list);
    });
    return grouped;
  });

  readonly sessionDates = computed(() => {
    return Array.from(this.sessionGroups().keys()).sort((a, b) => (a < b ? -1 : 1));
  });

  readonly selectedSessions = signal<string[]>([]);
  readonly aiLoading = signal<boolean>(false);
  readonly aiError = signal<string | null>(null);
  readonly aiResult = signal<AiTimingResponse | null>(null);

  readonly selectedSymbolName = computed(() => {
    const symbol = this.selectedSymbol();
    const entry = this.watchlist().find((row) => row.symbol === symbol);
    return entry?.name ?? null;
  });

  readonly sessionSummaries = computed<SessionSummary[]>(() => {
    const summaries: SessionSummary[] = [];
    this.sessionGroups().forEach((items, date) => {
      const sorted = [...items].sort((a, b) => this.parseBarDate(a.date) - this.parseBarDate(b.date));
      const open = sorted[0]?.open ?? null;
      const close = sorted[sorted.length - 1]?.close ?? null;
      const midday = sorted.filter((bar) => {
        const hour = this.getIsoHourFraction(bar.date);
        if (hour === null) {
          return false;
        }
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

  readonly activeSessionDates = computed(() => {
    const selected = new Set(this.selectedSessions());
    const all = this.sessionDates();
    if (!selected.size) {
      return all;
    }
    return all.filter((date) => selected.has(date));
  });

  readonly overlaySeries = computed<TvSeries[]>(() => {
    const palette = ['#38bdf8', '#22c55e', '#f97316', '#6366f1', '#ef4444', '#14b8a6', '#eab308'];
    const baseTimestamp = Date.UTC(2000, 0, 1) / 1000;
    let colorIndex = 0;
    const series: TvSeries[] = [];

    this.activeSessionDates().forEach((date) => {
      const items = this.sessionGroups().get(date) ?? [];
        const color = palette[colorIndex % palette.length];
        colorIndex += 1;
        const points = items
          .slice()
          .sort((a, b) => this.parseBarDate(a.date) - this.parseBarDate(b.date))
          .map((bar) => ({
            time: (baseTimestamp + this.minutesSinceMidnight(bar.date) * 60) as Time,
            value: bar.close
          }));

        series.push({
          name: date,
          type: 'line',
          data: points,
          options: {
            lineWidth: 2,
            color
          },
          legendColor: color
        });
    });

    return series;
  });

  readonly averageSessionSeries = computed<TvSeries>(() => {
    const baseTimestamp = Date.UTC(2000, 0, 1) / 1000;
    const minuteBuckets = new Map<number, number[]>();

    this.activeSessionDates().forEach((date) => {
      const items = this.sessionGroups().get(date) ?? [];
      items.forEach((bar) => {
        const minute = this.minutesSinceMidnight(bar.date);
        const list = minuteBuckets.get(minute) ?? [];
        list.push(bar.close);
        minuteBuckets.set(minute, list);
      });
    });

    const sortedMinutes = Array.from(minuteBuckets.entries()).sort(([a], [b]) => a - b);
    const minuteToAvg = new Map<number, number>();
    const points = sortedMinutes.map(([minute, values]) => {
      const avg = values.reduce((sum, v) => sum + v, 0) / values.length;
      minuteToAvg.set(minute, avg);
      return {
        time: (baseTimestamp + minute * 60) as Time,
        value: avg
      };
    });

    const [medianLowMinute, medianHighMinute] = this.medianLowHighMinutes();
    const lowPrice = minuteToAvg.get(medianLowMinute) ?? points[0]?.value ?? 0;
    const highPrice = minuteToAvg.get(medianHighMinute) ?? points[points.length - 1]?.value ?? 0;
    const markers: SeriesMarker<Time>[] = [
      {
        time: (baseTimestamp + medianLowMinute * 60) as Time,
        position: 'belowBar',
        color: '#ef4444',
        shape: 'circle',
        text: `Median low ${this.formatMinuteLabel(medianLowMinute)}`,
        price: lowPrice
      },
      {
        time: (baseTimestamp + medianHighMinute * 60) as Time,
        position: 'aboveBar',
        color: '#22c55e',
        shape: 'circle',
        text: `Median high ${this.formatMinuteLabel(medianHighMinute)}`,
        price: highPrice
      }
    ];

    return {
      name: 'Average session',
      type: 'line',
      data: points,
      options: {
        lineWidth: 3,
        color: '#0ea5e9'
      },
      legendColor: '#0ea5e9',
      markers
    };
  });

  readonly overlayLegend = computed<TvLegendItem[]>(() => {
    const legend = this.overlaySeries().map((entry) => ({
      label: entry.name ?? 'Session',
      color: entry.legendColor ?? '#38bdf8'
    }));
    return [{ label: 'Average session', color: '#0ea5e9' }, ...legend];
  });

  readonly overlayCombinedSeries = computed<TvSeries[]>(() => {
    const series = [...this.overlaySeries()];
    const average = this.averageSessionSeries();
    return average.data.length ? [average, ...series] : series;
  });

  readonly medianLowTime = computed(() => this.formatMinuteLabel(this.medianLowHighMinutes()[0]));
  readonly medianHighTime = computed(() => this.formatMinuteLabel(this.medianLowHighMinutes()[1]));

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
          this.syncSelectedSessions();
          this.requestAiTiming();
        },
        error: () => {
          this.bars.set([]);
          this.isLoading.set(false);
          this.loadError.set('Unable to load intraday bars right now.');
          this.aiResult.set(null);
          this.aiError.set('AI timing insight unavailable until bars load.');
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

  private minutesSinceMidnight(value: string): number {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return 0;
    }
    return date.getUTCHours() * 60 + date.getUTCMinutes();
  }

  private medianLowHighMinutes(): [number, number] {
    const lows: number[] = [];
    const highs: number[] = [];
    this.activeSessionDates().forEach((date) => {
      const items = this.sessionGroups().get(date) ?? [];
      if (!items.length) {
        return;
      }
      let low = Number.POSITIVE_INFINITY;
      let lowMinute = 0;
      let high = Number.NEGATIVE_INFINITY;
      let highMinute = 0;
      items.forEach((bar) => {
        if (bar.close < low) {
          low = bar.close;
          lowMinute = this.minutesSinceMidnight(bar.date);
        }
        if (bar.close > high) {
          high = bar.close;
          highMinute = this.minutesSinceMidnight(bar.date);
        }
      });
      lows.push(lowMinute);
      highs.push(highMinute);
    });
    return [this.median(lows) || 0, this.median(highs) || 0];
  }

  private formatMinuteLabel(minute: number): string {
    const hours = Math.floor(minute / 60);
    const mins = minute % 60;
    return `${String(hours).padStart(2, '0')}:${String(mins).padStart(2, '0')}`;
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

  toggleSession(date: string): void {
    this.selectedSessions.update((current) => {
      const next = new Set(current);
      if (next.has(date)) {
        next.delete(date);
      } else {
        next.add(date);
      }
      return Array.from(next);
    });
  }

  selectAllSessions(): void {
    this.selectedSessions.set(this.sessionDates());
  }

  clearAllSessions(): void {
    this.selectedSessions.set([]);
  }

  private syncSelectedSessions(): void {
    const available = this.sessionDates();
    const selected = new Set(this.selectedSessions());
    if (!selected.size) {
      this.selectedSessions.set(available);
      return;
    }
    const filtered = available.filter((date) => selected.has(date));
    this.selectedSessions.set(filtered.length ? filtered : available);
  }

  requestAiTiming(forceRefresh = false): void {
    const symbol = this.selectedSymbol();
    const bars = this.sortedBars();
    if (!symbol || bars.length === 0) {
      this.aiResult.set(null);
      return;
    }
    this.aiLoading.set(true);
    this.aiError.set(null);
    const payload = {
      symbol,
      bar_size: this.barSize(),
      duration_days: this.durationDays(),
      timezone: this.aiTimezone(),
      use_rth: this.useRth(),
      force_refresh: forceRefresh,
      symbol_name: this.selectedSymbolName(),
      session_summaries: this.sessionSummaries().map((summary) => ({
        date: summary.date,
        bars: summary.bars,
        open: summary.open,
        midday_low: summary.middayLow,
        close: summary.close,
        drawdown_pct: summary.drawdownPct,
        recovery_pct: summary.recoveryPct
      })),
      bars: bars.map((bar) => ({
        date: bar.date,
        open: bar.open,
        high: bar.high,
        low: bar.low,
        close: bar.close,
        volume: bar.volume
      }))
    };
    this.aiTiming.getTiming(payload).subscribe({
      next: (response) => {
        this.aiResult.set(response);
        this.aiLoading.set(false);
      },
      error: (err) => {
        const detail = err?.error?.detail ?? 'Unable to load AI timing insight right now.';
        this.aiError.set(detail);
        this.aiResult.set(null);
        this.aiLoading.set(false);
      }
    });
  }
}
