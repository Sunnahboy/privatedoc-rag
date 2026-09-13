declare module "event-source-polyfill" {
  export interface EventSourcePolyfillOptions {
    headers?: Record<string, string>;
    withCredentials?: boolean;
  }

  export class EventSourcePolyfill {
    constructor(url: string, options?: EventSourcePolyfillOptions);
    onopen: ((event: Event) => void) | null;
    onmessage: ((event: MessageEvent<string>) => void) | null;
    onerror: ((event: Event) => void) | null;
    close(): void;
  }
}
