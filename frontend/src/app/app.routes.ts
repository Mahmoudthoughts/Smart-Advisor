import { Routes } from '@angular/router';
import { authGuard } from './auth.guard';
import { AdvisorDashboardComponent } from './advisor-dashboard/advisor-dashboard.component';
import { AlertsComponent } from './alerts/alerts.component';
import { ForecastComponent } from './forecast/forecast.component';
import { LoginComponent } from './login/login.component';
import { MacroComponent } from './macro/macro.component';
import { MyStocksComponent } from './my-stocks/my-stocks.component';
import { OnboardingComponent } from './onboarding/onboarding.component';
import { OpportunitiesComponent } from './opportunities/opportunities.component';
import { RegisterComponent } from './register/register.component';
import { SentimentComponent } from './sentiment/sentiment.component';
import { SignalsComponent } from './signals/signals.component';
import { SymbolDetailComponent } from './symbol-detail/symbol-detail.component';
import { SimulatorComponent } from './simulator/simulator.component';
import { TimelineComponent } from './timeline/timeline.component';
import { TransactionsComponent } from './transactions/transactions.component';

export const APP_ROUTES: Routes = [
  {
    path: 'login',
    component: LoginComponent
  },
  {
    path: 'register',
    component: RegisterComponent
  },
  {
    path: 'app/onboarding',
    component: OnboardingComponent,
    canActivate: [authGuard]
  },
  {
    path: 'app/overview',
    component: AdvisorDashboardComponent,
    canActivate: [authGuard]
  },
  {
    path: 'app/stocks',
    component: MyStocksComponent,
    canActivate: [authGuard]
  },
  {
    path: 'app/transactions',
    component: TransactionsComponent,
    canActivate: [authGuard]
  },
  {
    path: 'app/symbols/:symbol',
    component: SymbolDetailComponent,
    canActivate: [authGuard]
  },
  {
    path: 'app/timeline',
    component: TimelineComponent,
    canActivate: [authGuard]
  },
  {
    path: 'app/opportunities',
    component: OpportunitiesComponent,
    canActivate: [authGuard]
  },
  {
    path: 'app/signals',
    component: SignalsComponent,
    canActivate: [authGuard]
  },
  {
    path: 'app/sentiment',
    component: SentimentComponent,
    canActivate: [authGuard]
  },
  {
    path: 'app/forecast',
    component: ForecastComponent,
    canActivate: [authGuard]
  },
  {
    path: 'app/simulator',
    component: SimulatorComponent,
    canActivate: [authGuard]
  },
  {
    path: 'app/macro',
    component: MacroComponent,
    canActivate: [authGuard]
  },
  {
    path: 'app/alerts',
    component: AlertsComponent,
    canActivate: [authGuard]
  },
  {
    path: 'app/portfolio',
    pathMatch: 'full',
    redirectTo: 'app/stocks'
  },
  {
    path: 'app',
    pathMatch: 'full',
    redirectTo: 'app/overview'
  },
  {
    path: '',
    pathMatch: 'full',
    redirectTo: 'login'
  },
  {
    path: '**',
    redirectTo: 'login'
  }
];
