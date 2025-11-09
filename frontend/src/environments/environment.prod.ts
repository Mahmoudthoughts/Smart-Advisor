export const environment = {
  production: true,
  apiBaseUrl: 'http://localhost:8000',
  telemetry: {
    enabled: true,
    serviceName: 'smart-advisor-frontend',
    exporterUrl: 'http://otel-collector:4318/v1/traces',
    resourceAttributes: {
      'deployment.environment': 'prod',
      'service.version': '1.0.0'
    },
    propagateTraceHeaderCorsUrls: ['http://backend:8000']
  }
};
