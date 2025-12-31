import {
  AfterViewInit,
  Component,
  ElementRef,
  EventEmitter,
  Input,
  NgZone,
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
  @Input() showTooltip = false;
  @Input() tooltipMode: 'floating' | 'tracking' | 'magnifier' = 'magnifier';

  @Output() chartClick = new EventEmitter<{ time: Time | null }>();

  @ViewChild('chartContainer', { static: true })
  chartContainer!: ElementRef<HTMLDivElement>;

  private chart?: IChartApi;
  private seriesEntries: ISeriesApi<SeriesType>[] = [];
  private seriesMeta: Array<{ series: ISeriesApi<SeriesType>; name: string }> = [];
  private resizeObserver?: ResizeObserver;
  private containerWidth = 0;
  private containerHeight = 0;

  tooltipVisible = false;
  tooltipDate = '';
  tooltipPrimaryLabel = '';
  tooltipPrimaryValue = '';
  tooltipItems: Array<{ label: string; value: string }> = [];
  tooltipX = 0;
  tooltipY = 0;

  constructor(private readonly ngZone: NgZone) {}

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

    this.chart.subscribeCrosshairMove((param) => {
      if (!this.showTooltip) {
        return;
      }
      this.ngZone.run(() => {
        if (!param || !param.time || !param.point || !param.seriesData) {
          this.tooltipVisible = false;
          return;
        }

        const width = this.containerWidth || this.chartContainer.nativeElement.clientWidth;
        const height = this.containerHeight || this.chartContainer.nativeElement.clientHeight;
        if (
          !width ||
          !height ||
          param.point.x < 0 ||
          param.point.x > width ||
          param.point.y < 0 ||
          param.point.y > height
        ) {
          this.tooltipVisible = false;
          return;
        }

        const items: Array<{ label: string; value: string }> = [];
        this.seriesMeta.forEach((meta, index) => {
          const data = param.seriesData.get(meta.series);
          if (!data) {
            return;
          }
          const value = this.extractValue(data);
          if (value === null || Number.isNaN(value)) {
            return;
          }
          const label = meta.name || `Series ${index + 1}`;
          items.push({ label, value: this.formatNumber(value) });
        });

        if (!items.length) {
          this.tooltipVisible = false;
          return;
        }

        const primaryMeta =
          this.seriesMeta.find((meta) => meta.name.toLowerCase().includes('price')) ?? this.seriesMeta[0];
        if (!primaryMeta) {
          this.tooltipVisible = false;
          return;
        }
        const primaryData = param.seriesData.get(primaryMeta.series);
        const primaryValue = primaryData ? this.extractValue(primaryData) : null;
        if (primaryValue === null || Number.isNaN(primaryValue)) {
          this.tooltipVisible = false;
          return;
        }

        this.tooltipDate = this.formatTime(param.time);
        this.tooltipPrimaryLabel = primaryMeta.name;
        this.tooltipPrimaryValue = this.formatNumber(primaryValue);
        this.tooltipItems = items;
        const tooltipWidth = this.tooltipMode === 'magnifier' ? 200 : 180;
        const tooltipHeight = this.tooltipMode === 'magnifier' ? 96 : 120;
        const tooltipMargin = 12;

        if (this.tooltipMode === 'magnifier') {
          let left = param.point.x - tooltipWidth / 2;
          left = Math.max(0, Math.min(width - tooltipWidth, left));
          this.tooltipX = left;
          this.tooltipY = 0;
        } else if (this.tooltipMode === 'tracking') {
          let left = param.point.x + tooltipMargin;
          if (left > width - tooltipWidth) {
            left = param.point.x - tooltipMargin - tooltipWidth;
          }
          let top = param.point.y + tooltipMargin;
          if (top > height - tooltipHeight) {
            top = param.point.y - tooltipHeight - tooltipMargin;
          }
          this.tooltipX = left;
          this.tooltipY = top;
        } else {
          const primaryY = primaryMeta.series.priceToCoordinate(primaryValue);
          if (primaryY === null) {
            this.tooltipVisible = false;
            return;
          }
          let shiftedCoordinate = param.point.x - tooltipWidth / 2;
          shiftedCoordinate = Math.max(0, Math.min(width - tooltipWidth, shiftedCoordinate));

          const coordinateY =
            primaryY - tooltipHeight - tooltipMargin > 0
              ? primaryY - tooltipHeight - tooltipMargin
              : Math.max(0, Math.min(height - tooltipHeight - tooltipMargin, primaryY + tooltipMargin));

          this.tooltipX = shiftedCoordinate;
          this.tooltipY = coordinateY;
        }
        this.tooltipVisible = true;
      });
    });

    this.refreshSeries();

    this.resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        if (entry.contentRect.width && entry.contentRect.height) {
          this.containerWidth = entry.contentRect.width;
          this.containerHeight = entry.contentRect.height;
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
    this.seriesMeta = [];
    let usesVolumeScale = false;

    this.series.forEach((entry, index) => {
      const series = this.addSeries(entry.type, entry.options);
      if (series) {
        series.setData(entry.data ?? []);
        if (entry.markers && 'setMarkers' in series) {
          (series as ISeriesApi<SeriesType> & { setMarkers: (m: SeriesMarker<Time>[]) => void }).setMarkers(
            entry.markers
          );
        }
        this.seriesEntries.push(series);
        const legendName = this.legend?.[index]?.label;
        this.seriesMeta.push({ series, name: entry.name ?? legendName ?? `Series ${index + 1}` });
        if (entry.options && typeof entry.options === 'object') {
          const priceScaleId = (entry.options as { priceScaleId?: string }).priceScaleId;
          if (priceScaleId === 'volume') {
            usesVolumeScale = true;
          }
        }
      }
    });

    if (usesVolumeScale) {
      this.chart.applyOptions({
        rightPriceScale: {
          scaleMargins: {
            top: 0.1,
            bottom: 0.3
          }
        }
      });
      this.chart.priceScale('volume').applyOptions({
        scaleMargins: {
          top: 0.7,
          bottom: 0
        }
      });
    }

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

  private extractValue(data: any): number | null {
    if (typeof data === 'number') {
      return data;
    }
    if (data && typeof data === 'object') {
      if (typeof data.value === 'number') {
        return data.value;
      }
      if (typeof data.close === 'number') {
        return data.close;
      }
    }
    return null;
  }

  private formatNumber(value: number): string {
    return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
  }

  private formatTime(time: Time): string {
    if (typeof time === 'string') {
      return time;
    }
    if (typeof time === 'number') {
      return new Date(time * 1000).toLocaleDateString();
    }
    if (typeof time === 'object' && time && 'year' in time) {
      const month = String(time.month).padStart(2, '0');
      const day = String(time.day).padStart(2, '0');
      return `${time.year}-${month}-${day}`;
    }
    return '';
  }
}
