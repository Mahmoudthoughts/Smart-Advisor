import {
  AreaData,
  BarData,
  BusinessDay,
  CandlestickData,
  HistogramData,
  LineData
} from 'lightweight-charts';

export function toBusinessDay(date: Date): BusinessDay {
  return {
    year: date.getUTCFullYear(),
    month: date.getUTCMonth() + 1,
    day: date.getUTCDate()
  };
}

export function parseDateString(date: string): BusinessDay {
  const [year, month, day] = date.split('-').map((part) => Number(part));
  return { year, month, day };
}

export function businessDayToString(day: BusinessDay): string {
  const month = String(day.month).padStart(2, '0');
  const date = String(day.day).padStart(2, '0');
  return `${day.year}-${month}-${date}`;
}

export function buildSequentialDays(count: number, endDate: Date = new Date()): BusinessDay[] {
  const days: BusinessDay[] = [];
  for (let i = count - 1; i >= 0; i -= 1) {
    const d = new Date(endDate);
    d.setUTCDate(endDate.getUTCDate() - i);
    days.push(toBusinessDay(d));
  }
  return days;
}

export function mapLineSeries(values: number[], endDate?: Date): LineData[] {
  const days = buildSequentialDays(values.length, endDate);
  return values.map((value, idx) => ({
    time: days[idx],
    value
  }));
}

export function mapAreaSeries(values: number[], endDate?: Date): AreaData[] {
  const days = buildSequentialDays(values.length, endDate);
  return values.map((value, idx) => ({
    time: days[idx],
    value
  }));
}

export function mapHistogramSeries(values: number[], endDate?: Date, color?: string): HistogramData[] {
  const days = buildSequentialDays(values.length, endDate);
  return values.map((value, idx) => ({
    time: days[idx],
    value,
    color
  }));
}

export function mapBarSeries(ohlc: Array<[number, number, number, number]>, endDate?: Date): BarData[] {
  const days = buildSequentialDays(ohlc.length, endDate);
  return ohlc.map(([open, high, low, close], idx) => ({
    time: days[idx],
    open,
    high,
    low,
    close
  }));
}

export function mapCandles(ohlc: Array<[number, number, number, number]>, endDate?: Date): CandlestickData[] {
  const days = buildSequentialDays(ohlc.length, endDate);
  return ohlc.map(([open, high, low, close], idx) => ({
    time: days[idx],
    open,
    high,
    low,
    close
  }));
}
