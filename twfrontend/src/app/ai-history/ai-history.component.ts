import { CommonModule } from '@angular/common';
import { Component, OnDestroy, OnInit, computed, inject, signal } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { Subscription } from 'rxjs';

import { PortfolioDataService, WatchlistSymbol } from '../portfolio-data.service';
import { AiTimingHistoryEntry, AiTimingResponse, AiTimingService } from '../services/ai-timing.service';

type HistorySelection = {
  readonly entry: AiTimingHistoryEntry;
  readonly response: AiTimingResponse | null;
};

@Component({
  selector: 'app-ai-history',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './ai-history.component.html',
  styleUrls: ['./ai-history.component.scss']
})
export class AiHistoryComponent implements OnInit, OnDestroy {
  private readonly dataService = inject(PortfolioDataService);
  private readonly aiTiming = inject(AiTimingService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private querySub: Subscription | null = null;

  readonly watchlist = signal<WatchlistSymbol[]>([]);
  readonly selectedSymbol = signal<string>('');
  readonly startDate = signal<string>('');
  readonly endDate = signal<string>('');
  readonly isLoading = signal<boolean>(false);
  readonly loadError = signal<string | null>(null);
  readonly historyEntries = signal<AiTimingHistoryEntry[]>([]);
  readonly selectedIndex = signal<number>(0);

  readonly selectedSymbolName = computed(() => {
    const symbol = this.selectedSymbol();
    const entry = this.watchlist().find((row) => row.symbol === symbol);
    return entry?.name ?? null;
  });

  readonly selectedEntry = computed<HistorySelection | null>(() => {
    const entries = this.historyEntries();
    if (!entries.length) {
      return null;
    }
    const index = Math.min(this.selectedIndex(), entries.length - 1);
    const entry = entries[index] ?? entries[0];
    const response = entry ? (entry.response_payload as AiTimingResponse) : null;
    return entry ? { entry, response } : null;
  });

  ngOnInit(): void {
    this.loadWatchlist();
    this.querySub = this.route.queryParamMap.subscribe((params) => {
      const symbol = (params.get('symbol') ?? '').toUpperCase();
      if (symbol && symbol !== this.selectedSymbol()) {
        this.selectedSymbol.set(symbol);
        this.loadHistory();
      }
    });
  }

  ngOnDestroy(): void {
    this.querySub?.unsubscribe();
  }

  loadWatchlist(): void {
    this.dataService.getWatchlist().subscribe({
      next: (items) => {
        this.watchlist.set(items);
        if (!this.selectedSymbol() && items.length) {
          const first = items[0].symbol;
          this.selectedSymbol.set(first);
          void this.router.navigate(['/app/ai-history'], { queryParams: { symbol: first } });
          this.loadHistory();
        }
      },
      error: () => this.watchlist.set([])
    });
  }

  onSymbolChange(symbol: string): void {
    if (!symbol || symbol === this.selectedSymbol()) {
      return;
    }
    this.selectedSymbol.set(symbol);
    void this.router.navigate(['/app/ai-history'], { queryParams: { symbol } });
    this.loadHistory();
  }

  applyFilters(): void {
    this.loadHistory();
  }

  loadHistory(): void {
    const symbol = this.selectedSymbol();
    if (!symbol) {
      this.historyEntries.set([]);
      return;
    }
    this.isLoading.set(true);
    this.loadError.set(null);
    this.aiTiming
      .getTimingHistory({
        symbol,
        startDate: this.startDate() || undefined,
        endDate: this.endDate() || undefined
      })
      .subscribe({
        next: (entries) => {
          this.historyEntries.set(entries);
          this.selectedIndex.set(0);
          this.isLoading.set(false);
        },
        error: () => {
          this.isLoading.set(false);
          this.loadError.set('Unable to load AI timing history right now.');
        }
      });
  }

  selectEntry(index: number): void {
    this.selectedIndex.set(index);
  }

  regenerate(): void {
    const entries = this.historyEntries();
    if (entries.length < 2) {
      return;
    }
    const nextIndex = (this.selectedIndex() + 1) % entries.length;
    this.selectedIndex.set(nextIndex);
  }

  formatTimestamp(value: string): string {
    const dt = new Date(value);
    if (Number.isNaN(dt.getTime())) {
      return value;
    }
    return dt.toLocaleString();
  }
}
