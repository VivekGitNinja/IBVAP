import test from 'node:test';
import assert from 'node:assert/strict';

test('Distributed tracing X-Trace-ID generation format', () => {
  function generateTraceId() {
    const rand = Math.random().toString(16).substring(2, 10);
    const ts = Date.now().toString(16).substring(4);
    return `trace-fe-${rand}-${ts}`;
  }

  const tid1 = generateTraceId();
  const tid2 = generateTraceId();

  assert.match(tid1, /^trace-fe-[a-f0-9]+-[a-f0-9]+$/);
  assert.notEqual(tid1, tid2);
});

test('HTTP request telemetry header decoration', () => {
  function decorateHeaders(customHeaders, token, traceId) {
    const headers = { ...customHeaders };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    headers['X-Trace-ID'] = traceId;
    return headers;
  }

  const decorated = decorateHeaders(
    { 'Content-Type': 'application/json' },
    'mock-token-xyz',
    'trace-fe-1234abcd-5678ef'
  );

  assert.equal(decorated['Content-Type'], 'application/json');
  assert.equal(decorated['Authorization'], 'Bearer mock-token-xyz');
  assert.equal(decorated['X-Trace-ID'], 'trace-fe-1234abcd-5678ef');
});

test('Telemetry ring buffer bounded capacity and FIFO eviction', () => {
  class BoundedBuffer {
    constructor(maxSize = 5) {
      this.maxSize = maxSize;
      this.buffer = [];
    }
    push(item) {
      if (this.buffer.length >= this.maxSize) {
        this.buffer.shift();
      }
      this.buffer.push(item);
    }
    getAll() {
      return [...this.buffer];
    }
  }

  const buf = new BoundedBuffer(3);
  buf.push('event-1');
  buf.push('event-2');
  buf.push('event-3');
  assert.deepEqual(buf.getAll(), ['event-1', 'event-2', 'event-3']);

  buf.push('event-4');
  assert.deepEqual(buf.getAll(), ['event-2', 'event-3', 'event-4']);
  assert.equal(buf.getAll().length, 3);
});

test('Core Web Vitals health thresholds classification', () => {
  function classifyLCP(lcpMs) {
    if (lcpMs <= 2500) return 'GOOD';
    if (lcpMs <= 4000) return 'NEEDS_IMPROVEMENT';
    return 'POOR';
  }

  function classifyCLS(clsScore) {
    if (clsScore <= 0.1) return 'GOOD';
    if (clsScore <= 0.25) return 'NEEDS_IMPROVEMENT';
    return 'POOR';
  }

  assert.equal(classifyLCP(1200), 'GOOD');
  assert.equal(classifyLCP(2800), 'NEEDS_IMPROVEMENT');
  assert.equal(classifyLCP(5200), 'POOR');

  assert.equal(classifyCLS(0.04), 'GOOD');
  assert.equal(classifyCLS(0.18), 'NEEDS_IMPROVEMENT');
  assert.equal(classifyCLS(0.42), 'POOR');
});
