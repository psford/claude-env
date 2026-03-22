// StephenA Away - Content script for ESPN
// Removes Stephen A. Smith content from ESPN pages

(function() {
  'use strict';

  // Patterns to match Stephen A. Smith content
  const PATTERNS = [
    /stephen\s*a\.?\s*smith/i,
    /stephen\s*a\s*$/i,  // "Stephen A" at end of string
    /\bstephen\s*a\b/i,  // "Stephen A" as word
    /first\s*take/i,     // His show
    /smith['']?s\s*take/i
  ];

  // Track removed count for debugging
  let removedCount = 0;

  /**
   * Check if text contains Stephen A. Smith references
   */
  function containsStephenA(text) {
    if (!text) return false;
    return PATTERNS.some(pattern => pattern.test(text));
  }

  /**
   * Remove an element from the DOM
   */
  function removeElement(element, reason) {
    if (element && element.parentNode) {
      element.remove();
      removedCount++;
      console.log(`[StephenA Away] Removed: ${reason}`);
    }
  }

  /**
   * Scan and remove Stephen A content from the page
   */
  function scanAndRemove() {
    // Common ESPN content selectors
    const selectors = [
      'article',
      '.contentItem',
      '.content-item',
      '.Card',
      '.headlineStack__list li',
      '.carousel__item',
      '.video-item',
      '.media-pod',
      '.article-container',
      '[data-mptype="story"]',
      '[data-mptype="video"]',
      '.news-feed-item',
      '.feed-item',
      '.storyline'
    ];

    selectors.forEach(selector => {
      document.querySelectorAll(selector).forEach(element => {
        const text = element.textContent || '';
        const imgAlt = Array.from(element.querySelectorAll('img'))
          .map(img => img.alt || '')
          .join(' ');

        if (containsStephenA(text) || containsStephenA(imgAlt)) {
          removeElement(element, `Matched in ${selector}`);
        }
      });
    });

    // Also check headlines specifically
    document.querySelectorAll('h1, h2, h3, h4, a[href*="stephen"], a[href*="first-take"]').forEach(element => {
      if (containsStephenA(element.textContent) ||
          (element.href && containsStephenA(element.href))) {
        // Try to remove parent container for cleaner removal
        const container = element.closest('article, .contentItem, .Card, li, .feed-item') || element;
        removeElement(container, 'Headline match');
      }
    });

    // Check video embeds and iframes
    document.querySelectorAll('iframe, video, [data-video-id]').forEach(element => {
      const title = element.title || element.getAttribute('data-title') || '';
      if (containsStephenA(title)) {
        const container = element.closest('.video-item, .media-pod, article') || element;
        removeElement(container, 'Video match');
      }
    });
  }

  /**
   * Set up MutationObserver to catch dynamically loaded content
   */
  function observeChanges() {
    const observer = new MutationObserver((mutations) => {
      let shouldScan = false;

      mutations.forEach(mutation => {
        if (mutation.addedNodes.length > 0) {
          shouldScan = true;
        }
      });

      if (shouldScan) {
        // Debounce to avoid excessive scanning
        clearTimeout(observeChanges.timeout);
        observeChanges.timeout = setTimeout(scanAndRemove, 100);
      }
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true
    });
  }

  // Initial scan when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      scanAndRemove();
      observeChanges();
    });
  } else {
    scanAndRemove();
    observeChanges();
  }

  // Also scan after a short delay for lazy-loaded content
  setTimeout(scanAndRemove, 1000);
  setTimeout(scanAndRemove, 3000);

  console.log('[StephenA Away] Extension loaded on ESPN');
})();
