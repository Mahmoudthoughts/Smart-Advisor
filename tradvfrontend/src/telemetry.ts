import { environment } from './environments/environment';

import { diag, DiagConsoleLogger, DiagLogLevel } from '@opentelemetry/api';
import { registerInstrumentations } from '@opentelemetry/instrumentation';
import { DocumentLoadInstrumentation } from '@opentelemetry/instrumentation-document-load';
import { FetchInstrumentation } from '@opentelemetry/instrumentation-fetch';
import { XMLHttpRequestInstrumentation } from '@opentelemetry/instrumentation-xml-http-request';
import { ZoneContextManager } from '@opentelemetry/context-zone-peer-dep';
import { Resource } from '@opentelemetry/resources';
import { SemanticResourceAttributes } from '@opentelemetry/semantic-conventions';
import { WebTracerProvider } from '@opentelemetry/sdk-trace-web';
import { BatchSpanProcessor } from '@opentelemetry/sdk-trace-base';
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-http';

type TelemetryConfig = {
  enabled: boolean;
  serviceName: string;
  exporterUrl: string;
  resourceAttributes?: Record<string, string>;
  propagateTraceHeaderCorsUrls?: string[];
};

const telemetryConfig: TelemetryConfig | undefined = environment.telemetry;

function configureTelemetry(config: TelemetryConfig): void {
  try {
    diag.setLogger(new DiagConsoleLogger(), environment.production ? DiagLogLevel.ERROR : DiagLogLevel.INFO);

    const resource = Resource.default().merge(
      new Resource({
        [SemanticResourceAttributes.SERVICE_NAME]: config.serviceName,
        ...(config.resourceAttributes ?? {})
      })
    );

    const provider = new WebTracerProvider({ resource });
    const exporter = new OTLPTraceExporter({ url: config.exporterUrl });
    provider.addSpanProcessor(new BatchSpanProcessor(exporter));

    provider.register({ contextManager: new ZoneContextManager() });

    const corsUrls = config.propagateTraceHeaderCorsUrls ?? [environment.apiBaseUrl];

    registerInstrumentations({
      instrumentations: [
        new DocumentLoadInstrumentation(),
        new FetchInstrumentation({ propagateTraceHeaderCorsUrls: corsUrls }),
        new XMLHttpRequestInstrumentation({ propagateTraceHeaderCorsUrls: corsUrls })
      ]
    });
  } catch (error) {
    diag.error('Failed to initialise OpenTelemetry', error as Error);
  }
}

if (telemetryConfig?.enabled) {
  configureTelemetry(telemetryConfig);
}
