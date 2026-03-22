# Road Trip Photo Map Design

## Summary

Road Trip Map is a lightweight, mobile-first web application that lets a trip organizer create a shared trip in seconds and hand two links to anyone who needs them: a secret link for posting photos and a public link for viewing the map. There are no accounts, no logins, and no app to install — the secret link is the only credential needed to post.

The application is built on ASP.NET Core Minimal API, serving a vanilla HTML/JS/CSS frontend as static files. When a traveler taps the secret link and picks a photo on their phone, GPS coordinates are extracted directly in the browser from the photo's EXIF metadata. Those coordinates are reverse-geocoded server-side into a human-readable place name ("Grand Canyon, AZ") and cached to avoid redundant lookups. The photo is stored in three tiers — thumbnail, display-quality, and lossless original — in Azure Blob Storage, with EXIF data stripped from every copy. Anyone with the view link can open a Leaflet.js map, see pins at each photo location, tap a pin to see the photo and metadata, and optionally toggle a route line that connects the stops in chronological order. Authorization is pluggable by design: Phase 1 uses a secret token embedded in the URL, but the interface boundary is already in place for PIN codes or OAuth to be dropped in later without changing any endpoint logic.

## Definition of Done

1. **A mobile-first website** where anyone can create a road trip and get two links: a secret post link and a public view link.
2. **Zero-friction posting** via secret link — one tap, pick/take photo, auto-GPS from EXIF + auto-resolved place name, optional caption, done.
3. **Public map view** — anyone with the view link sees a map with photo pins and an optional chronological route line connecting them.
4. **Reusable** — anyone can create new trips from the homepage. Not a single-use app.
5. **No login system** — secret links for posting, public links for viewing. No accounts.
6. **Modular auth** — the secret-link authorization mechanism must be pluggable/swappable so PIN codes or proper auth can replace it later without architectural changes. Privacy constraint: parents' location must not be discoverable by web crawlers.

## Acceptance Criteria

### road-trip-map.AC1: Trip Creation
- **road-trip-map.AC1.1 Success:** Submitting a name creates a trip and returns a unique slug, secret token, view URL, and post URL
- **road-trip-map.AC1.2 Success:** Generated slug is URL-friendly (lowercase, hyphens, no special characters)
- **road-trip-map.AC1.3 Success:** Duplicate trip names produce unique slugs (suffix or variation)
- **road-trip-map.AC1.4 Failure:** Empty trip name returns 400 validation error
- **road-trip-map.AC1.5 Edge:** Very long trip names are truncated to a reasonable slug length

### road-trip-map.AC2: Photo Posting
- **road-trip-map.AC2.1 Success:** Photo uploaded with valid secret token is stored in three tiers (original, display, thumbnail)
- **road-trip-map.AC2.2 Success:** GPS coordinates extracted from EXIF client-side are sent with upload and stored
- **road-trip-map.AC2.3 Success:** Place name auto-resolved from coordinates and displayed before confirming
- **road-trip-map.AC2.4 Success:** Caption is optional — photo posts successfully with or without one
- **road-trip-map.AC2.5 Success:** Original photo is downloadable at full quality (no degradation)
- **road-trip-map.AC2.6 Failure:** Upload without valid secret token returns 401
- **road-trip-map.AC2.7 Failure:** Non-image file upload returns 400
- **road-trip-map.AC2.8 Failure:** File exceeding 15MB returns 400
- **road-trip-map.AC2.9 Edge:** Photo without GPS EXIF shows fallback pin-drop map for manual location

### road-trip-map.AC3: Map View
- **road-trip-map.AC3.1 Success:** Map displays pins at correct GPS coordinates for each photo
- **road-trip-map.AC3.2 Success:** Clicking a pin shows display-quality image, place name, caption, and timestamp
- **road-trip-map.AC3.3 Success:** Route line toggle connects pins chronologically with a polyline
- **road-trip-map.AC3.4 Success:** Map auto-fits bounds to show all pins on load
- **road-trip-map.AC3.5 Success:** "Download original" link in popup serves full-quality photo
- **road-trip-map.AC3.6 Edge:** Trip with zero photos shows empty map with message
- **road-trip-map.AC3.7 Edge:** Trip with one photo centers map on that pin (no route line)

### road-trip-map.AC4: Reusability
- **road-trip-map.AC4.1 Success:** Homepage allows creating multiple independent trips
- **road-trip-map.AC4.2 Success:** Each trip has its own slug, token, photos, and map

### road-trip-map.AC5: No Login System
- **road-trip-map.AC5.1 Success:** Viewing a trip map requires no authentication — just the URL
- **road-trip-map.AC5.2 Success:** Posting requires only the secret link — no username, password, or account
- **road-trip-map.AC5.3 Success:** Creating a trip requires no authentication

### road-trip-map.AC6: Modular Auth & Privacy
- **road-trip-map.AC6.1 Success:** Auth strategy is injected via DI and swappable without code changes to endpoints
- **road-trip-map.AC6.2 Success:** Trip pages are not indexed by search engines (robots.txt + meta tags + headers)
- **road-trip-map.AC6.3 Success:** EXIF data is stripped from all stored photo files
- **road-trip-map.AC6.4 Success:** Photos are not accessible via direct blob URLs — served through API only
- **road-trip-map.AC6.5 Failure:** Guessing a random slug returns 404 (no trip enumeration)
- **road-trip-map.AC6.6 Failure:** Upload rate exceeding 20/hr from same IP is throttled

## Glossary

- **ASP.NET Core Minimal API**: A .NET web framework style that defines HTTP endpoints as simple lambda functions rather than controller classes. Used here because the app's surface area is small.
- **EF Core (Entity Framework Core)**: Microsoft's ORM for .NET. Defines database schema in C# and applies it via migrations.
- **EF Core migration**: A versioned, code-generated file that records a schema change. Applied automatically on startup in production; manually with `dotnet ef database update` locally.
- **Azure Blob Storage**: Microsoft's object/file storage service. Stores the three photo tiers in a private container, proxied through the API.
- **Azure App Service**: Microsoft's managed hosting platform. The road-trip app shares an existing App Service Plan with Stock Analyzer as a second web app.
- **Azure SQL**: Microsoft's managed SQL Server service. Shared database instance with Stock Analyzer, isolated under the `roadtrip` schema.
- **Leaflet.js**: Open-source JavaScript mapping library (BSD-2). Renders the interactive map using OpenStreetMap tiles with pin markers and polyline primitives.
- **OpenStreetMap (OSM)**: Community-maintained, openly licensed map dataset. Provides the tile layer (background map imagery) rendered by Leaflet.
- **Nominatim**: OSM's free reverse-geocoding service. Converts lat/lng into place names. Rate-limited to 1 request/second per usage policy.
- **Reverse geocoding**: Converting GPS coordinates into a readable address or place name.
- **exifr**: MIT-licensed JavaScript library that reads EXIF metadata from image files in the browser. Extracts GPS coordinates and timestamp before upload.
- **EXIF**: Metadata embedded in JPEG files by cameras/phones. Can include GPS location, timestamp, camera model. Stripped from stored copies for privacy.
- **SkiaSharp**: Cross-platform .NET graphics library (MIT). Resizes photos into display and thumbnail tiers server-side.
- **GeoCache**: App's internal reverse-geocoding cache table. Stores place names keyed by coordinates rounded to ~1km grid to avoid redundant Nominatim lookups.
- **IAuthStrategy**: C# interface abstracting the authorization check for photo posting. Allows auth mechanism (secret token, PIN, OAuth) to be swapped via DI without changing endpoint code.
- **DI (Dependency Injection)**: .NET pattern where concrete implementations are registered in `Program.cs` and injected into services. The `IAuthStrategy` swap relies on this.
- **Secret token**: UUID v4 string (122 bits of entropy) embedded in the post URL. Possession of the URL is the only credential needed to post photos.
- **Slug**: URL-friendly identifier derived from trip name (e.g., `parents-cross-country-2026`). Used in the public view URL.
- **Polyline**: Connected line segments between coordinate points on a map. Used as the optional route line connecting photo pins chronologically.
- **Three-tier photo storage**: Storing each photo at three resolutions — original (unmodified), display (max 1920px), and thumbnail (max 300px) — serving the right quality for each use case.
- **robots.txt**: Text file at site root instructing web crawlers which paths not to index.
- **X-Robots-Tag**: HTTP response header telling crawlers not to index the page. Supplements `robots.txt` for API responses.
- **`roadtrip` schema**: SQL Server schema namespace grouping road-trip tables within the shared Azure SQL database, isolated from Stock Analyzer's `data` schema.

## Architecture

ASP.NET Core Minimal API serving a vanilla HTML/JS/CSS frontend as static files. Photos stored in Azure Blob Storage, metadata in Azure SQL (shared instance with Stock Analyzer, `roadtrip` schema). Leaflet.js with OpenStreetMap tiles for map rendering. Client-side EXIF extraction via `exifr` (MIT).

```
[iPhone / Browser]
    ├── POST /api/trips/{secret-token}/photos  (multipart: photo + lat/lng + caption)
    ├── GET  /trips/{slug}                     (public map view)
    └── GET  /create                           (new trip form)

[ASP.NET Core Minimal API]
    ├── Static files (HTML/JS/CSS)
    ├── API endpoints (trip CRUD, photo upload/serve)
    ├── IAuthStrategy middleware (pluggable)
    ├── IGeocodingService (Nominatim + GeoCache)
    ├── IPhotoService (resize, EXIF strip, blob upload)
    └── EF Core DbContext (roadtrip schema)

[Azure SQL]                         [Azure Blob Storage]
    roadtrip.Trips                      road-trip-photos/
    roadtrip.Photos                         {tripId}/{photoId}.jpg
    roadtrip.GeoCache                       {tripId}/{photoId}_display.jpg
                                            {tripId}/{photoId}_thumb.jpg
```

### URL Structure

| URL | Purpose | Access |
|-----|---------|--------|
| `/create` | Create new trip form | Public |
| `/trips/{slug}` | Map view | Public (unlisted) |
| `/post/{secret-token}` | Photo posting page | Secret link |
| `/api/trips` | REST API | Varies by endpoint |

### Data Model

**Trips** — `roadtrip` schema

| Column | Type | Notes |
|--------|------|-------|
| Id | int, PK | Auto-increment |
| Slug | varchar, unique | URL-friendly name, e.g., `parents-cross-country-2026` |
| Name | nvarchar | Display name |
| Description | nvarchar, nullable | Optional trip description |
| SecretToken | varchar, unique | UUID v4 for posting auth |
| CreatedAt | datetime2 | |
| IsActive | bit | Soft-disable trips |

**Photos** — `roadtrip` schema

| Column | Type | Notes |
|--------|------|-------|
| Id | int, PK | Auto-increment |
| TripId | int, FK → Trips | |
| BlobPath | varchar | Base path in blob container (derives original/display/thumb URLs) |
| Latitude | float | From EXIF or manual pin drop |
| Longitude | float | |
| PlaceName | nvarchar | Reverse-geocoded, e.g., "Grand Canyon, AZ" |
| Caption | nvarchar, nullable | User-provided |
| TakenAt | datetime2 | From EXIF timestamp or upload time |
| CreatedAt | datetime2 | |
| SortOrder | int | Chronological ordering |

**GeoCache** — `roadtrip` schema

| Column | Type | Notes |
|--------|------|-------|
| Id | int, PK | |
| LatRounded | float | Rounded to ~1km grid |
| LngRounded | float | |
| PlaceName | nvarchar | Cached reverse-geocode result |
| CachedAt | datetime2 | |

### Contracts

**Pluggable auth interface:**

```csharp
public interface IAuthStrategy
{
    Task<AuthResult> ValidatePostAccess(HttpContext context, Trip trip);
}

public record AuthResult(bool IsAuthorized, string? DeniedReason = null);
```

Phase 1 implementation: `SecretTokenAuthStrategy` — matches URL token against `Trip.SecretToken`. Future implementations (PIN, OAuth) swap via DI registration.

**API endpoints:**

```
POST   /api/trips                              → CreateTripResponse { slug, secretToken, viewUrl, postUrl }
GET    /api/trips/{slug}                       → TripResponse { name, description, photoCount, createdAt }
GET    /api/trips/{slug}/photos                → PhotoResponse[] { id, thumbnailUrl, displayUrl, originalUrl, lat, lng, placeName, caption, takenAt }
POST   /api/trips/{secret-token}/photos        → PhotoResponse (multipart: file + lat + lng + caption + takenAt)
DELETE /api/trips/{secret-token}/photos/{id}    → 204 No Content
GET    /api/photos/{tripId}/{photoId}/{size}    → image binary (size: original|display|thumb)
```

### Photo Pipeline

Three storage tiers — original quality is always preserved:

| Tier | Max Width | Purpose | When Used |
|------|-----------|---------|-----------|
| Original | Unchanged | Full-quality download | "Download original" link |
| Display | 1920px | Lightbox/popup view | Click on map pin |
| Thumbnail | 300px | Map markers, lists | Map view, post page list |

Processing on upload:
1. Read uploaded file, validate image type and size (max 15MB)
2. Strip EXIF from all stored copies (privacy — no GPS in blob files)
3. Generate display and thumbnail versions via SkiaSharp (MIT, cross-platform)
4. Upload all three to Azure Blob (`road-trip-photos/{tripId}/{photoId}[_display|_thumb].jpg`)
5. Photos served through API endpoint, not direct blob URLs (prevents enumeration)

### Reverse Geocoding

Nominatim (OpenStreetMap, free). Rate limited to 1 request/second per their usage policy. Polite `User-Agent` header. Results cached in `GeoCache` table — lat/lng rounded to ~1km grid so nearby photos reuse lookups.

### Privacy

- `robots.txt` disallows `/post/`, `/trips/`, `/api/`
- `<meta name="robots" content="noindex, nofollow">` on all trip pages
- `X-Robots-Tag: noindex` HTTP header on API responses
- No trip listing or discovery page — must know the slug
- Secret tokens are UUID v4 (122 bits of entropy)
- EXIF stripped from all stored photos
- Blob container is private — photos proxied through API
- Basic IP-based rate limiting on upload endpoint (20 uploads/hour)

## Existing Patterns

This is a greenfield project — no existing road-trip codebase to follow. However, the project shares Azure infrastructure with Stock Analyzer:

- **Azure Blob Storage** — same storage account, new `road-trip-photos` container. Same pattern as `themes` container used for Stock Analyzer theme JSON files.
- **Azure SQL** — same database instance, new `roadtrip` schema. Follows Stock Analyzer's pattern of schema separation (`data` schema for prices/coverage).
- **EF Core migrations** — same migration workflow as Stock Analyzer (create locally, apply on startup in production).
- **Azure App Service** — same App Service Plan, deployed as a second web app.

New patterns introduced:
- **Minimal API** instead of controllers (Stock Analyzer uses controllers). Appropriate for this app's simplicity.
- **Pluggable auth via DI** — new pattern, not present in Stock Analyzer.
- **Static file serving** from Kestrel for the frontend (Stock Analyzer uses `wwwroot` similarly).

## Implementation Phases

<!-- START_PHASE_1 -->
### Phase 1: Project Scaffolding & Database
**Goal:** ASP.NET Core project with EF Core, Azure SQL connection, and initial migration

**Components:**
- `projects/road-trip/src/RoadTripMap/RoadTripMap.csproj` — Minimal API project
- `RoadTripDbContext` — EF Core context with `roadtrip` schema
- `Trip` and `Photo` and `GeoCache` entity classes
- Initial EF Core migration creating all three tables
- `Program.cs` — minimal setup with EF Core, static files, CORS

**Dependencies:** None (first phase)

**Done when:** Project builds, migration applies to local SQL Express, empty app runs on localhost
<!-- END_PHASE_1 -->

<!-- START_PHASE_2 -->
### Phase 2: Trip Creation API & Homepage
**Goal:** Users can create trips and receive post/view links

**Components:**
- `POST /api/trips` endpoint — creates trip, generates slug + secret token
- Slug generation (from trip name, uniqueness check)
- `/create` static page — form with trip name + description, displays generated links with copy buttons
- `CreateTripResponse` DTO

**Dependencies:** Phase 1

**Covers:** road-trip-map.AC1, road-trip-map.AC4

**Done when:** User can fill form, create trip, see and copy both links. Tests verify slug uniqueness, token generation, and API response shape.
<!-- END_PHASE_2 -->

<!-- START_PHASE_3 -->
### Phase 3: Auth Module & Photo Upload API
**Goal:** Pluggable auth and photo upload with three-tier storage

**Components:**
- `IAuthStrategy` interface and `SecretTokenAuthStrategy` implementation
- Auth middleware wired via DI
- `IPhotoService` — EXIF stripping, resize (SkiaSharp), blob upload
- `POST /api/trips/{secret-token}/photos` endpoint
- `DELETE /api/trips/{secret-token}/photos/{id}` endpoint
- `GET /api/photos/{tripId}/{photoId}/{size}` — serves photos from private blob
- Azure Blob Storage integration (`road-trip-photos` container)

**Dependencies:** Phase 2

**Covers:** road-trip-map.AC2, road-trip-map.AC5, road-trip-map.AC6

**Done when:** Photos upload through API with valid token, rejected without. Three image tiers stored in blob. Photos served through API proxy. Auth is swappable via DI. Tests verify auth acceptance/rejection, image tier generation, and blob storage.
<!-- END_PHASE_3 -->

<!-- START_PHASE_4 -->
### Phase 4: EXIF Extraction & Reverse Geocoding
**Goal:** Client-side GPS extraction and server-side place name resolution

**Components:**
- Client-side `exifr` integration — extract lat/lng and timestamp from photo EXIF
- Fallback UI for photos without GPS (manual pin drop on mini-map)
- `IGeocodingService` — Nominatim client with rate limiting (1 req/sec)
- `GeoCache` lookup/insert logic (rounded to ~1km grid)
- Place name stored on photo record after upload

**Dependencies:** Phase 3

**Covers:** road-trip-map.AC2 (GPS/place name aspects)

**Done when:** GPS extracted client-side from EXIF, place name resolved and cached server-side. Fallback works for photos without GPS. Tests verify EXIF parsing, geocode caching, and rate limiting.
<!-- END_PHASE_4 -->

<!-- START_PHASE_5 -->
### Phase 5: Post Page UI
**Goal:** Mobile-first photo posting experience

**Components:**
- `/post/{secret-token}` static page
- Large "Add Photo" button triggering `<input type="file" accept="image/*">`
- Photo preview with auto-resolved place name before confirming
- Optional caption field
- Posted photos list (most recent first) with thumbnails
- Success/error feedback (toast notifications)

**Dependencies:** Phase 3, Phase 4

**Covers:** road-trip-map.AC2

**Done when:** Full posting flow works on mobile: tap → pick photo → see preview with place name → optional caption → post → see in list. Tests verify the upload flow end-to-end.
<!-- END_PHASE_5 -->

<!-- START_PHASE_6 -->
### Phase 6: Map View
**Goal:** Public map with photo pins and route line

**Components:**
- `/trips/{slug}` static page
- Leaflet.js map with OpenStreetMap tiles
- Photo pin markers (thumbnail as marker icon or popup)
- Pin click → popup with display image, place name, caption, timestamp, download-original link
- Route toggle button — polyline connecting pins chronologically
- Auto-fit map bounds to all pins
- `GET /api/trips/{slug}` and `GET /api/trips/{slug}/photos` endpoints

**Dependencies:** Phase 3 (photo serving), Phase 2 (trip data)

**Covers:** road-trip-map.AC3

**Done when:** Map renders with pins for all photos. Clicking pin shows popup with display image and metadata. Route line toggles on/off. Map auto-fits. Download original works. Tests verify map data API, pin rendering, and route toggle.
<!-- END_PHASE_6 -->

<!-- START_PHASE_7 -->
### Phase 7: Privacy & Hardening
**Goal:** Crawler protection, rate limiting, production readiness

**Components:**
- `robots.txt` (disallow `/post/`, `/trips/`, `/api/`)
- Meta `noindex`/`nofollow` tags on all pages
- `X-Robots-Tag: noindex` response header
- IP-based rate limiting on upload endpoint (20/hr)
- Input validation (file type, file size, caption length, slug format)
- Error handling (graceful failures, no stack traces in responses)

**Dependencies:** All prior phases

**Covers:** road-trip-map.AC6

**Done when:** Crawlers blocked from indexing. Upload rate limited. Invalid inputs rejected gracefully. Tests verify robots.txt content, rate limiting behavior, and input validation.
<!-- END_PHASE_7 -->

<!-- START_PHASE_8 -->
### Phase 8: Azure Deployment
**Goal:** Running in production on Azure alongside Stock Analyzer

**Components:**
- Azure App Service configuration (second web app in same plan)
- Azure Blob container `road-trip-photos` creation
- `roadtrip` schema migration applied to production Azure SQL
- Connection strings and app settings in Azure configuration
- Deployment pipeline (GitHub Actions or manual publish)

**Dependencies:** All prior phases

**Done when:** App accessible at production URL. Trip creation, photo upload, and map view all functional against Azure SQL and Blob Storage.
<!-- END_PHASE_8 -->

## Additional Considerations

**Future auth upgrades:** The `IAuthStrategy` interface is designed for this. When ready to add PIN codes:
1. Add `PinHash` column to Trips table (migration)
2. Implement `PinCodeAuthStrategy` (check PIN against hash)
3. Swap DI registration
4. Add PIN entry UI to post page

No architectural changes needed — the interface boundary is already in place.

**EXIF edge cases:** Not all photos have GPS in EXIF (screenshots, edited photos, privacy-stripped photos). The fallback "drop a pin" mini-map handles this. Timestamps may also be missing — fall back to upload time.

**Nominatim reliability:** Free service with no SLA. If Nominatim is down, store the photo with coordinates but null place name. Backfill place names later via a retry mechanism or admin endpoint.
