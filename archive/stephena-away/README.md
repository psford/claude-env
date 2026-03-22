# StephenA Away

A Firefox extension that filters Stephen A. Smith content from ESPN.

## Versions

| Version | Mode | Description |
|---------|------|-------------|
| **1.0.0** | Hide | Removes Stephen A. Smith content entirely from ESPN pages |
| **1.1.0** | Onion | Replaces SAS content with satirical Onion headlines about him |

## Installation

### Signed Release (v1.0.0)
1. Download `stephena-away-1.0.0.zip`
2. In Firefox: `about:addons` → gear icon → "Install Add-on From File"
3. Select the zip file

### Temporary Install (for testing v1.1.0)
1. In Firefox: navigate to `about:debugging#/runtime/this-firefox`
2. Click "Load Temporary Add-on"
3. Select `manifest-v1.1.json` from this folder

## Files

```
stephena-away/
├── content.js          # v1.0 - hide mode (removes SAS content)
├── manifest.json       # v1.0 manifest
├── content-v1.1.js     # v1.1 - Onion mode (replaces with Onion headlines)
├── manifest-v1.1.json  # v1.1 manifest (different addon ID)
├── onion_headlines.json # Reference: 12 verified Onion articles about SAS
├── build_zip.ps1       # Build script for v1.0
├── build_zip_v1.1.ps1  # Build script for v1.1
├── icons/
│   ├── icon-48.svg     # Toolbar icon (prohibition sign over SAS)
│   └── icon-96.svg     # High-res icon
└── ROADMAP.md          # Feature roadmap
```

## How It Works

### Detection Patterns
The extension matches Stephen A. Smith content using these patterns:
- `stephen a. smith` / `stephen a smith` (case insensitive)
- `stephen a` as standalone phrase
- `first take` (his show)
- `smith's take`

### Selectors Scanned
ESPN content containers targeted:
- `article`, `.contentItem`, `.Card`
- `.headlineStack__list li`, `.carousel__item`
- `.video-item`, `.media-pod`
- `[data-mptype="story"]`, `[data-mptype="video"]`
- Headlines: `h1, h2, h3, h4`
- Links containing `stephen` or `first-take`

### Dynamic Content
A MutationObserver watches for dynamically loaded content and re-scans with 100ms debounce. Additional scans run at 1s and 3s after page load to catch lazy-loaded content.

## Onion Headlines Index (v1.1)

The extension includes 12 verified Onion articles about Stephen A. Smith:

| Date | Headline |
|------|----------|
| 2025-04 | Stephen A. Smith Hasn't Ruled Out Living Cushy Life As Millionaire TV Personality... |
| 2023-09 | Stephen A. Smith Recalls Rough Childhood Having To Debate Gang Members |
| 2023-05 | Stephen A. Smith Blasts Ja Morant For Poor Gun-Handling Fundamentals |
| 2023-04 | Stephen A. Smith Blasts Laid-Off ESPN Employees For Not Wanting Jobs Bad Enough |
| 2021-07 | Shohei Ohtani's Translator: 'There Are No Words In Japanese To Describe Stephen A. Smith' |
| 2021-06 | Stephen A. Smith Blasts Anthony Davis For Refusing To Play Through Groin Surgery |
| 2020-05 | Stephen A. Smith: 'I've Loved Ha-Seong Kim For Years...' |
| 2019-09 | Stephen A. Smith Retreats To Tranquil, Secluded Fig Tree... |
| 2017-10 | Stephen A. Smith Reveals He Still Meets Up With Skip Bayless To Argue |
| 2013-08 | Nation Feels Fucking Awful For Woman Who Sits Between Skip Bayless, Stephen A. Smith |
| 2013-03 | Stephen A. Smith's Dismissive Attitude Toward Hockey Gets People To Like Hockey |
| 2012-09 | Stephen A. Smith Thinking Son Is Finally Ready For The Sex Argument |

All articles have verified image URLs. The extension prevents duplicate headlines on the same page using a Set-based tracker.

## Styling (v1.1)

Replacement cards match ESPN's visual style:
- **Background:** `#ffffff`
- **Border radius:** `5px`
- **Padding:** `12px`
- **Font:** Helvetica Neue, Arial, sans-serif
- **Font size:** `14px`
- **Font weight:** `500`
- **Layout:** Horizontal flex with 120x68px thumbnail

## Building

```powershell
# Build v1.0
.\build_zip.ps1

# Build v1.1
.\build_zip_v1.1.ps1
```

## Browser Compatibility

Built for Firefox (Manifest V2). Uses standard DOM APIs and CSS - no browser-specific features.

## License

MIT
