// StephenA Away v1.1 - Content script for ESPN
// Replaces Stephen A. Smith content with The Onion headlines about him

(function() {
  'use strict';

  // The Onion headlines about Stephen A. Smith (comprehensive archive)
  const ONION_HEADLINES = [
    {
      "headline": "Stephen A. Smith Hasn't Ruled Out Living Cushy Life As Millionaire TV Personality With No Responsibilities",
      "url": "https://theonion.com/stephen-a-smith-hasnt-ruled-out-living-cushy-life-as-millionaire-tv-personality-with-no-responsibilities/",
      "image": "https://theonion.com/wp-content/uploads/2025/04/Stephen_A_Smith_Says-NIB-PH.jpg"
    },
    {
      "headline": "Stephen A. Smith Thinking Son Is Finally Ready For The Sex Argument",
      "url": "https://theonion.com/stephen-a-smith-thinking-son-is-finally-ready-for-the-1819573914/",
      "image": "https://theonion.com/wp-content/uploads/2012/09/xs6dcih644khfztg0nig.jpg"
    },
    {
      "headline": "Stephen A. Smith Recalls Rough Childhood Having To Debate Gang Members",
      "url": "https://theonion.com/stephen-a-smith-recalls-rough-childhood-having-to-deba-1850864895/",
      "image": "https://theonion.com/wp-content/uploads/2023/09/bf53bb52ce8ecb8ea592559d87ad178a.jpg"
    },
    {
      "headline": "Stephen A. Smith Blasts Ja Morant For Poor Gun-Handling Fundamentals",
      "url": "https://theonion.com/stephen-a-smith-blasts-ja-morant-for-poor-gun-handling-1850451271/",
      "image": "https://theonion.com/wp-content/uploads/2023/05/306410a4faaa91cd97d1213831d7517c.png"
    },
    {
      "headline": "Stephen A. Smith Blasts Anthony Davis For Refusing To Play Through Groin Surgery",
      "url": "https://theonion.com/stephen-a-smith-blasts-anthony-davis-for-refusing-to-p-1847046531/",
      "image": "https://theonion.com/wp-content/uploads/2021/06/c497c77c03dd840d4135aaebcbf3b5cb.jpg"
    },
    {
      "headline": "Stephen A. Smith Blasts Laid-Off ESPN Employees For Not Wanting Jobs Bad Enough",
      "url": "https://theonion.com/stephen-a-smith-blasts-laid-off-espn-employees-for-not-1850375000/",
      "image": "https://theonion.com/wp-content/uploads/2023/04/7ba0ac9dd45a6c4cef4a377dc425aeb2.jpg"
    },
    {
      "headline": "Stephen A. Smith Retreats To Tranquil, Secluded Fig Tree To Contemplate On Meaning Of NFL Week One",
      "url": "https://theonion.com/stephen-a-smith-retreats-to-tranquil-secluded-fig-tre-1838015144/",
      "image": "https://theonion.com/wp-content/uploads/2019/09/yqjajl1twozittcbrlhg.jpg"
    },
    {
      "headline": "Stephen A. Smith's Dismissive Attitude Toward Hockey Gets People To Like Hockey",
      "url": "https://theonion.com/stephen-a-smiths-dismissive-attitude-toward-hockey-get-1819574668/",
      "image": "https://theonion.com/wp-content/uploads/2013/03/wjtlo4gmt8himzzqztb1.jpg"
    },
    {
      "headline": "Stephen A. Smith Reveals He Still Meets Up With Skip Bayless To Argue",
      "url": "https://theonion.com/stephen-a-smith-reveals-he-still-meets-up-with-skip-ba-1819580024/",
      "image": "https://theonion.com/wp-content/uploads/2017/06/cty5kcrfufhh1a8mv10l.jpg"
    },
    {
      "headline": "Nation Feels Fucking Awful For Woman Who Sits Between Skip Bayless, Stephen A. Smith",
      "url": "https://theonion.com/nation-feels-fucking-awful-for-woman-who-sits-between-s-1819575478/",
      "image": "https://theonion.com/wp-content/uploads/2013/08/mradpj3qpqrfqq3oytta.jpg"
    },
    {
      "headline": "Shohei Ohtani's Translator: 'There Are No Words In Japanese To Describe Stephen A. Smith'",
      "url": "https://theonion.com/shohei-ohtani-s-translator-there-are-no-words-in-japa-1847284629/",
      "image": "https://theonion.com/wp-content/uploads/2021/07/80de59e2be66df9c46b29d409c158002.jpg"
    },
    {
      "headline": "Stephen A. Smith: 'I've Loved Ha-Seong Kim For Years, But He Will Simply Never Be The Player Jeong Choi Is'",
      "url": "https://theonion.com/stephen-a-smith-i-ve-loved-ha-seong-kim-for-years-b-1843319538/",
      "image": "https://theonion.com/wp-content/uploads/2020/05/rw5xalyvz9cfqg2mactk.jpg"
    }
  ];

  // Track which headlines have been used on this page (no duplicates)
  const usedHeadlines = new Set();

  // Patterns to match Stephen A. Smith content
  const PATTERNS = [
    /stephen\s*a\.?\s*smith/i,
    /stephen\s*a\s*$/i,
    /\bstephen\s*a\b/i,
    /first\s*take/i,
    /smith['']?s\s*take/i
  ];

  // Track replaced count for debugging
  let replacedCount = 0;

  // Get a random Onion headline (no duplicates on same page)
  function getRandomOnion() {
    // Filter to headlines not yet used on this page
    const available = ONION_HEADLINES.filter(h => !usedHeadlines.has(h.url));

    // If all headlines used, reset and start over
    if (available.length === 0) {
      usedHeadlines.clear();
      return getRandomOnion();
    }

    // Pick a random one from available
    const selected = available[Math.floor(Math.random() * available.length)];
    usedHeadlines.add(selected.url);
    return selected;
  }

  // Check if text contains Stephen A. Smith references
  function containsStephenA(text) {
    if (!text) return false;
    return PATTERNS.some(pattern => pattern.test(text));
  }

  // Create replacement content that matches ESPN styling
  function createOnionReplacement(onion, originalElement) {
    const container = document.createElement('div');
    container.className = 'stephena-away-onion';
    container.style.cssText = `
      background: #ffffff;
      padding: 12px;
      margin-bottom: 8px;
      border-radius: 5px;
    `;

    // Content wrapper - horizontal layout with image and text
    const contentWrapper = document.createElement('div');
    contentWrapper.style.cssText = 'display: flex; gap: 12px; align-items: flex-start;';

    // Image (if available)
    if (onion.image) {
      const imgLink = document.createElement('a');
      imgLink.href = onion.url;
      imgLink.target = '_blank';
      imgLink.rel = 'noopener noreferrer';
      imgLink.style.cssText = 'flex-shrink: 0;';

      const img = document.createElement('img');
      img.src = onion.image;
      img.alt = '';
      img.style.cssText = `
        width: 120px;
        height: 68px;
        object-fit: cover;
        display: block;
      `;
      img.onerror = () => { imgLink.style.display = 'none'; };
      imgLink.appendChild(img);
      contentWrapper.appendChild(imgLink);
    }

    // Text content
    const textContent = document.createElement('div');
    textContent.style.cssText = 'flex: 1; min-width: 0; overflow: hidden;';

    const link = document.createElement('a');
    link.href = onion.url;
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    link.style.cssText = `
      color: #000000;
      text-decoration: none;
      font-family: "Helvetica Neue", "Arial", sans-serif;
      font-size: 14px;
      font-weight: 500;
      line-height: 1.3;
      display: block;
      word-wrap: break-word;
      overflow-wrap: break-word;
    `;
    link.textContent = onion.headline;
    link.onmouseover = () => { link.style.color = '#0066cc'; };
    link.onmouseout = () => { link.style.color = '#000000'; };

    textContent.appendChild(link);
    contentWrapper.appendChild(textContent);
    container.appendChild(contentWrapper);

    return container;
  }

  // Replace an element with Onion content
  function replaceElement(element, reason) {
    if (element && element.parentNode && !element.classList.contains('stephena-away-onion')) {
      const onion = getRandomOnion();
      const replacement = createOnionReplacement(onion, element);
      element.parentNode.replaceChild(replacement, element);
      replacedCount++;
      console.log(`[StephenA Away] Replaced: ${reason} -> "${onion.headline.substring(0, 50)}..."`);
    }
  }

  // Scan and replace Stephen A content on the page
  function scanAndReplace() {
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
        if (element.classList.contains('stephena-away-onion')) return;

        const text = element.textContent || '';
        const imgAlt = Array.from(element.querySelectorAll('img'))
          .map(img => img.alt || '')
          .join(' ');

        if (containsStephenA(text) || containsStephenA(imgAlt)) {
          replaceElement(element, `Matched in ${selector}`);
        }
      });
    });

    // Check headlines specifically
    document.querySelectorAll('h1, h2, h3, h4, a[href*="stephen"], a[href*="first-take"]').forEach(element => {
      if (element.closest('.stephena-away-onion')) return;

      if (containsStephenA(element.textContent) ||
          (element.href && containsStephenA(element.href))) {
        const container = element.closest('article, .contentItem, .Card, li, .feed-item') || element;
        if (!container.classList.contains('stephena-away-onion')) {
          replaceElement(container, 'Headline match');
        }
      }
    });

    // Check video embeds
    document.querySelectorAll('iframe, video, [data-video-id]').forEach(element => {
      if (element.closest('.stephena-away-onion')) return;

      const title = element.title || element.getAttribute('data-title') || '';
      if (containsStephenA(title)) {
        const container = element.closest('.video-item, .media-pod, article') || element;
        if (!container.classList.contains('stephena-away-onion')) {
          replaceElement(container, 'Video match');
        }
      }
    });
  }

  // MutationObserver for dynamic content
  function observeChanges() {
    const observer = new MutationObserver((mutations) => {
      let shouldScan = false;
      mutations.forEach(mutation => {
        if (mutation.addedNodes.length > 0) {
          shouldScan = true;
        }
      });

      if (shouldScan) {
        clearTimeout(observeChanges.timeout);
        observeChanges.timeout = setTimeout(scanAndReplace, 100);
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
      scanAndReplace();
      observeChanges();
    });
  } else {
    scanAndReplace();
    observeChanges();
  }

  // Scan again for lazy-loaded content
  setTimeout(scanAndReplace, 1000);
  setTimeout(scanAndReplace, 3000);

  console.log('[StephenA Away v1.1] Onion mode loaded on ESPN 🧅');
})();
