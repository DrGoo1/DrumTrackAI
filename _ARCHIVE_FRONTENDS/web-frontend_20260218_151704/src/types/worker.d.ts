// Web Worker TypeScript declarations for React Scripts compatibility

declare global {
  interface DedicatedWorkerGlobalScope extends WorkerGlobalScope {
    onmessage: ((this: DedicatedWorkerGlobalScope, ev: MessageEvent) => any) | null;
    postMessage(message: any, transfer?: Transferable[]): void;
  }

  interface Window {
    webkitAudioContext?: typeof AudioContext;
  }
}

// Worker constructor types
declare module "*.worker.ts" {
  class WebpackWorker extends Worker {
    constructor();
  }
  export default WebpackWorker;
}

declare module "*.worker?worker" {
  class WebpackWorker extends Worker {
    constructor();
  }
  export default WebpackWorker;
}

export {};
