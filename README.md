# WanderWise — Travel Discovery Website

**Live demo:** [https://haneef-shaik1.github.io/wanderwise-travel-discovery/](https://haneef-shaik1.github.io/wanderwise-travel-discover/)

Open the link in any modern browser to see the finished website. No download or setup is needed.

## 1. What is WanderWise?

WanderWise is a premium, scroll-driven travel discovery website built with **only HTML5, CSS3, vanilla JavaScript and JSON**. There are no frameworks, no build step, no backend and no database. Scroll the page and the scene changes around you: the hero separates into parallax layers, and a sticky "stage" swaps destinations with cinematic image reveals while text animates in piece by piece.

> **About the images:** the bundled pictures are original *illustrations* generated for this project, not photographs, because photo sites could not be reached while building it. See [CREDITS.md](CREDITS.md) and [Replacing destination images](#11-replacing-destination-images).

## 2. Main features and interactions

- **Cinematic hero** with a Ken Burns background, drifting mist, staggered headline, featured-destination label and an animated scroll cue.
- **Immersive destination showcase**: eight destinations presented in one sticky, scroll-driven stage. Images wipe in, text staggers independently, a counter and progress bar update, and side dots let you jump to any stop.
- **Page scroll-progress bar** across the top of the viewport.
- **Explore gallery**: live search, category filter chips, sort by name or indicative budget, hover image zoom and a clear empty state.
- **Destination details**: a modal (native `<dialog>`) with the full description, best time, budget, attractions, activities, tips and a favourite button. Closes with Esc, the × button or a backdrop click.
- **Wishlist**: save and remove favourites; the heart buttons, header badge and wishlist section stay in sync and persist after refresh.
- **Trip planner**: add destinations, choose a date, travelers and budget, and see an estimated total. Saved and restored automatically.
- **Experiences**: an expanding image accordion; each panel jumps to the gallery filtered by that style.
- **Accessible by default**: skip link, semantic landmarks, keyboard-operable controls, visible focus rings, `aria-pressed` states, live regions and full `prefers-reduced-motion` support.

## 3. Technologies used

| Area | What is used |
|------|--------------|
| Markup | Semantic HTML5 (`header`, `main`, `section`, `article`, `nav`, `dialog`, `dl`) |
| Styling | CSS3, custom properties, Grid, Flexbox, `position: sticky`, `clip-path`, `@keyframes`, media queries |
| Behaviour | Vanilla JavaScript ES modules, Fetch API, IntersectionObserver, `requestAnimationFrame`, LocalStorage |
| Data | One JSON file: `data/destinations.json` |
| Images | Local `.jpg` files under `assets/images/` |

## 4. Project folder structure

```
wanderwise/
├── index.html
├── README.md
├── CREDITS.md
├── data/
│   └── destinations.json
├── assets/
│   ├── images/          # hero, 8 destinations, 5 experiences (.jpg)
│   └── icons/           # favicon.svg, placeholder.svg (image fallback)
├── css/
│   ├── style.css        # tokens, layout and components
│   ├── animations.css   # @keyframes + reveal classes + reduced motion
│   └── responsive.css   # breakpoints
├── js/
│   ├── app.js           # entry point
│   ├── destinations.js  # data, showcase, gallery, modal
│   ├── animations.js    # scroll-driven effects
│   ├── wishlist.js      # favourites
│   ├── planner.js       # trip planner
│   └── utils.js         # shared helpers
└── tools/
    └── generate_images.py   # optional: regenerates the illustrations
```

## 5. What each file does

**HTML**
- `index.html`: all page sections (hero, showcase mount point, gallery, wishlist, planner, experiences, about, CTA, footer), the details `<dialog>`, a toast region, and a small non-module script that explains the `file://` limitation.

**CSS**
- `css/style.css`: design tokens (colours, spacing, fonts, radii, easing), base styles and every component.
- `css/animations.css`: all `@keyframes` (see section 8) plus scroll-reveal classes and the reduced-motion overrides.
- `css/responsive.css`: layout changes for laptop, tablet and phone widths, the mobile navigation, and the swipe-row (non-sticky) showcase and gallery layout on phones.

**JavaScript**
- `js/app.js`: loads the data, then initialises every module; handles image fallbacks and the load-error screen with a retry button.
- `js/destinations.js`: fetches and validates JSON, renders the showcase and gallery, runs search / filter / sort, and powers the details modal.
- `js/animations.js`: page progress bar, hero parallax, the sticky showcase controller, IntersectionObserver reveals, count-up numbers, the experiences accordion and header behaviour.
- `js/wishlist.js`: favourites state, LocalStorage persistence, button syncing and the wishlist section.
- `js/planner.js`: itinerary state, budget maths, persistence and rendering.
- `js/utils.js`: DOM helpers, currency formatting, safe LocalStorage wrapper, toast, HTML escaping.

**Data**
- `data/destinations.json`: the eight destination records; the single source of truth for every card, modal, filter and showcase stop.

## 6. How destination data is loaded

1. `app.js` calls `loadDestinations()`, which uses `fetch('data/destinations.json')`.
2. The response must be a JSON array. Each record is validated: required text fields, three non-empty lists and numeric `budgetMin <= budgetMax`. Invalid records are skipped with a console warning.
3. If the file is missing, malformed, or has no valid records, a friendly error appears with a **Try again** button. When the page is opened over `file://`, a banner explains how to start a local server.
4. The validated array feeds the showcase, gallery, modal, wishlist and planner. Nothing is duplicated in HTML or JavaScript.

## 7. How LocalStorage is used

| Key | Contents |
|-----|----------|
| `wanderwise.wishlist` | Array of favourite destination ids, e.g. `[1,5]` |
| `wanderwise.itinerary` | `{ items: [ids], date, travelers, budget }` |

- Reads and writes are wrapped in `try/catch`, so a browser that blocks storage degrades gracefully instead of crashing.
- Ids that no longer exist in the JSON are dropped when loading, so editing the data never breaks saved state.
- The itinerary saves automatically on every change; **Save itinerary** gives explicit confirmation, and **Clear** removes it.
- Nothing ever leaves your browser. To reset everything, clear the site's data in your browser settings.

## 8. How the scroll-driven animations work

Scrolling is never hijacked. The page scrolls natively; JavaScript only *reads* the scroll position (one shared, `requestAnimationFrame`-throttled listener) and updates CSS variables and classes.

**The sticky showcase**
- `.showcase__track` is a tall element (about 85vh per destination). Inside it, `.showcase__sticky` uses `position: sticky; top: 0; height: 100vh`, so the stage stays fixed while you scroll through the track.
- Scroll progress through the track is `progress = -rect.top / (trackHeight - viewportHeight)`. Multiplied by the number of destinations, it gives the active index.
- Each slide's image is clipped with `clip-path: inset(100% 0 0 0)`. Becoming active transitions it to `inset(0)`, a wipe-up reveal. Scrolling back reverses it.
- Inside the active slide the image drifts via `--shift`, a per-slide CSS variable derived from fractional progress, giving a parallax feel.
- Text parts (kicker, title, country, description, stats, buttons) share a `.rv` class with staggered `transition-delay` driven by `--i`. Entering text rises in; leaving text lifts away, so each part animates independently.
- Inactive panels get the `inert` attribute so they can't be focused or read, keeping keyboard and screen-reader use correct.

**Other effects**
- **Hero parallax**: background, two mist layers and the content move at different speeds; content fades as you leave.
- **Reveals**: `IntersectionObserver` adds `.is-visible` to sections, cards and wishlist items; CSS transitions do the animating.
- **Counters** count up once when visible. The **progress bar** is a `transform: scaleX()`.

**`@keyframes` used** (all in `css/animations.css`): `kenBurns` (hero zoom), `riseIn` and `fadeUp` (hero text), `mistDriftA/B` (foreground mist), `scrollWheel` and `cueBob` (scroll cue), `pulseRing` (featured dot), `shimmer` (loading skeletons), `slideIn` (itinerary rows), `modalIn` and `backdropIn` (details modal), `toastPop` (notifications), `heartPop` (favourite button) and `hintSlide` (showcase hint).

**Performance & accessibility**: effects use `transform`, `opacity` and `clip-path`; `will-change` is applied sparingly; images are lazy-loaded after the first two. With `prefers-reduced-motion: reduce`, animations and transitions are neutralised, parallax is skipped, content is shown immediately, and the sticky showcase is replaced by a plain stacked list.

**Mobile (≤ 820px)**: the sticky stage is replaced by a side-scrolling, snap-to-card row (the Explore gallery uses the same swipe row), so no content becomes inaccessible, and parallax work is skipped.

## 9. How to run the application locally

WanderWise reads its data with the Fetch API and uses ES modules, so browsers **block it when you double-click `index.html`** (a `file://` URL). Serve it over HTTP instead. No package installation, API key, database or backend is needed.

**Extract the ZIP first:** right-click `wanderwise.zip` → *Extract All* (Windows), double-click it (macOS), or run `unzip wanderwise.zip` (Linux/macOS terminal). You will get a `wanderwise/` folder.

### Option 1: Visual Studio Code

1. Open VS Code → **File → Open Folder** → choose the `wanderwise` folder.
2. Install the **Live Server** extension (by Ritwick Dey) if you don't have it: Extensions panel → search "Live Server" → Install.
3. Right-click `index.html` in the Explorer.
4. Choose **Open with Live Server**.
5. Open the local URL it shows (usually `http://127.0.0.1:5500`).

### Option 2: Python

If Python is installed, open a terminal **inside the project folder** and run:

```bash
python -m http.server 8000
```

(use `python3 -m http.server 8000` if `python` isn't found), then open:

```
http://localhost:8000
```

**To stop the server:** click the terminal and press `Ctrl + C`.

## 10. How to add or edit destinations

Open `data/destinations.json` and add an object to the array (keep the commas valid):

```json
{
  "id": 9,
  "name": "Lisbon",
  "country": "Portugal",
  "category": "Culture",
  "shortDescription": "One-line teaser used on cards and the showcase.",
  "description": "A longer paragraph shown in the details modal.",
  "image": "assets/images/lisbon.jpg",
  "imageAlt": "Describe the picture for screen readers",
  "imagePosition": "50% 50%",
  "bestTimeToVisit": "March to June",
  "budgetMin": 70000,
  "budgetMax": 130000,
  "currency": "INR",
  "idealDays": "4–6 days",
  "climate": "Mild, 12–28°C",
  "highlights": ["Alfama", "Belém Tower"],
  "activities": ["Ride Tram 28"],
  "travelTips": ["Wear comfortable shoes for the hills"],
  "featured": false
}
```

- `id` must be a unique number. Required: `name`, `country`, `category`, `shortDescription`, `description`, `image`, `bestTimeToVisit`, `budgetMin`, `budgetMax` and the three lists. Optional: `imageAlt`, `imagePosition`, `idealDays`, `climate`, `featured`, `currency`.
- Everything updates automatically: showcase stop count, gallery cards, filter chips (from `category`), the planner dropdown and the About-section counters. Set `"featured": true` on one record to change the hero label.
- Budgets are **indicative per-person estimates** for roughly a week, excluding international flights.
- The showcase height is computed from the number of records, so any count works; 5–8 is recommended for pacing.

## 11. Replacing destination images

1. Save your photo in `assets/images/` (the existing filenames are listed in `CREDITS.md`), either overwriting a file or using a new name.
2. If you used a new name, update the record's `"image"` path in `data/destinations.json`.
3. Update `"imageAlt"` and, if the subject sits off-centre, `"imagePosition"` (CSS `object-position`, e.g. `"50% 30%"`).
4. Recommended: about 1600×1000 px, JPEG quality around 80, ideally under 300 KB.
5. The hero, CTA and experience images are referenced directly in `index.html`.
6. Record the photographer, URL and license in `CREDITS.md`.

If an image fails to load, a local placeholder (`assets/icons/placeholder.svg`) is shown automatically.

## 12. Browser compatibility and limitations

- Tested in Chromium. Targets current Chrome, Edge, Firefox and Safari (2023 or later). Required features: ES modules, `<dialog>`, `inert`, `clip-path`, CSS `:has()` (used only for a focus ring), `position: sticky`.
- It must be served over HTTP(S); `file://` is not supported (a banner explains this).
- All prices are **indicative estimates**, not live travel prices.
- Favourites and itineraries live in one browser on one device and do not sync across devices; private windows may discard them.
- The bundled artwork consists of illustrations, not photos of the real places.
- There is no backend, search index or authentication, by design.

## 13. Image attribution and licensing

The 14 bundled images are original, procedurally generated illustrations released as CC0 / public domain, and no third-party photographs are included. Full details, plus a log for recording real photographs you add, are in [CREDITS.md](CREDITS.md).
