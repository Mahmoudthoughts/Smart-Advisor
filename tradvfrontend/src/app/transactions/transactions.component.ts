import { CommonModule, CurrencyPipe, DatePipe, DecimalPipe } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule, NgForm } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { firstValueFrom } from 'rxjs';

import {
  PortfolioAccount,
  PortfolioDataService,
  PortfolioTransaction,
  TransactionPayload,
  WatchlistSymbol
} from '../portfolio-data.service';

interface TransactionFilters {
  symbol: string;
  type: string;
  account: string;
  from?: string;
  to?: string;
}

@Component({
  selector: 'app-transactions',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, CurrencyPipe, DatePipe, DecimalPipe],
  templateUrl: './transactions.component.html',
  styleUrls: ['./transactions.component.scss']
})
export class TransactionsComponent implements OnInit {
  private readonly dataService = inject(PortfolioDataService);
  private readonly route = inject(ActivatedRoute);

  readonly transactions = signal<PortfolioTransaction[]>([]);
  readonly watchlist = signal<WatchlistSymbol[]>([]);
  readonly accounts = signal<PortfolioAccount[]>([]);
  readonly loadError = signal<string | null>(null);
  readonly importStatus = signal<string | null>(null);
  readonly importError = signal<string | null>(null);
  readonly exportStatus = signal<string | null>(null);
  readonly isLoading = signal<boolean>(true);
  readonly isImporting = signal<boolean>(false);

  readonly filters = signal<TransactionFilters>({ symbol: '', type: '', account: '' });
  readonly editingId = signal<number | null>(null);
  readonly editModel = signal<TransactionPayload | null>(null);
  readonly saveError = signal<string | null>(null);
  readonly saveStatus = signal<string | null>(null);
  readonly newTransaction = signal<TransactionPayload>({
    symbol: '',
    type: 'BUY',
    quantity: 0,
    price: 0,
    trade_datetime: '',
    fee: 0,
    tax: 0,
    currency: 'USD',
    account: '',
    notes: ''
  });
  readonly createError = signal<string | null>(null);
  readonly createStatus = signal<string | null>(null);
  readonly isSaving = signal<boolean>(false);
  readonly deletingId = signal<number | null>(null);
  readonly deleteError = signal<string | null>(null);
  readonly deleteStatus = signal<string | null>(null);

  readonly filteredTransactions = computed(() => {
    const { symbol, type, account, from, to } = this.filters();
    return this.transactions().filter((tx) => {
      const matchesSymbol = !symbol || tx.symbol === symbol;
      const matchesType = !type || tx.type === type;
      const matchesAccount = !account || tx.account === account;
      const txDate = new Date(tx.trade_datetime);
      const matchesFrom = !from || txDate >= new Date(from);
      const matchesTo = !to || txDate <= new Date(to);
      return matchesSymbol && matchesType && matchesAccount && matchesFrom && matchesTo;
    });
  });

  readonly totalNotional = computed(() =>
    this.filteredTransactions().reduce((acc, tx) => acc + tx.notional_value, 0)
  );

  readonly totalFees = computed(() =>
    this.filteredTransactions().reduce((acc, tx) => acc + tx.fee, 0)
  );

  readonly totalTaxes = computed(() =>
    this.filteredTransactions().reduce((acc, tx) => acc + tx.tax, 0)
  );

  ngOnInit(): void {
    this.route.queryParamMap.subscribe((params) => {
      const symbol = params.get('symbol');
      if (symbol) {
        this.filters.update((current) => ({ ...current, symbol }));
      }
    });
    this.loadDependencies();
  }

  loadDependencies(): void {
    this.isLoading.set(true);
    this.loadError.set(null);
    this.dataService.getWatchlist().subscribe({
      next: (items) => this.watchlist.set(items),
      error: () => this.watchlist.set([])
    });
    this.dataService.getAccounts().subscribe({
      next: (items) => this.accounts.set(items),
      error: () => this.accounts.set([])
    });
    this.dataService.getTransactions().subscribe({
      next: (items) => {
        this.transactions.set(items);
        this.isLoading.set(false);
      },
      error: () => {
        this.transactions.set([]);
        this.isLoading.set(false);
        this.loadError.set('Unable to load transactions. Try refreshing.');
      }
    });
  }

  resetFilters(): void {
    this.filters.set({ symbol: '', type: '', account: '' });
  }

  updateFilters(patch: Partial<TransactionFilters>): void {
    this.filters.update((current) => ({ ...current, ...patch }));
  }

  toNumber(value: unknown): number {
    const numeric = typeof value === 'number' ? value : Number(value ?? 0);
    return Number.isNaN(numeric) ? 0 : numeric;
  }

  private normalizeNumber(value: unknown): string {
    const numeric = this.toNumber(value);
    return numeric.toFixed(10);
  }

  private buildTransactionKey(value: {
    symbol?: string;
    type?: string;
    quantity?: number;
    price?: number;
    trade_datetime?: string;
    fee?: number;
    tax?: number;
    currency?: string;
    account?: string | null;
    notes?: string | null;
  }): string {
    const tradeDate = value.trade_datetime ? new Date(value.trade_datetime).toISOString() : '';
    return [
      value.symbol?.trim().toUpperCase() ?? '',
      value.type?.trim().toUpperCase() ?? '',
      this.normalizeNumber(value.quantity ?? 0),
      this.normalizeNumber(value.price ?? 0),
      tradeDate,
      this.normalizeNumber(value.fee ?? 0),
      this.normalizeNumber(value.tax ?? 0),
      value.currency?.trim().toUpperCase() ?? 'USD',
      value.account?.trim() ?? '',
      value.notes?.trim() ?? ''
    ].join('|');
  }

  updateNewTransaction(patch: Partial<TransactionPayload>): void {
    this.newTransaction.update((current) => ({ ...current, ...patch }));
  }

  beginEdit(transaction: PortfolioTransaction): void {
    this.editingId.set(transaction.id);
    this.saveError.set(null);
    this.saveStatus.set(null);
    this.editModel.set({
      symbol: transaction.symbol,
      type: transaction.type,
      quantity: transaction.quantity,
      price: transaction.price,
      trade_datetime: transaction.trade_datetime.slice(0, 16),
      fee: transaction.fee,
      tax: transaction.tax,
      currency: transaction.currency,
      account: transaction.account ?? undefined,
      account_id: transaction.account_id ?? undefined,
      notes: transaction.notes ?? undefined
    });
  }

  cancelEdit(): void {
    this.editingId.set(null);
    this.editModel.set(null);
  }

  async submitTransaction(form: NgForm): Promise<void> {
    const model = this.newTransaction();
    if (!model.symbol.trim()) {
      this.createError.set('Choose a symbol to record a transaction.');
      return;
    }
    if (!model.trade_datetime) {
      this.createError.set('Provide the trade date and time.');
      return;
    }
    this.isSaving.set(true);
    this.createError.set(null);
    this.createStatus.set(null);
    try {
      const accountName = model.account ? model.account.trim() : undefined;
      const accountRecord = accountName
        ? this.accounts().find((acct) => acct.name === accountName)
        : undefined;
      const payload: TransactionPayload = {
        symbol: model.symbol.trim().toUpperCase(),
        type: model.type.toUpperCase(),
        quantity: Number(model.quantity),
        price: Number(model.price),
        trade_datetime: new Date(model.trade_datetime).toISOString(),
        fee: Number(model.fee || 0),
        tax: Number(model.tax || 0),
        currency: model.currency?.trim().toUpperCase() || 'USD',
        account: accountName,
        account_id: accountRecord?.id,
        notes: model.notes?.trim() || undefined
      };
      const response = await firstValueFrom(this.dataService.createTransaction(payload));
      this.transactions.update((current) => [response, ...current]);
      this.createStatus.set('Transaction saved. Analytics will refresh shortly.');
      this.newTransaction.set({
        symbol: payload.symbol,
        type: payload.type,
        quantity: 0,
        price: 0,
        trade_datetime: '',
        fee: 0,
        tax: 0,
        currency: payload.currency,
        account: accountName ?? '',
        notes: ''
      });
      form.resetForm({
        symbol: payload.symbol,
        type: payload.type,
        quantity: 0,
        price: 0,
        trade_datetime: '',
        fee: 0,
        tax: 0,
        currency: payload.currency,
        account: accountName ?? '',
        notes: ''
      });
    } catch (error: any) {
      const message = error?.error?.detail ?? 'Unable to record the transaction.';
      this.createError.set(message);
    } finally {
      this.isSaving.set(false);
    }
  }

  async saveEdit(form: NgForm, transaction: PortfolioTransaction): Promise<void> {
    const payload = this.editModel();
    if (!payload) {
      return;
    }
    if (!payload.symbol?.trim()) {
      this.saveError.set('Select a symbol for the transaction.');
      return;
    }
    if (!payload.trade_datetime) {
      this.saveError.set('Provide a trade date/time.');
      return;
    }
    this.saveError.set(null);
    this.saveStatus.set(null);
    try {
      const accountName = payload.account ? payload.account.trim() : undefined;
      const accountRecord = accountName
        ? this.accounts().find((acct) => acct.name === accountName)
        : undefined;
      const parsedDate = new Date(payload.trade_datetime);
      if (Number.isNaN(parsedDate.getTime())) {
        throw new Error('Invalid trade date provided.');
      }
      const isoDate = parsedDate.toISOString();
      const response = await firstValueFrom(
        this.dataService.updateTransaction(transaction.id, {
          symbol: payload.symbol.trim().toUpperCase(),
          type: payload.type.toUpperCase(),
          quantity: Number(payload.quantity),
          price: Number(payload.price),
          trade_datetime: isoDate,
          fee: Number(payload.fee || 0),
          tax: Number(payload.tax || 0),
          currency: payload.currency?.trim().toUpperCase() || 'USD',
          account_id: accountRecord?.id,
          account: accountName ?? accountRecord?.name,
          notes: payload.notes?.trim() || undefined
        })
      );
      this.transactions.update((current) =>
        current.map((item) => (item.id === transaction.id ? response : item))
      );
      this.saveStatus.set('Transaction updated. Snapshots recalculated.');
      this.editingId.set(null);
      this.editModel.set(null);
      form.resetForm();
    } catch (error: any) {
      const message = error?.error?.detail ?? 'Unable to save changes. Please retry.';
      this.saveError.set(message);
    }
  }

  async deleteTransaction(transaction: PortfolioTransaction): Promise<void> {
    const confirmed = window.confirm(
      `Delete the ${transaction.type} transaction for ${transaction.symbol} recorded on ${new Date(
        transaction.trade_datetime
      ).toLocaleString()}?`
    );
    if (!confirmed) {
      return;
    }
    this.deletingId.set(transaction.id);
    this.deleteError.set(null);
    this.deleteStatus.set(null);
    try {
      await firstValueFrom(this.dataService.deleteTransaction(transaction.id));
      this.transactions.update((current) => current.filter((item) => item.id !== transaction.id));
      if (this.editingId() === transaction.id) {
        this.editingId.set(null);
        this.editModel.set(null);
      }
      this.deleteStatus.set('Transaction removed. Portfolio metrics will refresh shortly.');
    } catch (error: any) {
      const message = error?.error?.detail ?? 'Unable to delete the transaction. Please retry.';
      this.deleteError.set(message);
    } finally {
      this.deletingId.set(null);
    }
  }

  async importCsv(event: Event): Promise<void> {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) {
      return;
    }
    this.isImporting.set(true);
    this.importStatus.set(null);
    this.importError.set(null);
    try {
      const text = await file.text();
      const rows = text
        .split(/\r?\n/)
        .map((line) => line.trim())
        .filter((line) => line.length);
      if (rows.length <= 1) {
        throw new Error('CSV must contain header and at least one row.');
      }
      const header = rows[0].split(',').map((cell) => cell.trim().toLowerCase());
      const dateIndex = header.indexOf('date');
      const typeIndex = header.indexOf('type');
      const symbolIndex = header.indexOf('symbol');
      const qtyIndex = header.indexOf('quantity');
      const priceIndex = header.indexOf('price');
      const feeIndex = header.indexOf('fee');
      const taxIndex = header.indexOf('tax');
      const currencyIndex = header.indexOf('currency');
      const accountIndex = header.indexOf('account') !== -1 ? header.indexOf('account') : header.indexOf('broker_id');
      const notesIndex = header.indexOf('notes');
      if (dateIndex === -1 || typeIndex === -1 || symbolIndex === -1 || qtyIndex === -1 || priceIndex === -1) {
        throw new Error('CSV header missing required columns (date, type, symbol, quantity, price).');
      }
      const existingKeys = new Set(
        this.transactions().map((tx) =>
          this.buildTransactionKey({
            symbol: tx.symbol,
            type: tx.type,
            quantity: tx.quantity,
            price: tx.price,
            trade_datetime: tx.trade_datetime,
            fee: tx.fee,
            tax: tx.tax,
            currency: tx.currency,
            account: tx.account ?? null,
            notes: tx.notes ?? null
          })
        )
      );
      let importedCount = 0;
      let skippedCount = 0;
      for (let i = 1; i < rows.length; i += 1) {
        const cells = rows[i].split(',').map((cell) => cell.trim());
        const payload: TransactionPayload = {
          symbol: cells[symbolIndex]?.trim().toUpperCase() ?? '',
          type: cells[typeIndex]?.trim().toUpperCase() ?? '',
          quantity: Number(cells[qtyIndex]),
          price: Number(cells[priceIndex]),
          trade_datetime: new Date(cells[dateIndex]).toISOString(),
          fee: feeIndex !== -1 ? Number(cells[feeIndex]) : 0,
          tax: taxIndex !== -1 ? Number(cells[taxIndex]) : 0,
          currency: currencyIndex !== -1 && cells[currencyIndex] ? cells[currencyIndex].toUpperCase() : 'USD',
          account: accountIndex !== -1 ? cells[accountIndex] || undefined : undefined,
          notes: notesIndex !== -1 ? cells[notesIndex] || undefined : undefined
        };
        const payloadKey = this.buildTransactionKey(payload);
        if (existingKeys.has(payloadKey)) {
          skippedCount += 1;
          continue;
        }
        existingKeys.add(payloadKey);
        // eslint-disable-next-line no-await-in-loop
        const created = await firstValueFrom(this.dataService.createTransaction(payload));
        this.transactions.update((current) => [created, ...current]);
        importedCount += 1;
      }
      if (!importedCount && skippedCount) {
        this.importStatus.set(`${skippedCount} duplicate transactions skipped.`);
      } else if (skippedCount) {
        this.importStatus.set(`${importedCount} transactions imported. ${skippedCount} duplicates skipped.`);
      } else {
        this.importStatus.set(`${importedCount} transactions imported.`);
      }
    } catch (error: any) {
      this.importError.set(error?.message ?? 'Import failed. Ensure the CSV matches the template.');
    } finally {
      this.isImporting.set(false);
      input.value = '';
    }
  }

  exportCsv(): void {
    const rows = [
      'date,type,symbol,quantity,price,fee,tax,currency,account,notes',
      ...this.filteredTransactions().map((tx) =>
        [
          new Date(tx.trade_datetime).toISOString(),
          tx.type,
          tx.symbol,
          tx.quantity,
          tx.price,
          tx.fee,
          tx.tax,
          tx.currency,
          tx.account ?? '',
          (tx.notes ?? '').replace(/"/g, "''")
        ].join(',')
      )
    ];
    const blob = new Blob([rows.join('\n')], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = 'transactions-export.csv';
    anchor.click();
    URL.revokeObjectURL(url);
    this.exportStatus.set(`${this.filteredTransactions().length} transactions exported.`);
  }
}
