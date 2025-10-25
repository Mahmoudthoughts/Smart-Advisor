import { CommonModule } from '@angular/common';
import { Component, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import type { EChartsOption } from 'echarts';
import { NgxEchartsDirective } from 'ngx-echarts';

interface TimelinePoint {
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
  readonly selectedSymbol = signal<string>(this.symbols[0]);
  readonly fromDate = signal<string>('2024-01-01');
  readonly toDate = signal<string>('2024-03-31');

  private readonly data: TimelinePoint[] = [
    { date: '2024-01-05', price: 14.2, hypoPnl: 3200, unrealizedPnl: 2100, dayOpportunity: 700 },
    { date: '2024-01-12', price: 14.6, hypoPnl: 3600, unrealizedPnl: 2300, dayOpportunity: 900 },
    { date: '2024-01-19', price: 15.1, hypoPnl: 4100, unrealizedPnl: 2650, dayOpportunity: 1200 },
    { date: '2024-02-02', price: 15.8, hypoPnl: 4550, unrealizedPnl: 2980, dayOpportunity: 1450 },
    { date: '2024-02-16', price: 15.4, hypoPnl: 4400, unrealizedPnl: 2810, dayOpportunity: 1320 },
    { date: '2024-03-01', price: 16.2, hypoPnl: 4880, unrealizedPnl: 3120, dayOpportunity: 1640 },
    { date: '2024-03-15', price: 16.9, hypoPnl: 5120, unrealizedPnl: 3380, dayOpportunity: 1840 }
  ];

  readonly timelineOption: EChartsOption = {
    tooltip: { trigger: 'axis' },
    legend: { data: ['Hypo P&L', 'Unrealized P&L', 'Price'] },
    grid: { left: 32, right: 16, top: 32, bottom: 48 },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: this.data.map((point) => point.date)
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
        data: this.data.map((point) => (point.hypoPnl / 1000).toFixed(2))
      },
      {
        name: 'Unrealized P&L',
        type: 'line',
        smooth: true,
        areaStyle: { opacity: 0.1 },
        data: this.data.map((point) => (point.unrealizedPnl / 1000).toFixed(2))
      },
      {
        name: 'Price',
        type: 'line',
        smooth: true,
        yAxisIndex: 1,
        lineStyle: { width: 2, type: 'dashed' },
        data: this.data.map((point) => point.price)
      }
    ]
  };

  get filteredData(): TimelinePoint[] {
    return this.data;
  }
}
