import { CommonModule } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { forkJoin, of } from 'rxjs';
import { catchError, map, switchMap } from 'rxjs/operators';

import { PortfolioDataService, SymbolSearchResult, TimelineResponse, WatchlistSymbol } from '../portfolio-data.service';
import { mapHistogramSeries } from '../shared/chart-utils';
import { TvChartComponent, TvLegendItem, TvSeries } from '../shared/tv-chart/tv-chart.component';

type GroupKey = 'industry' | 'region' | 'currency';
type MetricKey = 'unrealized' | 'realized' | 'total';

interface HoldingSnapshot {
  readonly symbol: string;
  readonly name: string;
  readonly industry: string;
  readonly region: string;
  readonly currency: string;
  readonly realized: number;
  readonly unrealized: number;
  readonly marketValue: number;
}

interface GroupBucket {
  key: string;
  realized: number;
  unrealized: number;
  total: number;
  metricTotal: number;
  children: {
    name: string;
    value: number;
    symbol: string;
    marketValue: number;
  }[];
}

@Component({
  selector: 'app-portfolio-analysis',
  standalone: true,
  imports: [CommonModule, TvChartComponent],
  templateUrl: './portfolio-analysis.component.html',
  styleUrls: ['./portfolio-analysis.component.scss']
})
export class PortfolioAnalysisComponent implements OnInit {
  private readonly dataService = inject(PortfolioDataService);

  readonly isLoading = signal<boolean>(false);
  readonly loadError = signal<string | null>(null);
  readonly holdings = signal<HoldingSnapshot[]>([]);
  readonly groupBy = signal<GroupKey>('region');
  readonly metric = signal<MetricKey>('total');

  readonly chartSeries = computed<TvSeries[]>(() => this.buildGroupSeries());
  readonly chartLegend = computed<TvLegendItem[]>(() => [
    {
      label: `${this.metricLabel(this.metric())} by ${this.groupBy()}`,
      color: '#38bdf8'
    }
  ]);
  readonly summaryTotals = computed(() => {
    const holdings = this.holdings();
    const realized = holdings.reduce((sum, h) => sum + h.realized, 0);
    const unrealized = holdings.reduce((sum, h) => sum + h.unrealized, 0);
    return {
      realized,
      unrealized,
      total: realized + unrealized
    };
  });

  ngOnInit(): void {
    this.loadData();
  }

  setGroup(key: GroupKey): void {
    this.groupBy.set(key);
  }

  setMetric(key: MetricKey): void {
    this.metric.set(key);
  }

  retry(): void {
    this.loadData();
  }

  private loadData(): void {
    this.isLoading.set(true);
    this.loadError.set(null);
    this.dataService
      .getWatchlist()
      .pipe(
        switchMap((items) => {
          if (!items.length) {
            return of([] as HoldingSnapshot[]);
          }
          const perSymbol = items.map((item) => this.fetchSnapshotForSymbol(item));
          return forkJoin(perSymbol);
        })
      )
      .subscribe({
        next: (rows) => {
          this.holdings.set(rows.filter(Boolean));
          this.isLoading.set(false);
        },
        error: () => {
          this.holdings.set([]);
          this.loadError.set('Unable to load portfolio analysis right now.');
          this.isLoading.set(false);
        }
      });
  }

  private fetchSnapshotForSymbol(item: WatchlistSymbol) {
    return forkJoin({
      timeline: this.dataService.getTimeline(item.symbol).pipe(catchError(() => of(null as TimelineResponse | null))),
      meta: this.dataService.searchSymbols(item.symbol).pipe(catchError(() => of(null as SymbolSearchResult[] | null)))
    }).pipe(
      map(({ timeline, meta }) => {
        const latestSnapshot = timeline?.snapshots?.[timeline.snapshots.length - 1];
        const realized = latestSnapshot ? Number(latestSnapshot.realized_pl_to_date_base) : 0;
        const unrealized = latestSnapshot
          ? Number(latestSnapshot.unrealized_pl_base)
          : Number(item.unrealized_pl ?? 0);
        const marketValue = latestSnapshot
          ? Number(latestSnapshot.market_value_base)
          : (item.latest_close ?? 0) * (item.position_qty ?? 0);

        const bestMeta = this.selectSymbolMeta(item.symbol, meta);
        return {
          symbol: item.symbol,
          name: item.name ?? item.symbol,
          industry: 'Unknown industry',
          region: bestMeta?.region ?? 'Unknown region',
          currency: bestMeta?.currency ?? 'USD',
          realized,
          unrealized,
          marketValue
        } as HoldingSnapshot;
      })
    );
  }

  private selectSymbolMeta(symbol: string, metas: SymbolSearchResult[] | null): SymbolSearchResult | null {
    if (!metas || metas.length === 0) {
      return null;
    }
    const normalized = symbol.toUpperCase();
    const exact = metas.find((meta) => meta.symbol.toUpperCase() === normalized);
    return exact ?? metas[0];
  }

  private buildGroupSeries(): TvSeries[] {
    const buckets = this.groupHoldings(this.holdings(), this.groupBy(), this.metric());
    const values = buckets.map((bucket) => Number(bucket.metricTotal.toFixed(2)));
    return [
      {
        type: 'histogram',
        data: mapHistogramSeries(values, undefined, '#38bdf8'),
        options: {
          priceFormat: { type: 'volume' }
        }
      }
    ];
  }

  private groupHoldings(data: HoldingSnapshot[], groupKey: GroupKey, metric: MetricKey): GroupBucket[] {
    const buckets = new Map<string, GroupBucket>();
    data.forEach((holding) => {
      const key = this.groupKeyValue(holding, groupKey);
      const value = this.metricValue(holding, metric);
      const bucket = buckets.get(key) ?? {
        key,
        realized: 0,
        unrealized: 0,
        total: 0,
        metricTotal: 0,
        children: []
      };
      bucket.realized += holding.realized;
      bucket.unrealized += holding.unrealized;
      bucket.total += holding.realized + holding.unrealized;
      bucket.metricTotal += value;
      bucket.children.push({
        name: holding.name,
        value,
        symbol: holding.symbol,
        marketValue: holding.marketValue
      });
      buckets.set(key, bucket);
    });
    return Array.from(buckets.values()).sort((a, b) => Math.abs(b.metricTotal) - Math.abs(a.metricTotal));
  }

  private groupKeyValue(holding: HoldingSnapshot, key: GroupKey): string {
    if (key === 'industry') {
      return holding.industry || 'Unknown industry';
    }
    if (key === 'currency') {
      return holding.currency || 'Unknown currency';
    }
    return holding.region || 'Unknown region';
  }

  private metricValue(holding: HoldingSnapshot, metric: MetricKey): number {
    if (metric === 'realized') {
      return holding.realized;
    }
    if (metric === 'unrealized') {
      return holding.unrealized;
    }
    return holding.realized + holding.unrealized;
  }

  private colorForValue(value: number): string {
    if (value > 0) {
      return 'rgba(22, 163, 74, 0.8)';
    }
    if (value < 0) {
      return 'rgba(220, 38, 38, 0.8)';
    }
    return 'rgba(99, 102, 241, 0.6)';
  }

  private formatCurrency(value: number, signed = false): string {
    const formatter = new Intl.NumberFormat(undefined, {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: Math.abs(value) >= 1000 ? 0 : 2,
      signDisplay: signed ? 'always' : 'auto'
    });
    return formatter.format(value);
  }

  private metricLabel(metric: MetricKey): string {
    switch (metric) {
      case 'realized':
        return 'Realized P&L';
      case 'unrealized':
        return 'Unrealized P&L';
      default:
        return 'Total P&L';
    }
  }
}
