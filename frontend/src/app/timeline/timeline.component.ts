import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import type { EChartsOption } from 'echarts';
import { NgxEchartsDirective } from 'ngx-echarts';

interface TimelinePoint {
  readonly symbol: string;
  readonly date: string;
  readonly price: number;
  readonly hypoPnl: number;
  readonly unrealizedPnl: number;
  readonly dayOpportunity: number;
}

@Component({
  selector: 'app-timeline-page',
  standalone: true,
  imports: [CommonModule, FormsModule, NgxEchartsDirective],
  templateUrl: './timeline.component.html',
  styleUrls: ['./timeline.component.scss']
})
export class TimelineComponent {
  readonly symbols = ['PATH', 'TSLA', 'NVDA', 'LAC'];
  selectedSymbol = this.symbols[0];
  fromDate = '2024-01-01';
  toDate = '2024-03-31';

  private readonly data: TimelinePoint[] = [
    { symbol: 'PATH', date: '2024-01-05', price: 14.2, hypoPnl: 3200, unrealizedPnl: 2100, dayOpportunity: 700 },
    { symbol: 'PATH', date: '2024-01-12', price: 14.6, hypoPnl: 3600, unrealizedPnl: 2300, dayOpportunity: 900 },
    { symbol: 'PATH', date: '2024-01-19', price: 15.1, hypoPnl: 4100, unrealizedPnl: 2650, dayOpportunity: 1200 },
    { symbol: 'PATH', date: '2024-02-02', price: 15.8, hypoPnl: 4550, unrealizedPnl: 2980, dayOpportunity: 1450 },
    { symbol: 'PATH', date: '2024-02-16', price: 15.4, hypoPnl: 4400, unrealizedPnl: 2810, dayOpportunity: 1320 },
    { symbol: 'PATH', date: '2024-03-01', price: 16.2, hypoPnl: 4880, unrealizedPnl: 3120, dayOpportunity: 1640 },
    { symbol: 'PATH', date: '2024-03-15', price: 16.9, hypoPnl: 5120, unrealizedPnl: 3380, dayOpportunity: 1840 },
    { symbol: 'TSLA', date: '2024-01-05', price: 206.1, hypoPnl: 5800, unrealizedPnl: 4300, dayOpportunity: 1600 },
    { symbol: 'TSLA', date: '2024-03-15', price: 219.4, hypoPnl: 7260, unrealizedPnl: 5140, dayOpportunity: 2420 }
  ];

  get filteredData(): TimelinePoint[] {
    return this.data.filter((point) => {
      if (point.symbol !== this.selectedSymbol) {
        return false;
      }

      return point.date >= this.fromDate && point.date <= this.toDate;
    });
  }

  get timelineOption(): EChartsOption {
    const rows = this.filteredData;
    const dates = rows.map((point) => point.date);

    return {
      tooltip: { trigger: 'axis' },
      legend: { data: ['Hypo P&L', 'Unrealized P&L', 'Price'] },
      grid: { left: 32, right: 16, top: 32, bottom: 48 },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: dates
      },
      yAxis: [
        {
          type: 'value',
          axisLabel: { formatter: '${value}k' }
        },
        {
          type: 'value',
          position: 'right',
          axisLabel: { formatter: '${value}' }
        }
      ],
      series: [
        {
          name: 'Hypo P&L',
          type: 'line',
          smooth: true,
          symbol: 'circle',
          areaStyle: { opacity: 0.1 },
          data: rows.map((point) => Number((point.hypoPnl / 1000).toFixed(2)))
        },
        {
          name: 'Unrealized P&L',
          type: 'line',
          smooth: true,
          areaStyle: { opacity: 0.1 },
          data: rows.map((point) => Number((point.unrealizedPnl / 1000).toFixed(2)))
        },
        {
          name: 'Price',
          type: 'line',
          smooth: true,
          yAxisIndex: 1,
          lineStyle: { width: 2, type: 'dashed' },
          data: rows.map((point) => point.price)
        }
      ]
    } satisfies EChartsOption;
  }
}
