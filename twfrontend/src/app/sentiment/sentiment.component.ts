import { CommonModule } from '@angular/common';
import { Component, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { mapLineSeries } from '../shared/chart-utils';
import { createColumnVisibility } from '../shared/column-visibility';
import { TvChartComponent, TvLegendItem, TvSeries } from '../shared/tv-chart/tv-chart.component';

interface SentimentRow {
  readonly date: string;
  readonly symbol: string;
  readonly score: number;
  readonly articles: number;
  readonly highlights: string;
}

@Component({
  selector: 'app-sentiment-page',
  standalone: true,
  imports: [CommonModule, FormsModule, TvChartComponent],
  templateUrl: './sentiment.component.html',
  styleUrls: ['./sentiment.component.scss']
})
export class SentimentComponent {
  private readonly columnDefaults = {
    date: true,
    symbol: true,
    score: true,
    articles: true,
    highlights: true
  };
  private readonly columnState = createColumnVisibility(
    'smart-advisor.tradv.sentiment.columns',
    this.columnDefaults
  );

  readonly tableFirst = signal<boolean>(false);
  readonly columns = this.columnState.visibility;
  readonly setColumnVisibility = this.columnState.setVisibility;
  readonly resetColumns = this.columnState.resetVisibility;

  readonly sentimentSeries: TvSeries[] = [
    {
      name: 'PATH',
      type: 'line',
      data: mapLineSeries([0.42, 0.61, 0.48, 0.15, -0.12]),
      options: { lineWidth: 2, color: '#38bdf8' }
    },
    {
      name: 'TSLA',
      type: 'line',
      data: mapLineSeries([0.33, 0.64, 0.58, 0.47, 0.39]),
      options: { lineWidth: 2, color: '#22c55e' }
    },
    {
      name: 'NVDA',
      type: 'line',
      data: mapLineSeries([0.12, 0.28, 0.45, 0.52, 0.22]),
      options: { lineWidth: 2, color: '#f97316' }
    },
    {
      name: 'LAC',
      type: 'line',
      data: mapLineSeries([-0.34, -0.12, 0.05, 0.18, 0.09]),
      options: { lineWidth: 2, color: '#ef4444' }
    }
  ];

  readonly sentimentLegend: TvLegendItem[] = [
    { label: 'PATH', color: '#38bdf8' },
    { label: 'TSLA', color: '#22c55e' },
    { label: 'NVDA', color: '#f97316' },
    { label: 'LAC', color: '#ef4444' }
  ];

  readonly sentimentRows: SentimentRow[] = [
    {
      date: '2024-03-18',
      symbol: 'PATH',
      score: 0.62,
      articles: 12,
      highlights: 'Coordinated upgrades; tone: bullish; macro easing references.'
    },
    {
      date: '2024-03-18',
      symbol: 'TSLA',
      score: 0.54,
      articles: 18,
      highlights: 'Delivery beat speculation; AI narrative alignment; watch volatility.'
    },
    {
      date: '2024-03-18',
      symbol: 'NVDA',
      score: 0.31,
      articles: 9,
      highlights: 'Supply chain update; AI backlog coverage remained constructive.'
    },
    {
      date: '2024-03-18',
      symbol: 'LAC',
      score: -0.18,
      articles: 6,
      highlights: 'Lithium oversupply concerns tempered by policy support chatter.'
    }
  ];
}
