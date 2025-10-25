import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule, NgForm } from '@angular/forms';

import {
  PortfolioDataService,
  PortfolioTransaction,
  TransactionPayload,
  WatchlistSymbol,
} from '../portfolio-data.service';

interface TransactionFormModel {
  symbol: string;
  type: string;
  quantity: number;
  price: number;
  tradeDateTime: string;
  fee: number;
  tax: number;
  currency: string;
  account: string;
  notes: string;
}

@Component({
  selector: 'app-portfolio-workspace',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './portfolio.component.html',
  styleUrls: ['./portfolio.component.scss']
})
export class PortfolioComponent implements OnInit {
  private readonly dataService = inject(PortfolioDataService);

  readonly watchlist = signal<WatchlistSymbol[]>([]);
  readonly transactions = signal<PortfolioTransaction[]>([]);
  readonly symbolError = signal<string | null>(null);
  readonly transactionError = signal<string | null>(null);
  readonly transactionSuccess = signal<string | null>(null);
  readonly isSubmittingSymbol = signal<boolean>(false);
  readonly isSubmittingTransaction = signal<boolean>(false);

  newSymbolValue = '';
  transactionModel: TransactionFormModel = {
    symbol: '',
    type: 'BUY',
    quantity: 0,
    price: 0,
    tradeDateTime: '',
    fee: 0,
    tax: 0,
    currency: 'USD',
    account: '',
    notes: ''
  };

  ngOnInit(): void {
    this.loadWatchlist();
    this.loadTransactions();
  }

  loadWatchlist(): void {
    this.dataService.getWatchlist().subscribe({
      next: (items) => {
        this.watchlist.set(items);
        if (!this.transactionModel.symbol && items.length > 0) {
          this.transactionModel.symbol = items[0].symbol;
        }
      },
      error: () => {
        this.symbolError.set('Unable to load watchlist symbols.');
      }
    });
  }

  loadTransactions(): void {
    this.dataService.getTransactions().subscribe({
      next: (items) => {
        this.transactions.set(items);
      },
      error: () => {
        this.transactionError.set('Unable to load transactions.');
      }
    });
  }

  addSymbol(form: NgForm): void {
    const value = this.newSymbolValue.trim().toUpperCase();
    if (!value) {
      this.symbolError.set('Enter a symbol to track.');
      return;
    }
    this.symbolError.set(null);
    this.isSubmittingSymbol.set(true);
    this.dataService.addWatchlistSymbol(value).subscribe({
      next: (symbol) => {
        this.watchlist.update((current) => {
          const exists = current.some((item) => item.symbol === symbol.symbol);
          return exists ? current : [...current, symbol].sort((a, b) => a.symbol.localeCompare(b.symbol));
        });
        this.newSymbolValue = '';
        form.resetForm();
        this.isSubmittingSymbol.set(false);
        if (!this.transactionModel.symbol) {
          this.transactionModel.symbol = symbol.symbol;
        }
      },
      error: (err) => {
        const message = err?.error?.detail ?? 'Failed to add symbol. Please verify the ticker.';
        this.symbolError.set(message);
        this.isSubmittingSymbol.set(false);
      }
    });
  }

  submitTransaction(form: NgForm): void {
    const model = this.transactionModel;
    if (!model.symbol) {
      this.transactionError.set('Choose a symbol before recording a trade.');
      return;
    }
    if (!model.tradeDateTime) {
      this.transactionError.set('Provide the trade date and time.');
      return;
    }
    this.transactionError.set(null);
    this.transactionSuccess.set(null);
    this.isSubmittingTransaction.set(true);
    const payload: TransactionPayload = {
      symbol: model.symbol.trim().toUpperCase(),
      type: model.type,
      quantity: Number(model.quantity),
      price: Number(model.price),
      trade_datetime: model.tradeDateTime,
      fee: Number(model.fee || 0),
      tax: Number(model.tax || 0),
      currency: model.currency.trim().toUpperCase() || 'USD',
      account: model.account ? model.account.trim() : null,
      notes: model.notes?.trim() || null
    };
    this.dataService.createTransaction(payload).subscribe({
      next: (tx) => {
        this.transactions.update((current) => [tx, ...current]);
        this.transactionSuccess.set('Transaction saved and analytics recomputed.');
        this.isSubmittingTransaction.set(false);
        form.resetForm({
          symbol: model.symbol,
          type: model.type,
          quantity: 0,
          price: 0,
          tradeDateTime: '',
          fee: 0,
          tax: 0,
          currency: model.currency,
          account: '',
          notes: ''
        });
        this.transactionModel = {
          symbol: model.symbol,
          type: model.type,
          quantity: 0,
          price: 0,
          tradeDateTime: '',
          fee: 0,
          tax: 0,
          currency: model.currency,
          account: '',
          notes: ''
        };
        this.loadWatchlist();
        this.loadTransactions();
      },
      error: (err) => {
        const message = err?.error?.detail ?? 'Failed to save the transaction.';
        this.transactionError.set(message);
        this.isSubmittingTransaction.set(false);
      }
    });
  }
}
