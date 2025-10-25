import { Routes } from '@angular/router';
import { authGuard } from './auth.guard';
import { AdvisorDashboardComponent } from './advisor-dashboard/advisor-dashboard.component';
import { AlertsComponent } from './alerts/alerts.component';
import { ForecastComponent } from './forecast/forecast.component';
import { LoginComponent } from './login/login.component';
import { MacroComponent } from './macro/macro.component';
import { OpportunitiesComponent } from './opportunities/opportunities.component';
import { RegisterComponent } from './register/register.component';
import { SentimentComponent } from './sentiment/sentiment.component';
import { SignalsComponent } from './signals/signals.component';
import { SimulatorComponent } from './simulator/simulator.component';
import { TimelineComponent } from './timeline/timeline.component';
import { PortfolioComponent } from './portfolio/portfolio.component';

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
    path: 'app/overview',
    component: AdvisorDashboardComponent,
    canActivate: [authGuard]
  },
  {
    path: 'app/timeline',
    component: TimelineComponent,
    canActivate: [authGuard]
  },
  {
    path: 'app/portfolio',
    component: PortfolioComponent,
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
