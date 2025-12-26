import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { mapLineSeries } from '../shared/chart-utils';
import { TvChartComponent, TvSeries } from '../shared/tv-chart/tv-chart.component';

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
  imports: [CommonModule, TvChartComponent],
  templateUrl: './sentiment.component.html',
  styleUrls: ['./sentiment.component.scss']
})
export class SentimentComponent {
  readonly sentimentSeries: TvSeries[] = [
    {
      type: 'line',
      data: mapLineSeries([0.42, 0.61, 0.48, 0.15, -0.12]),
      options: { lineWidth: 2, color: '#38bdf8' }
    },
    {
      type: 'line',
      data: mapLineSeries([0.33, 0.64, 0.58, 0.47, 0.39]),
      options: { lineWidth: 2, color: '#22c55e' }
    },
    {
      type: 'line',
      data: mapLineSeries([0.12, 0.28, 0.45, 0.52, 0.22]),
      options: { lineWidth: 2, color: '#f97316' }
    },
    {
      type: 'line',
      data: mapLineSeries([-0.34, -0.12, 0.05, 0.18, 0.09]),
      options: { lineWidth: 2, color: '#ef4444' }
    }
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
