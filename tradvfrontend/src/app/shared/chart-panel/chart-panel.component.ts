import {
  AfterViewInit,
  Component,
  ElementRef,
  Input,
  OnChanges,
  OnDestroy,
  SimpleChanges,
  ViewChild
} from '@angular/core';
import {
  CandlestickData,
  CandlestickSeries,
  ColorType,
  createChart,
  IChartApi,
  ISeriesApi
} from 'lightweight-charts';

@Component({
  selector: 'app-chart-panel',
  standalone: true,
  templateUrl: './chart-panel.component.html',
  styleUrl: './chart-panel.component.scss'
})
export class ChartPanelComponent implements AfterViewInit, OnChanges, OnDestroy {
  @Input({ required: true }) data: CandlestickData[] = [];
  @Input({ required: true }) symbol = '';

  @ViewChild('chartContainer', { static: true })
  chartContainer!: ElementRef<HTMLDivElement>;

  private chart?: IChartApi;
  private series?: ISeriesApi<'Candlestick'>;
  private resizeObserver?: ResizeObserver;

  ngAfterViewInit(): void {
    this.initializeChart();
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['data'] && this.series) {
      this.series.setData(this.data);
      this.chart?.timeScale().fitContent();
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
    const upColor = this.readCssVar(container, '--success-600', '#22c55e');
    const downColor = this.readCssVar(container, '--danger-600', '#ef4444');

    this.chart = createChart(container, {
      height: container.clientHeight || 420,
      layout: {
        background: { type: ColorType.Solid, color: background },
        textColor
      },
      grid: {
        vertLines: { color: gridColor },
        horzLines: { color: gridColor }
      },
      rightPriceScale: {
        borderColor: gridColor
      },
      timeScale: {
        borderColor: gridColor
      },
      crosshair: {
        vertLine: { color: gridColor },
        horzLine: { color: gridColor }
      }
    });

    const series = this.chart.addSeries(CandlestickSeries, {
      upColor,
      downColor,
      borderUpColor: upColor,
      borderDownColor: downColor,
      wickUpColor: upColor,
      wickDownColor: downColor
    });

    this.series = series;
    series.setData(this.data);
    this.chart.timeScale().fitContent();

    this.resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        if (entry.contentRect.width && entry.contentRect.height) {
          this.chart?.applyOptions({
            width: entry.contentRect.width,
            height: entry.contentRect.height
          });
        }
      }
    });
    this.resizeObserver.observe(container);
  }

  private readCssVar(element: HTMLElement, name: string, fallback: string): string {
    const value = getComputedStyle(element).getPropertyValue(name).trim();
    return value || fallback;
  }
}
