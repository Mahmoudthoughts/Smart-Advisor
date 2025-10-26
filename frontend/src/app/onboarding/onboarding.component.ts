import { CommonModule } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule, NgForm } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';

import {
  PortfolioAccount,
  PortfolioAccountPayload,
  PortfolioDataService,
  SymbolSearchResult,
  WatchlistSymbol
} from '../portfolio-data.service';

@Component({
  selector: 'app-onboarding',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './onboarding.component.html',
  styleUrls: ['./onboarding.component.scss']
})
export class OnboardingComponent implements OnInit {
  private readonly dataService = inject(PortfolioDataService);
  private readonly router = inject(Router);

  readonly watchlist = signal<WatchlistSymbol[]>([]);
  readonly accounts = signal<PortfolioAccount[]>([]);
  readonly searchResults = signal<SymbolSearchResult[]>([]);
  readonly isSearching = signal<boolean>(false);
  readonly isAddingSymbol = signal<boolean>(false);
  readonly isSavingAccount = signal<boolean>(false);
  readonly searchError = signal<string | null>(null);
  readonly addSymbolStatus = signal<string | null>(null);
  readonly addSymbolError = signal<string | null>(null);
  readonly accountStatus = signal<string | null>(null);
  readonly accountError = signal<string | null>(null);

  searchTerm = '';
  manualSymbol = '';
  manualName = '';

  accountForm: PortfolioAccountPayload = {
    name: '',
    type: 'Brokerage',
    currency: 'USD',
    notes: '',
    is_default: true
  };

  readonly onboardingComplete = computed(
    () => this.watchlist().length > 0 && this.accounts().length > 0
  );

  ngOnInit(): void {
    this.loadWatchlist();
    this.loadAccounts();
  }

  loadWatchlist(): void {
    this.dataService.getWatchlist().subscribe({
      next: (items) => this.watchlist.set(items),
      error: () => this.watchlist.set([])
    });
  }

  loadAccounts(): void {
    this.dataService.getAccounts().subscribe({
      next: (items) => this.accounts.set(items),
      error: () => this.accounts.set([])
    });
  }

  searchSymbols(): void {
    const query = this.searchTerm.trim();
    if (!query) {
      this.searchResults.set([]);
      this.searchError.set('Enter a ticker or company name to search.');
      return;
    }
    this.searchError.set(null);
    this.isSearching.set(true);
    this.dataService.searchSymbols(query).subscribe({
      next: (results) => {
        this.searchResults.set(results);
        this.isSearching.set(false);
        if (!results.length) {
          this.searchError.set('No matches found. Refine your search keywords.');
        }
      },
      error: () => {
        this.searchResults.set([]);
        this.isSearching.set(false);
        this.searchError.set('Unable to search symbols right now. Try again later.');
      }
    });
  }

  addSymbol(result: SymbolSearchResult): void {
    this.handleSymbolAdd(result);
  }

  addSymbolFromInput(form: NgForm): void {
    const normalized = this.manualSymbol.trim().toUpperCase();
    if (!normalized) {
      this.addSymbolError.set('Enter a symbol ticker (e.g., AAPL) to add it.');
      return;
    }
    const name = this.manualName.trim() || undefined;
    this.handleSymbolAdd(
      {
        symbol: normalized,
        name: name ?? normalized,
        region: undefined,
        currency: undefined,
        match_score: null
      },
      () => {
        form.resetForm({ symbol: '', name: '' });
        this.manualSymbol = '';
        this.manualName = '';
      }
    );
  }

  private handleSymbolAdd(result: SymbolSearchResult, onSuccess?: () => void): void {
    if (!result?.symbol) {
      return;
    }
    const normalized = result.symbol.toUpperCase();
    this.isAddingSymbol.set(true);
    this.addSymbolError.set(null);
    this.dataService.addWatchlistSymbol(normalized, result.name).subscribe({
      next: (symbol) => {
        this.watchlist.update((current) => {
          const exists = current.some((item) => item.symbol === symbol.symbol);
          const enriched = {
            ...symbol,
            name: result.name ?? symbol.name ?? symbol.symbol
          } as WatchlistSymbol;
          return exists
            ? current.map((item) =>
                item.symbol === enriched.symbol ? enriched : item
              )
            : [...current, enriched];
        });
        this.addSymbolStatus.set(`${normalized} added to your workspace.`);
        this.isAddingSymbol.set(false);
        onSuccess?.();
      },
      error: (err) => {
        const message = err?.error?.detail ?? 'Unable to add the selected symbol.';
        this.addSymbolError.set(message);
        this.isAddingSymbol.set(false);
      }
    });
  }

  saveAccount(form: NgForm): void {
    const payload: PortfolioAccountPayload = {
      name: this.accountForm.name?.trim() ?? '',
      type: this.accountForm.type?.trim() || undefined,
      currency: (this.accountForm.currency || 'USD').trim().toUpperCase(),
      notes: this.accountForm.notes?.trim() || undefined,
      is_default: Boolean(this.accountForm.is_default)
    };
    if (!payload.name) {
      this.accountError.set('Provide an account name (e.g., Interactive Brokers).');
      return;
    }
    this.accountError.set(null);
    this.accountStatus.set(null);
    this.isSavingAccount.set(true);
    this.dataService.createAccount(payload).subscribe({
      next: (account) => {
        this.accounts.update((current) => {
          const updated = payload.is_default
            ? current.map((item) => ({ ...item, is_default: false }))
            : current;
          return [...updated.filter((item) => item.id !== account.id), account].sort((a, b) =>
            a.name.localeCompare(b.name)
          );
        });
        this.accountStatus.set(`${account.name} is ready for trade tracking.`);
        this.isSavingAccount.set(false);
        form.resetForm({
          name: '',
          type: payload.type ?? 'Brokerage',
          currency: payload.currency ?? 'USD',
          notes: '',
          is_default: false
        });
        this.accountForm = {
          name: '',
          type: payload.type ?? 'Brokerage',
          currency: payload.currency ?? 'USD',
          notes: '',
          is_default: false
        };
      },
      error: (err) => {
        const message = err?.error?.detail ?? 'Unable to save the account. Please try again.';
        this.accountError.set(message);
        this.isSavingAccount.set(false);
      }
    });
  }

  goToStocks(): void {
    void this.router.navigate(['/app/stocks']);
  }
}
