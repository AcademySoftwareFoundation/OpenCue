// lib/metricsService.ts
import { Counter, Registry } from 'prom-client';

class MetricsService {
  private static instance: MetricsService;
  private registry: Registry;
  private counters: Map<string, Counter>;

  private constructor() {
    this.registry = new Registry();
    this.counters = new Map();

    // Initialize default metrics (optional)
    // collectDefaultMetrics({ register: this.registry });
  }

  public static getInstance(): MetricsService {
    if (!MetricsService.instance) {
      MetricsService.instance = new MetricsService();
    }
    return MetricsService.instance;
  }

  public registerCounter(name: string, help: string): Counter | undefined {
    if (!this.counters.has(name)) {
      const counter = new Counter({
        name,
        help,
        registers: [this.registry],
        labelNames: ['user']
      });
      this.counters.set(name, counter);
    }
    return this.counters.get(name);
  }

  public incrementCounter(name: string, username: string): void {
    const counter = this.counters.get(name);
    if (counter) {
      // Increment the specified counter for the given username.
      counter.inc({user: username});
    } else {
      // Log a warning if the counter specified by name does not exist in the registry.
      console.warn(`Counter ${name} not found`);
    }
  }

  public async getMetrics(): Promise<string> {
    return this.registry.metrics();
  }
}
export default MetricsService;