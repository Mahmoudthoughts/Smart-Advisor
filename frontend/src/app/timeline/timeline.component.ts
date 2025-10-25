import { CommonModule } from '@angular/common';

import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import type { EChartsOption } from 'echarts';
import { NgxEchartsDirective } from 'ngx-echarts';

import {
  PortfolioDataService,
  TimelinePricePoint,
  TimelineResponse,
  TimelineSnapshot,
  TimelineTransaction,
  WatchlistSymbol,
} from '../portfolio-data.service';

@Component({
  selector: 'app-timeline-page',
  standalone: true,
  imports: [CommonModule, FormsModule, NgxEchartsDirective],
  templateUrl: './timeline.component.html',
  styleUrls: ['./timeline.component.scss']
})
export class TimelineComponent implements OnInit {
  private readonly dataService = inject(PortfolioDataService);

  readonly watchlist = signal<WatchlistSymbol[]>([]);
  readonly selectedSymbol = signal<string>('');
  readonly fromDate = signal<string>('');
  readonly toDate = signal<string>('');
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

  readonly timelineOption = signal<EChartsOption>({
    tooltip: { trigger: 'axis' },
    legend: { data: ['Hypo P&L', 'Unrealized P&L', 'Price', 'Trades'] },
    grid: { left: 32, right: 24, top: 32, bottom: 48 },
    xAxis: { type: 'category', boundaryGap: false, data: [] },
    yAxis: [
      {
        type: 'value',
        axisLabel: {
          formatter: (value: number) => `$${value.toLocaleString()}`
        }
      },
      {
        type: 'value',
        position: 'right',
        axisLabel: {
          formatter: (value: number) => `$${value.toFixed(2)}`
        }
      }
    ],
    series: []
  });

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

  onSymbolChange(symbol: string): void {
    this.selectedSymbol.set(symbol);
    this.loadTimeline();
  }

  updateChart(): void {
    const snapshots = this.snapshots();
    const prices = this.prices();
    const transactions = this.transactions();
    if (!snapshots.length && !prices.length) {
      this.timelineOption.update((option) => ({
        ...option,
        xAxis: { ...option.xAxis, data: [] },
        series: []
      }));
      return;
    }

    const axisDates = snapshots.length ? snapshots.map((snapshot) => snapshot.date) : prices.map((price) => price.date);
    const hypoSeries = snapshots.map((snapshot) => Number(snapshot.hypo_liquidation_pl_base));
    const unrealizedSeries = snapshots.map((snapshot) => Number(snapshot.unrealized_pl_base));
    const priceSeries = prices.map((point) => Number(point.adj_close));
    const tradeMarkers = transactions.map((tx) => {
      const tradeDate = tx.trade_datetime.split('T')[0];
      const markerColor = tx.type === 'SELL' ? '#dc2626' : '#16a34a';
      return {
        name: tx.type,
        value: [tradeDate, Number(tx.price), tx.quantity, tx.notional_value],
        symbol: tx.type === 'SELL' ? 'triangle' : 'circle',
        symbolSize: Math.max(10, Math.min(28, Math.abs(tx.quantity) * 2)),
        itemStyle: { color: markerColor }
      };
    });

    this.timelineOption.set({
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'cross' },
        formatter: (params: any) => {
          const entries = Array.isArray(params) ? params : [params];
          const dateLabel = entries[0]?.axisValueLabel ?? '';
          const lines = entries
            .filter((entry: any) => entry.seriesName !== 'Trades')
            .map((entry: any) => {
              const value = Number(entry.data).toLocaleString(undefined, {
                maximumFractionDigits: entry.seriesName === 'Price' ? 2 : 0
              });
              const prefix = entry.seriesName === 'Price' ? '$' : '$';
              return `${entry.marker} ${entry.seriesName}: ${prefix}${value}`;
            });
          const tradesForDay = transactions.filter((tx) => tx.trade_datetime.startsWith(dateLabel));
          tradesForDay.forEach((tx) => {
            const direction = tx.type === 'SELL' ? 'Sold' : 'Bought';
            const value = (tx.quantity * tx.price).toLocaleString(undefined, { maximumFractionDigits: 2 });
            lines.push(
              `${tx.type === 'SELL' ? '🔻' : '🔺'} ${direction} ${tx.quantity} @ $${tx.price.toFixed(2)} (≈ $${value})`
            );
          });
          return [`<strong>${dateLabel}</strong>`, ...lines].join('<br/>');
        }
      },
      legend: { data: ['Hypo P&L', 'Unrealized P&L', 'Price', 'Trades'] },
      grid: { left: 32, right: 24, top: 32, bottom: 48 },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: axisDates
      },
      yAxis: [
        {
          type: 'value',
          axisLabel: {
            formatter: (value: number) => `$${value.toLocaleString()}`
          }
        },
        {
          type: 'value',
          position: 'right',
          axisLabel: {
            formatter: (value: number) => `$${value.toFixed(2)}`
          }
        }
      ],
      series: [
        {
          name: 'Hypo P&L',
          type: 'line',
          smooth: true,
          symbol: 'circle',
          areaStyle: { opacity: 0.12 },
          data: hypoSeries
        },
        {
          name: 'Unrealized P&L',
          type: 'line',
          smooth: true,
          areaStyle: { opacity: 0.1 },
          data: unrealizedSeries
        },
        {
          name: 'Price',
          type: 'line',
          smooth: true,
          yAxisIndex: 1,
          lineStyle: { width: 2, type: 'dashed' },
          data: priceSeries
        },
        {
          name: 'Trades',
          type: 'scatter',
          yAxisIndex: 1,
          data: tradeMarkers,
          tooltip: {
            formatter: (param: any) => {
              const [, price, quantity, value] = param.value;
              return `${param.seriesName}: ${param.name} ${quantity} @ $${price.toFixed(2)}<br/>Value: $${value.toFixed(2)}`;
            }
          }
        }
      ]
    });
  }
}
