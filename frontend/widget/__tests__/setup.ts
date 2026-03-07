/**
 * Test Setup
 * Mocks DOM APIs not fully supported by jsdom
 */

// Mock scrollIntoView (not implemented in jsdom)
Element.prototype.scrollIntoView = vi.fn();

// Mock WebSocket connection delay for more predictable tests
const originalSetTimeout = global.setTimeout;
(global as any).setTimeout = (fn: Function, delay: number) => {
  if (delay === 10) {
    // Make WebSocket connection instant in tests
    return originalSetTimeout(fn, 0);
  }
  return originalSetTimeout(fn, delay);
};
