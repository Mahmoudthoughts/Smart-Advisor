import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import type { EChartsOption } from 'echarts';
import { NgxEchartsDirective } from 'ngx-echarts';

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
  imports: [CommonModule, NgxEchartsDirective],
  templateUrl: './sentiment.component.html',
  styleUrls: ['./sentiment.component.scss']
})
export class SentimentComponent {
  readonly heatmapOption: EChartsOption = {
    tooltip: {
      formatter: ({ value }: any) => `${value[0]}<br/>Score ${value[1]}: ${value[2]}`
    },
    grid: { left: 40, right: 16, top: 40, bottom: 40 },
    xAxis: {
      type: 'category',
      data: ['PATH', 'TSLA', 'NVDA', 'LAC']
    },
    yAxis: {
      type: 'category',
      data: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']
    },
    visualMap: {
      min: -1,
      max: 1,
      calculable: true,
      orient: 'horizontal',
      left: 'center',
      bottom: 0
    },
    series: [
      {
        type: 'heatmap',
        data: [
          ['PATH', 'Mon', 0.42],
          ['PATH', 'Tue', 0.61],
          ['PATH', 'Wed', 0.48],
          ['PATH', 'Thu', 0.15],
          ['PATH', 'Fri', -0.12],
          ['TSLA', 'Mon', 0.33],
          ['TSLA', 'Tue', 0.64],
          ['TSLA', 'Wed', 0.58],
          ['TSLA', 'Thu', 0.47],
          ['TSLA', 'Fri', 0.39],
          ['NVDA', 'Mon', 0.12],
          ['NVDA', 'Tue', 0.28],
          ['NVDA', 'Wed', 0.45],
          ['NVDA', 'Thu', 0.52],
          ['NVDA', 'Fri', 0.22],
          ['LAC', 'Mon', -0.34],
          ['LAC', 'Tue', -0.12],
          ['LAC', 'Wed', 0.05],
          ['LAC', 'Thu', 0.18],
          ['LAC', 'Fri', 0.09]
        ].map(([symbol, day, score]) => [symbol, day, score])
      }
    ]
  };

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
