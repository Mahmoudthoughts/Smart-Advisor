import {
  AfterViewInit,
  Component,
  ElementRef,
  EventEmitter,
  Input,
  OnChanges,
  OnDestroy,
  Output,
  SimpleChanges,
  ViewChild
} from '@angular/core';
import {
  AreaSeries,
  BarSeries,
  CandlestickSeries,
  ColorType,
  createChart,
  HistogramSeries,
  IChartApi,
  ISeriesApi,
  LineSeries,
  SeriesMarker,
  SeriesType,
  Time
} from 'lightweight-charts';
import { NgFor, NgIf } from '@angular/common';

export type TvSeriesType = 'line' | 'area' | 'histogram' | 'bar' | 'candlestick';

export type TvSeries = {
  name?: string;
  type: TvSeriesType;
  data: any[];
  options?: Record<string, unknown>;
  markers?: SeriesMarker<Time>[];
  legendColor?: string;
};

export type TvLegendItem = {
  label: string;
  color: string;
};

@Component({
  selector: 'app-tv-chart',
  standalone: true,
  imports: [NgIf, NgFor],
  templateUrl: './tv-chart.component.html',
  styleUrl: './tv-chart.component.scss'
})
export class TvChartComponent implements AfterViewInit, OnChanges, OnDestroy {
  @Input({ required: true }) series: TvSeries[] = [];
  @Input() height = 320;
  @Input() showTimeScale = true;
  @Input() showPriceScale = true;
  @Input() autoFit = true;
  @Input() legend: TvLegendItem[] | null = null;

  @Output() chartClick = new EventEmitter<{ time: Time | null }>();

  @ViewChild('chartContainer', { static: true })
  chartContainer!: ElementRef<HTMLDivElement>;

  private chart?: IChartApi;
  private seriesEntries: ISeriesApi<SeriesType>[] = [];
  private resizeObserver?: ResizeObserver;

  ngAfterViewInit(): void {
    this.initializeChart();
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (!this.chart) {
      return;
    }
    if (changes['series']) {
      this.refreshSeries();
    }
  }

  ngOnDestroy(): void {
    this.resizeObserver?.disconnect();
    this.chart?.remove();
  }

  private initializeChart(): void {
    const container = this.chartContainer.nativeElement;
    const background = this.readCssVar(container, '--color-surface', '#111827');
    const textColor = this.readCssVar(container, '--color-text', '#e5e7eb');
    const gridColor = this.readCssVar(container, '--color-border', 'rgba(148,163,184,0.2)');

    this.chart = createChart(container, {
      height: this.height,
      layout: {
        background: { type: ColorType.Solid, color: background },
        textColor
      },
      grid: {
        vertLines: { color: gridColor },
        horzLines: { color: gridColor }
      },
      rightPriceScale: {
        borderColor: gridColor,
        visible: this.showPriceScale
      },
      timeScale: {
        borderColor: gridColor,
        visible: this.showTimeScale
      },
      crosshair: {
        vertLine: { color: gridColor },
        horzLine: { color: gridColor }
      }
    });

    this.chart.subscribeClick((param) => {
      this.chartClick.emit({ time: param.time ?? null });
    });

    this.refreshSeries();

    this.resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        if (entry.contentRect.width && entry.contentRect.height) {
          this.chart?.applyOptions({
            width: entry.contentRect.width,
            height: entry.contentRect.height
          });
          if (this.autoFit) {
            this.chart?.timeScale().fitContent();
          }
        }
      }
    });
    this.resizeObserver.observe(container);
  }

  private refreshSeries(): void {
    if (!this.chart) {
      return;
    }
    this.seriesEntries.forEach((series) => {
      try {
        this.chart?.removeSeries(series);
      } catch {
        // ignore series removal errors during refresh
      }
    });
    this.seriesEntries = [];

    this.series.forEach((entry) => {
      const series = this.addSeries(entry.type, entry.options);
      if (series) {
        series.setData(entry.data ?? []);
        if (entry.markers && 'setMarkers' in series) {
          (series as ISeriesApi<SeriesType> & { setMarkers: (m: SeriesMarker<Time>[]) => void }).setMarkers(
            entry.markers
          );
        }
        this.seriesEntries.push(series);
      }
    });

    if (this.autoFit) {
      this.chart.timeScale().fitContent();
    }
  }

  private addSeries(type: TvSeriesType, options?: Record<string, unknown>): ISeriesApi<SeriesType> | null {
    if (!this.chart) {
      return null;
    }
    switch (type) {
      case 'area':
        return this.chart.addSeries(AreaSeries, options);
      case 'histogram':
        return this.chart.addSeries(HistogramSeries, options);
      case 'bar':
        return this.chart.addSeries(BarSeries, options);
      case 'candlestick':
        return this.chart.addSeries(CandlestickSeries, options);
      case 'line':
      default:
        return this.chart.addSeries(LineSeries, options);
    }
  }

  private readCssVar(element: HTMLElement, name: string, fallback: string): string {
    const value = getComputedStyle(element).getPropertyValue(name).trim();
    return value || fallback;
  }
}
