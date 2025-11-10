export const environment = {
  production: true,
  // In production, prefer same-origin NGINX proxy to the backend
  apiBaseUrl: '/api',
  telemetry: {
    enabled: true,
    serviceName: 'smart-advisor-frontend',
    exporterUrl: 'http://otel-collector:4318/v1/traces',
    resourceAttributes: {
      'deployment.environment': 'prod',
      'service.version': '1.0.0'
    },
    // Propagate trace headers for cross-origin calls if used; same-origin '/api' needs no CORS allowlist
    propagateTraceHeaderCorsUrls: ['http://localhost:8000']
  }
};
