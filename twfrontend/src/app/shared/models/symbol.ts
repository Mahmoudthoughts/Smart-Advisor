export interface SymbolSearchResult {
  symbol: string;
  name: string;
  region?: string;
  currency?: string;
  match_score?: number;
}
