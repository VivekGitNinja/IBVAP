/**
 * IBVAP — Frontend Observability & Telemetry Subsystem
 * Captures Core Web Vitals (LCP, FID, CLS, FCP), distributes X-Trace-ID headers,
 * provides Sentry-compatible crash reporting, and maintains runtime telemetry buffers.
 */

export interface WebVitals {
  fcp?: number;
  lcp?: number;
  cls?: number;
  fid?: number;
  ttfb?: number;
}

export interface TelemetryEvent {
  timestamp: string;
  type: 'error' | 'performance' | 'navigation' | 'network';
  message: string;
  traceId?: string;
  durationMs?: number;
  metadata?: Record<string, any>;
}

class TelemetryManager {
  private static instance: TelemetryManager;
  private traceId: string = this.generateTraceId();
  private vitals: WebVitals = {};
  private eventBuffer: TelemetryEvent[] = [];
  private readonly maxBufferSize = 50;
  private initialized = false;

  private constructor() {}

  public static getInstance(): TelemetryManager {
    if (!TelemetryManager.instance) {
      TelemetryManager.instance = new TelemetryManager();
    }
    return TelemetryManager.instance;
  }

  public generateTraceId(): string {
    const rand = Math.random().toString(16).substring(2, 10);
    const ts = Date.now().toString(16).substring(4);
    this.traceId = `trace-fe-${rand}-${ts}`;
    return this.traceId;
  }

  public getTraceId(): string {
    return this.traceId;
  }

  public init(options?: { sentryDsn?: string }): void {
    if (this.initialized) return;
    this.initialized = true;

    // 1. Observe Web Vitals
    this.initPerformanceObservers();

    // 2. Capture Unhandled Global Errors
    window.addEventListener('error', (event) => {
      this.recordEvent({
        timestamp: new Date().toISOString(),
        type: 'error',
        message: event.message || 'Uncaught Error',
        traceId: this.traceId,
        metadata: {
          filename: event.filename,
          lineno: event.lineno,
          colno: event.colno,
          stack: event.error?.stack,
        },
      });
    });

    // 3. Capture Unhandled Promise Rejections
    window.addEventListener('unhandledrejection', (event) => {
      this.recordEvent({
        timestamp: new Date().toISOString(),
        type: 'error',
        message: event.reason?.message || String(event.reason) || 'Unhandled Promise Rejection',
        traceId: this.traceId,
        metadata: {
          stack: event.reason?.stack,
        },
      });
    });

    // 4. Sentry initialization hook if DSN or global SDK is present
    const dsn = options?.sentryDsn || (typeof import.meta !== 'undefined' && import.meta.env?.VITE_SENTRY_DSN);
    if (dsn && (window as any).Sentry) {
      try {
        (window as any).Sentry.init({
          dsn,
          tracesSampleRate: 1.0,
          environment: 'production',
        });
      } catch (err) {
        console.warn('Sentry initialization deferred:', err);
      }
    }
  }

  private initPerformanceObservers(): void {
    if (typeof window === 'undefined' || !('PerformanceObserver' in window)) return;

    try {
      // Paint Timing: FCP
      const paintObserver = new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          if (entry.name === 'first-contentful-paint') {
            this.vitals.fcp = Math.round(entry.startTime);
          }
        }
      });
      paintObserver.observe({ type: 'paint', buffered: true });

      // LCP Observer
      const lcpObserver = new PerformanceObserver((list) => {
        const entries = list.getEntries();
        if (entries.length > 0) {
          const lastEntry = entries[entries.length - 1];
          this.vitals.lcp = Math.round(lastEntry.startTime);
        }
      });
      lcpObserver.observe({ type: 'largest-contentful-paint', buffered: true });

      // CLS Observer
      let clsValue = 0;
      const clsObserver = new PerformanceObserver((list) => {
        for (const entry of list.getEntries() as any[]) {
          if (!entry.hadRecentInput) {
            clsValue += entry.value;
            this.vitals.cls = Math.round(clsValue * 1000) / 1000;
          }
        }
      });
      clsObserver.observe({ type: 'layout-shift', buffered: true });
    } catch {
      // Browsers lacking full observer support fallback gracefully
    }
  }

  public recordEvent(event: TelemetryEvent): void {
    if (this.eventBuffer.length >= this.maxBufferSize) {
      this.eventBuffer.shift();
    }
    this.eventBuffer.push(event);
  }

  public recordNetworkCall(url: string, durationMs: number, status: number, traceId?: string): void {
    this.recordEvent({
      timestamp: new Date().toISOString(),
      type: 'network',
      message: `${url} [${status}]`,
      traceId: traceId || this.traceId,
      durationMs,
      metadata: { url, status },
    });
  }

  public getVitals(): WebVitals {
    return { ...this.vitals };
  }

  public getRecentEvents(): TelemetryEvent[] {
    return [...this.eventBuffer];
  }
}

export const telemetry = TelemetryManager.getInstance();
