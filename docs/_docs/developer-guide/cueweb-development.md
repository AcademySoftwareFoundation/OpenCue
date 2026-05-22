---
layout: default
title: CueWeb Development
parent: Developer Guide
nav_order: 97
---

# CueWeb Development Guide
{: .no_toc }

Complete guide for developing, customizing, and deploying CueWeb.

<details open markdown="block">
  <summary>
    Table of contents
  </summary>
  {: .text-delta }
1. TOC
{:toc}
</details>

---

## Development Environment Setup

### Prerequisites

Before starting development, ensure you have:

- **Node.js** (version 18 or later)
- **npm** or **yarn** package manager
- **Git** for version control
- **Docker** (for REST Gateway and testing)
- **OpenCue** running instance (Cuebot, RQD, PostgreSQL)

### Clone and Setup

```bash
# Clone OpenCue repository
git clone https://github.com/AcademySoftwareFoundation/OpenCue.git
cd OpenCue/cueweb

# Install dependencies
npm install

# Create development environment file
cp .env.example .env
```

### Development Configuration

Configure your `.env` file for development:

```bash
# .env file for development
NEXT_PUBLIC_OPENCUE_ENDPOINT=http://localhost:8448
NEXT_PUBLIC_URL=http://localhost:3000
NEXT_JWT_SECRET=dev-secret-key

# Development settings
NODE_ENV=development
NEXT_TELEMETRY_DISABLED=1

# Authentication (optional for development)
# NEXT_PUBLIC_AUTH_PROVIDER=github,google
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=dev-nextauth-secret

# Sentry (disabled for development)
# SENTRY_DSN=your-sentry-dsn
SENTRY_ENVIRONMENT=development
```

### Start Development Server

```bash
# Start the development server
npm run dev

# Server will start at http://localhost:3000
# Hot reload enabled for development
```

---

## Project Structure

### Directory Layout

```
cueweb/
├── app/                  # Next.js App Router pages
│   ├── globals.css       # Global styles and theme CSS variables
│   ├── layout.tsx        # Root layout - mounts ThemeProvider,
│   │                     #   AppSessionProvider, AppHeader,
│   │                     #   ReadOnlyBanner, AppSidebar,
│   │                     #   AttributesPanel, StatusBar, and
│   │                     #   JobSubscriptionPoller around {children}
│   ├── page.tsx          # Jobs dashboard (Cuetopia → Monitor Jobs)
│   ├── icon.png          # Favicon (OpenCue logo, theme-agnostic)
│   ├── login/            # Authentication pages (chrome is hidden here)
│   ├── providers/        # Client-side providers
│   │   ├── session-provider.tsx       # Wraps NextAuth's SessionProvider
│   │   └── job-subscription-poller.tsx # Polls subscribed jobs
│   ├── utils/            # Client-side hooks and shared data
│   │   ├── menus.ts                       # Shared NAV_MENUS (Cuetopia/CueCommander)
│   │   ├── help_menu.ts                   # Help links + env-var overrides
│   │   ├── use_disable_job_interaction.ts # Safety flag hook
│   │   ├── use_cuebot_facility.ts         # Active facility hook
│   │   ├── use_attributes_panel.ts        # Panel open/closed + dock position
│   │   ├── use_attribute_selection.ts     # Selected entity for the panel
│   │   ├── use_menu_registry.ts           # Flat command registry for Help search
│   │   ├── use_shortcut_notifications.ts  # Toast-on-shortcut opt-out pref
│   │   ├── layer_progress_utils.ts        # Layer progress segments (mirrors jobs)
│   │   └── job_progress_utils.ts          # Job progress segments + tooltip rows
│   └── api/              # API routes (REST gateway proxy + auth)
│       └── health/       # Gateway reachability probe used by StatusBar
├── components/           # Reusable React components
│   ├── ui/               # Base UI components
│   │   ├── app-header.tsx       # Global persistent header (incl. mobile hamburger)
│   │   ├── app-sidebar.tsx      # Collapsible left sidebar (desktop)
│   │   ├── mobile-nav-sheet.tsx # Mobile drawer mirroring every sidebar group
│   │   ├── sheet.tsx            # Side-slide panel primitive (Radix Dialog-based)
│   │   ├── row-actions-cell.tsx # Per-row "⋮" Actions button (touch equivalent of right-click)
│   │   ├── attributes-panel.tsx # Docked Attributes drawer
│   │   ├── breadcrumbs.tsx      # Detail-view breadcrumb primitive
│   │   ├── read-only-banner.tsx # Amber strip when safety flag is on
│   │   ├── status-bar.tsx       # IDE-style fixed bottom status bar
│   │   ├── shortcuts-overlay.tsx # `?` overlay + global key handler + clickable kbd chips
│   │   ├── job-progress-bar.tsx # Stacked Jobs progress bar (tooltip + colors)
│   │   ├── layer-progress-bar.tsx # Stacked Layers progress bar (same renderer)
│   │   ├── job-details-inline.tsx # Inline Layers + Frames panel under the Jobs grid
│   │   ├── simple-data-table.tsx # Shared TanStack-table wrapper for Layers/Frames
│   │   ├── subscribe-bell.tsx   # Per-row bell in the Jobs Notify column
│   │   ├── cuewebicon.tsx       # OpenCue icon + "CueWeb" wordmark
│   │   ├── theme-toggle.tsx     # Light/dark toggle
│   │   ├── theme-provider.tsx   # next-themes wrapper
│   │   └── ...                  # button, dialog, dropdown-menu, etc.
│   └── context_menus/    # Right-click context menus (Job / Layer / Frame)
├── lib/                  # Utility libraries
│   ├── auth.ts           # NextAuth configuration (Okta/Google/GitHub/LDAP)
│   ├── utils.ts          # General utilities (incl. cn())
│   └── metrics-service.ts # Prometheus metrics
├── public/               # Static assets
│   ├── opencue-icon-black.png   # Header logo (light mode)
│   ├── opencue-icon-white.png   # Header logo (dark mode)
│   └── workers/                 # Web workers
├── __tests__/            # Unit and integration tests
├── jest.config.js        # Jest testing configuration
├── next.config.js        # Next.js configuration
├── tailwind.config.js    # Tailwind CSS configuration
├── tsconfig.json         # TypeScript configuration
└── package.json          # Dependencies and scripts
```

The OpenCue brand assets that drive the icon/wordmark live at the repo
root in `images/` (icon, horizontal, stacked × PNG + SVG × black + white)
so other OpenCue projects can re-use them. The two PNGs CueWeb actually
loads at runtime are copies under `cueweb/public/`.

### Key Components

#### Core Components

- **`AppHeader`** (`components/ui/app-header.tsx`): Persistent global header mounted by `app/layout.tsx`. Hidden on `/login*`. Composes:
  - The OpenCue logo (theme-aware via Tailwind `block dark:hidden` / `hidden dark:block`) + the **CueWeb** wordmark.
  - Six `DropdownMenu`s that mirror the CueGUI menu bar - **File** (Disable Job Interaction), **Cuebot Facility** (one item per facility), **Cuetopia**, **CueCommander** (both built from `NAV_MENUS` imported from `app/utils/menus.ts`), **Other** (Attributes toggle, Show Shortcuts launcher, Notify on Shortcut toggle), and a custom **Help** dropdown with a search input that searches the full `useMenuRegistry` list and renders matches as `Group > Label`.
  - The "Show Shortcuts" item dispatches a `cueweb:open-shortcuts` `CustomEvent` on `window` that `KeyboardShortcuts` (in `components/ui/shortcuts-overlay.tsx`) listens for; "Notify on Shortcut" reads/writes the `cueweb.shortcutNotifications` pref via `useShortcutNotifications()`.
  - The existing `ThemeToggle`.
  - An always-visible **Sign out** button. `handleSignOut` clears two `localStorage` keys (`tableData`, `tableDataUnfiltered`) and calls `signOut({ callbackUrl: "/login" })` regardless of session state. When a session exists the button is preceded by the session's name or email (truncated, hidden on mobile).
- **`AppSidebar`** (`components/ui/app-sidebar.tsx`): Persistent collapsible left sidebar mounted by `app/layout.tsx`. Hidden on `/login*` and on viewports smaller than the `md` breakpoint. Same six groups as the header, rendered as Radix `Collapsible` accordions when expanded and as an icon-only rail when collapsed. The group containing the active route auto-expands; overall state is persisted under `cueweb.sidebar.collapsed`, and per-group open/closed state under `cueweb.sidebar.openGroups`.
- **`AttributesPanel`** (`components/ui/attributes-panel.tsx`): Docked drawer toggled from Other ▸ Attributes. Renders a collapsible key/value tree of the entity in `useAttributeSelection`. Dock position (right / bottom / left / top), open state, and the filter query are all driven by `useAttributesPanel`.
- **`ReadOnlyBanner`** (`components/ui/read-only-banner.tsx`): Amber strip rendered just under the header when `useDisableJobInteraction().disabled` is true. Includes a *Re-enable* button so users can clear the safety flag without opening the menu.
- **`Breadcrumbs`** (`components/ui/breadcrumbs.tsx`): Reusable `<Breadcrumbs items={...} showHome />` primitive used on detail views. Accepts `Array<{ label, href?, title? }>`; non-last items with an `href` render as `next/link`s, the last item gets `aria-current="page"`, and every label is wrapped in a Radix Tooltip with `max-w-[40ch] truncate` so over-long names collapse with an ellipsis but remain recoverable on hover. Currently consumed by the frame log page (`app/frames/[frame-name]/page.tsx`) and the per-job comments page (`app/jobs/[job-name]/comments/page.tsx`).
- **`StatusBar`** (`components/ui/status-bar.tsx`): IDE-style fixed 24px bar at the bottom of every authenticated route. Polls `/api/health` every 10s, listens to the `cueweb:jobs-refreshed` CustomEvent for "last refresh", and reads `NEXT_PUBLIC_APP_VERSION` for the build version. Turns red when the gateway is unreachable. Hidden on `/login*`.
  - The companion route `app/api/health/route.ts` is a cheap JWT-signed reachability probe of the REST gateway (POST `show.ShowInterface/GetActiveShows` with a 5s `AbortController` timeout). It returns 200 in both healthy and unhealthy cases so the UI never sees an error response while polling.
  - The jobs data table dispatches `window.dispatchEvent(new CustomEvent("cueweb:jobs-refreshed", { detail: { at: ISO } }))` after each 5s reload tick; the status bar listens and updates the "last refresh" timer.
- **`AppSessionProvider`** (`app/providers/session-provider.tsx`): Thin client wrapper around `next-auth/react`'s `SessionProvider` so `useSession()` works inside the header and any other client component.
- **`CueWebIcon`** (`components/ui/cuewebicon.tsx`): OpenCue icon + **CueWeb** wordmark, sized off a single `height` prop. Used by the login page, LDAP login page, frame log page, and comments page. Reads the brand assets from `cueweb/public/opencue-icon-{black,white}.png`.
- **`JobsTable`** (`app/jobs/data-table.tsx`): Main jobs dashboard table (no longer renders its own inline header - the global `AppHeader` owns that chrome). Each `TableRow` left-click dispatches `setAttributeSelection(...)` so the Attributes panel updates as the user inspects rows and also surfaces the inline Layers + Frames panel below the grid via `JobDetailsInline`. Destructive toolbar actions (Eat / Retry / Pause / Unpause / Kill) consume `useDisableJobInteraction()` and dim themselves when the safety flag is on. Wires TanStack's `columnVisibility`, `columnOrder`, and `globalFilter` state into the reducer State so each is persisted to `localStorage` (`columnVisibility`, `columnOrder`); the per-table substring filter is purely component-state.
- **`JobDetailsInline`** (`components/ui/job-details-inline.tsx`): Inline Layers + Frames panel rendered below the Jobs table when a row is selected. Polls layers and frames every 5s with cancellation guards. Layer-row clicks toggle a frames-table filter to that layer and push the layer's attributes into the docked Attributes panel.
- **`JobDetailsPage`** (`app/jobs/[job-name]/page.tsx`): Standalone tabbed job-details route reached via the **View Job Details** right-click entry (or the row's `⋮` Actions button). Resolves the job by name through `findJobByName(...)`, polls layers + frames every 5s with cancellation guards, and exposes five tabs - **Overview**, **Layers**, **Frames**, **Comments**, **Dependencies**. The active tab is mirrored to the URL as `?tab=<key>` and read back through `useSearchParams()` + `router.replace(...)` so the page is bookmarkable and browser back/forward walks between tabs. `isTabKey(value)` rejects unknown query values so the URL can never select a missing tab. The Comments tab embeds a read-only preview of `getJobComments(...)` with a link out to the full `/jobs/<jobName>/comments` editor; Dependencies is currently a placeholder. The standard `Breadcrumbs` + `EmptyState` (`FileX` icon, "Job not found") wrappers cover loading and missing-job paths.
- **`SimpleDataTable`** (`components/ui/simple-data-table.tsx`): Shared TanStack-table wrapper used by Layers and Frames (and the standalone log-viewer / per-job detail page). Owns the per-table substring filter (`globalFilter` + `getFilteredRowModel`), column-visibility persistence (`columnVisibilityStorageKey`), and column-order persistence (a parallel `cueweb.<table>.columnOrder` key derived from the visibility key). Renders the Columns dropdown that holds the `←` / `→` reorder buttons and the **Reset to Default** action.
- **`JobProgressBar` / `LayerProgressBar`** (`components/ui/{job,layer}-progress-bar.tsx`): Stacked progress bars with a hover tooltip showing per-state counts and percentages. Both delegate to the shared `<ProgressBar/>` renderer in `components/ui/progressbar.tsx`. Segment colors and ordering come from `app/utils/{job,layer}_progress_utils.ts`.
- **`KeyboardShortcuts`** (`components/ui/shortcuts-overlay.tsx`): Global keyboard handler + cheat-sheet `Dialog` mounted once from `app/layout.tsx`. Exports `CUEWEB_REFRESH_NOW_EVENT`, `CUEWEB_FOCUS_SEARCH_EVENT`, and `CUEWEB_OPEN_SHORTCUTS_EVENT` so menu items / pages can subscribe without prop drilling. Fires a `toastSuccess(...)` on every triggered shortcut when `getShortcutNotificationsEnabled()` returns true (read imperatively so the latest pref applies on the next keypress).
- **`FrameViewer`**: Frame log viewer component
- **`SearchBar`**: Job search and filtering
- **`ThemeProvider`**: Dark/light theme management
- **`JobSubscriptionPoller`** (`app/providers/job-subscription-poller.tsx`): App-wide client provider (mounted in `app/layout.tsx`) that polls subscribed jobs every 15s. When a job reaches `FINISHED`, `fireCompletionNotice(entry)` runs inside a `navigator.locks.request("cueweb:notify-<jobId>", ...)` block: it fires an in-app `toastSuccess(...)` (always) and a desktop `new Notification(...)` popup (when `Notification.permission === "granted"` at fire-time). The lock serializes the re-read + fire + mark sequence across same-origin tabs so only one tab toasts when several poll the same job. An `inFlight` ref guards against overlapping ticks, and jobs that no longer exist in Cuebot are removed from the store on the next poll.

#### UI Components

- **`DataTable`**: Reusable table component with sorting/filtering
- **`Button`**: Standardized button component
- **`Dialog`**: Modal dialog wrapper
- **`Select`**: Dropdown selection component
- **`Toast`**: Notification system
- **`SubscribeBell`** (`components/ui/subscribe-bell.tsx`): Per-row bell button in the `JobsTable` **Notify** column. Reads/writes per-job subscription state via the `useJobSubscriptions` hook (`app/utils/use_job_subscriptions.ts`), backed by `localStorage` through `app/utils/subscription_utils.ts`. The bell always subscribes immediately; the OS-level permission is requested afterwards via an inlined `requestNotificationPermission()` helper that returns `"granted" | "denied" | "default" | "unsupported"`. The toast wording branches on the outcome: `granted` (in-app toast + desktop popup will fire on completion), `denied` (in-app only, instruction to enable in browser settings), `default` (in-app only, user dismissed the prompt). The button is disabled on rows whose `jobState` is already `FINISHED` and the row has no existing subscription.

##### Subscription store

Subscriptions are stored as a `Record<jobId, JobSubscription>` under the `localStorage` key `cueweb:job-subscriptions`. Each entry tracks `jobId`, `jobName`, `subscribedAt`, and `notifiedAt` (null until the poller fires the notification). Mutations dispatch a `cueweb:subscriptions-changed` window event so every `useJobSubscriptions` consumer re-reads from `localStorage` &mdash; this keeps the bell, the poller, and any other consumer in sync within the same tab without prop drilling. The store getter defensively returns `{}` for missing or malformed JSON so a stale or hand-edited entry cannot crash the UI.

#### Application state hooks

CueWeb keeps global UI state (which menus you toggled, which facility you
picked, where you docked the Attributes panel) outside of React Context.
Each piece of state lives in its own `localStorage` key with a module-level
helper that broadcasts changes via a `CustomEvent` (same tab) and the
browser's built-in `storage` event (cross-tab). Every consumer reads via a
small `use*` hook that subscribes to those events - no prop drilling, no
provider tree.

- **`useDisableJobInteraction`** (`app/utils/use_disable_job_interaction.ts`)
  &mdash; `{ disabled, setDisabled, toggle }`.
  - Key: `cueweb.safety.disable-job-interaction`. Event: `cueweb:disable-job-interaction-changed`.
  - Drives the read-only banner and every destructive button/menu item.
- **`useCuebotFacility`** (`app/utils/use_cuebot_facility.ts`)
  &mdash; `{ facility, facilities, setFacility }`.
  - Key: `cueweb.facility.selected`. Event: `cueweb:facility-changed`.
  - Available facilities are read from `NEXT_PUBLIC_CUEBOT_FACILITIES`
    (comma-separated); defaults to `local,dev,cloud,external`.
- **`useAttributesPanel`** (`app/utils/use_attributes_panel.ts`)
  &mdash; `{ isOpen, position, positions, setOpen, toggle, setPosition }`.
  - Keys: `cueweb.attributes.open` (`bool`) and `cueweb.attributes.position`
    (`right`|`bottom`|`left`|`top`).
  - Event: `cueweb:attributes-panel-changed`.
- **`useAttributeSelection`** (`app/utils/use_attribute_selection.ts`)
  &mdash; `{ selection, setSelection, clearSelection }`.
  - Transient (not persisted); the standalone `setAttributeSelection()`
    helper is callable from any non-hook code (e.g. table row handlers).
  - Event: `cueweb:attribute-selection-changed`.
- **`useMenuRegistry`** (`app/utils/use_menu_registry.ts`)
  &mdash; returns a flat `MenuCommand[]` aggregated from every menu in the
  app, plus a `filterMenuCommands(commands, query)` helper used by the
  Help search box.
- **`useShortcutNotifications`** (`app/utils/use_shortcut_notifications.ts`)
  &mdash; `{ enabled, setEnabled, toggle }`. Controls whether triggered
  keyboard shortcuts also fire a toast.
  - Key: `cueweb.shortcutNotifications` (`bool`, defaults to `true`).
  - Event: `cueweb:shortcut-notifications-changed` (same-tab) plus the
    standard `storage` event for cross-tab sync.
  - Helper: `getShortcutNotificationsEnabled()` reads the pref
    imperatively at fire time, so flipping the toggle takes effect on
    the very next keypress without remounting the listener.

The header and sidebar share their NAV data via
`app/utils/menus.ts` (exports `NAV_MENUS`, `NavMenu`, `NavItem`). The Help
links and their env-var overrides live in `app/utils/help_menu.ts`.

### Cross-component window events

CueWeb keeps cross-component wiring decoupled by dispatching `CustomEvent`s
on `window` instead of prop-drilling shared state. Existing events:

| Event | Dispatched by | Listened to by | Purpose |
|-------|---------------|----------------|---------|
| `cueweb:focus-search` | `KeyboardShortcuts` (`/` keypress) | `JobsSearchbox` | Focus the jobs search input |
| `cueweb:refresh-now` | `KeyboardShortcuts` (`r` keypress) | Jobs `data-table` | Trigger an immediate refresh tick |
| `cueweb:open-shortcuts` | Header / Sidebar **Other ▸ Show Shortcuts** | `KeyboardShortcuts` | Open the cheat-sheet overlay |
| `cueweb:jobs-refreshed` | Jobs `data-table` (every 5s + on manual refresh) | `StatusBar` | Update the "Last refresh" relative timer |
| `cueweb:subscriptions-changed` | `subscription_utils.ts` mutations | `useJobSubscriptions`, `JobSubscriptionPoller` | Same-tab sync of the subscription store |
| `cueweb:shortcut-notifications-changed` | `useShortcutNotifications().setEnabled` | `useShortcutNotifications` listeners | Same-tab sync of the toast-on-shortcut pref |
| `cueweb:user-colors` | `UserColorSwatch` writes (in `app/jobs/columns.tsx`) | `UserColorSwatch` instances | Same-tab sync of the per-job color map |
| `cueweb:attributes-panel-changed` | `useAttributesPanel().setOpen / setPosition` | `useAttributesPanel` listeners | Same-tab sync of the panel state |
| `cueweb:attribute-selection-changed` | `setAttributeSelection()` | `useAttributeSelection` listeners | Same-tab sync of the selected entity |
| `cueweb:disable-job-interaction-changed` | `useDisableJobInteraction().toggle` | `useDisableJobInteraction` listeners | Same-tab sync of the safety flag |
| `cueweb:open-mobile-nav` | `AppHeader` hamburger button (`md:hidden`) | `MobileNavSheet` | Open the mobile nav drawer |

The browser's built-in `storage` event handles cross-tab sync for every
pref that lives in `localStorage`, so the `CustomEvent`s only need to
cover the same-tab case.

### Table `meta` extensions

TanStack tables thread shared callbacks to cell renderers via `useReactTable({ meta })`. CueWeb attaches the following keys:

| Key | Type | Producer | Consumer | Purpose |
|-----|------|----------|----------|---------|
| `openContextMenu` | `(event, row) => void` | Jobs `data-table.tsx` and `simple-data-table.tsx` (each forwards its own `contextMenuHandleOpen` from `useContextMenu`) | `RowActionsCell` in the leftmost column of Jobs / Layers / Frames | Lets the per-row `⋮` button surface the same context menu the row-level right-click opens, so touch users can reach every action without a `contextmenu` event. |

`meta.openContextMenu` is the wiring that makes the per-row Actions button (`row-actions-cell.tsx`) interchangeable with right-click: the button looks up the callback from `table.options.meta` and invokes it with the click event + row.  The signature stays identical to `useContextMenu`'s `contextMenuHandleOpen`, so callers just thread the existing handler through.

---

## Architecture Overview

### Technology Stack

- **Framework**: Next.js 14 (React 18)
- **Styling**: Tailwind CSS + Radix UI
- **State Management**: React hooks + Context
- **Authentication**: NextAuth.js
- **API Client**: Custom fetch wrapper
- **Type Safety**: TypeScript
- **Testing**: Jest + React Testing Library
- **Bundling**: Next.js built-in (Webpack)

### Data Flow

<div class="mermaid">
graph TD
    A[User Interaction] --> B[React Component]
    B --> C[API Client]
    C --> D[REST Gateway]
    D --> E[OpenCue Cuebot]
    E --> D
    D --> C
    C --> F[State Update]
    F --> G[UI Re-render]
</div>

### Authentication Flow

<div class="mermaid">
sequenceDiagram
    participant User
    participant CueWeb
    participant NextAuth
    participant OAuth
    participant API

    User->>CueWeb: Access protected page
    CueWeb->>NextAuth: Check auth status
    NextAuth->>OAuth: Redirect for login
    OAuth->>NextAuth: Return auth token
    NextAuth->>CueWeb: Set session
    CueWeb->>API: Generate JWT token
    API->>CueWeb: Return API access token
    CueWeb->>User: Show authenticated UI
</div>

---

## RBAC and Admin UI

CueWeb ships a Role-Based Access Control layer that activates whenever `NEXT_PUBLIC_AUTH_PROVIDER` is non-empty. The implementation spans the SQLite policy store, NextAuth callbacks, an instrumentation hook, edge middleware, server-only helpers, and React hooks.

### File layout

```
cueweb/
├── instrumentation.ts                # Next.js server-startup hook (edge-safe)
├── instrumentation.node.ts           # Node-only side: kicks off ensureBootstrapAdmin
├── middleware.ts                     # Edge gate for /admin/* and /api/admin/*
├── types/next-auth.d.ts              # Session + JWT type augmentation
├── lib/auth.ts                       # NextAuth providers + jwt/session callbacks
├── lib/rbac/
│   ├── config.ts                     # authEnabled() / hasProvider() helpers
│   ├── permissions.ts                # PERMISSIONS catalog + hasPermission()
│   ├── roles.ts                      # BUILTIN_ROLE_SEEDS
│   ├── seed.ts                       # Re-seeds built-in role permissions on every start
│   ├── bootstrap.ts                  # ensureBootstrapAdmin + verifyLocalLogin
│   ├── local_provider.ts             # NextAuth Credentials provider for "local"
│   ├── identity.ts                   # upsertProviderIdentity for Google/GitHub
│   ├── rate_limit.ts                 # In-memory sliding-window limiter for /login/local
│   ├── require_feature.ts            # requireFeature(name) / requireAdmin() route helpers
│   ├── db/
│   │   ├── index.ts                  # getDb() factory (better-sqlite3, WAL, FK on)
│   │   ├── types.ts                  # UserRow / GroupRow / RoleRow / AuditLogRow
│   │   ├── migrations.ts             # Forward-only migration runner
│   │   ├── migrations_data.ts        # Migrations inlined as TS constants (so webpack bundles them)
│   │   ├── migrations/0001_initial.sql # Reference copy of the same SQL
│   │   └── dal.ts                    # Prepared statements for every table
│   └── resolvers/
│       ├── types.ts                  # GroupsResolver + ResolvedIdentity
│       ├── index.ts                  # activeResolver() + resolveAndPersist()
│       ├── okta.ts                   # Reads `groups` claim from Okta ID token
│       ├── ldap.ts                   # Looks up memberOf via ldapjs
│       └── none.ts                   # Open-source default (no sync)
├── components/rbac/
│   ├── index.ts                      # Barrel export
│   ├── use_roles.ts                  # useRoles / usePermissions / useFeature / useIsAdmin
│   └── require_feature.tsx           # <RequireFeature> / <RequireAdmin>
└── app/
    ├── login/page.tsx                # Provider buttons + local form + theme toggle
    ├── login/change-password/page.tsx# must_change_password forced rotation page
    ├── admin/                        # Server-rendered shell + 6 tabs
    │   ├── layout.tsx                # Tabs + breadcrumbs
    │   ├── tabs.tsx                  # Tab bar (client)
    │   ├── page.tsx                  # Overview stats
    │   ├── users/page.tsx
    │   ├── groups/page.tsx
    │   ├── roles/page.tsx
    │   ├── permissions/page.tsx
    │   ├── admins/page.tsx
    │   └── audit/page.tsx
    └── api/
        ├── me/password/route.ts      # Self-service password change
        └── admin/                    # CRUD endpoints; each writes an audit_log row
            ├── users/{,[id]/{,password,roles}}/route.ts
            ├── groups/{,[id]/{,roles}}/route.ts
            ├── roles/{,[id]}/route.ts
            ├── permissions/route.ts
            ├── admins/{,[userId]}/route.ts
            └── audit/route.ts
```

### Bootstrap admin flow

`ensureBootstrapAdmin()` (in `lib/rbac/bootstrap.ts`) is idempotent: if the `admins` table is empty, it inserts `users("admin", source=local)` with `must_change_password=1`, attaches the `site-admin` role, generates a 24-char `crypto.randomBytes(...)` password, hashes it with `argon2id`, writes the credentials to `/data/.cueweb-bootstrap` (mode `0600`), and prints a one-time banner to stdout. The trigger is `instrumentation.node.ts`, which is loaded by `instrumentation.ts` only when `process.env.NEXT_RUNTIME === "nodejs"` (the edge runtime cannot link to native modules).

`/api/me/password` accepts `{ currentPassword, newPassword }` and rotates the password via `setUserPassword(userId, newHash, mustChangePassword=false)`. The change-password page redirects to `/` on success. The endpoint sits under `/api/me/*`, not `/api/admin/*`, so the admin-only middleware doesn't block normal users from changing their own credentials.

### NextAuth jwt / session callbacks

`callbacks.jwt`:

1. On sign-in (`trigger === "signIn"`):
   - **Local** provider returns the user row via `local_provider.ts`'s `authorize()`. The jwt callback reads `user.cueweb.{source,externalId,mustChangePassword}` from the returned object.
   - **Okta** or LDAP (`credentials`) provider triggers `resolveAndPersist(...)`, which calls the active groups resolver (`CUEWEB_GROUPS_RESOLVER`), upserts the user, and syncs `user_groups` for the matching `source`.
   - **Google** or **GitHub** trigger `upsertProviderIdentity(...)`, which writes the user with `source="imported"`. No groups are synced; admins assign roles in the Users tab.
2. On every later call, if `cuewebRefreshedAt` is older than 60s, the callback re-reads `listEffectiveRolesForUser`, `listEffectivePermissionsForUser`, `isAdmin`, and `must_change_password` from the DB so changes from the Admin UI propagate without a re-login.

`callbacks.session` mirrors the JWT fields onto `session.user.{groups,roles,permissions,isAdmin,mustChangePassword,source}` so client components can read them via `useSession()`.

### Enforcement layers

| Layer | File | Responsibility |
|-------|------|----------------|
| Edge | `middleware.ts` | Coarse gate: redirect to `/login` if unauthenticated on `/admin/*`, return 401 on `/api/admin/*`; require `cuewebIsAdmin` on both paths; short-circuit to `NextResponse.next()` when `NEXT_PUBLIC_AUTH_PROVIDER` is empty. |
| Route handler | `lib/rbac/require_feature.ts` | `requireFeature(name)` looks up effective permissions for the session and returns a 403 NextResponse if missing. `requireAdmin()` additionally checks `admins`. Both short-circuit to `ok: true, permissions: ["*"]` when auth is disabled. |
| Client | `components/rbac/{use_roles,require_feature}` | Hooks read from `useSession()` and `<RequireFeature name="...">` renders `null` when the feature isn't held (matches CueGUI's "hide, don't disable" pattern). `useFeature` returns `true` and `useIsAdmin` returns `false` in sandbox mode. |

### Adding a new permission

1. Add the constant to `lib/rbac/permissions.ts` (both the `PERMISSIONS` map and the `PERMISSION_CATALOG` array - the catalog shows up in the Admin UI's Permissions tab).
2. Add it to the appropriate built-in role in `lib/rbac/roles.ts` if you want it granted out-of-the-box. The next server start re-seeds the role's permissions automatically.
3. Gate the UI with `<RequireFeature name="your.permission">` or `useFeature("your.permission")`.
4. Gate the route handler with `requireFeature("your.permission")` at the top of the function.

### Adding a new groups resolver

1. Create `lib/rbac/resolvers/<provider>.ts` implementing `GroupsResolver` with an async `resolve({profile, account, user, token})` that returns a `ResolvedIdentity` or `null`. Filter on `account.provider` to ignore sign-ins from other providers.
2. Register it in `lib/rbac/resolvers/index.ts`'s `RESOLVERS` map and add the env-var value to the `CUEWEB_GROUPS_RESOLVER` switch.
3. Update the Reference doc's "RBAC Variables" table.

### SQLite specifics

- `better-sqlite3` is the synchronous SQLite binding; the DAL is a thin layer of prepared statements. Migrations run inside `db.transaction(...)` so partial failures roll back.
- Native modules are listed in `next.config.js#serverExternalPackages` so webpack doesn't try to bundle them.
- The Dockerfile installs Python + g++ as a virtual `.build-deps` group during `npm ci` and removes them immediately after, so the runtime image stays slim.
- The `/data` volume is declared in the Dockerfile and mounted by `docker-compose.yml` as `cueweb-data:/data`.

---

## Development Workflow

### Running in Development Mode

```bash
# Start development server with hot reload
npm run dev

# Run with specific port
npm run dev -- -p 3001

# Run with debug mode
DEBUG=* npm run dev
```

### Code Quality Tools

```bash
# Run ESLint
npm run lint

# Fix linting issues automatically
npm run lint -- --fix

# Format code with Prettier
npm run format:fix

# Check formatting
npm run format:check
```

### Testing

```bash
# Run all tests
npm test

# Run tests in watch mode
npm run test:watch

# Run tests with coverage
npm run coverage

# Run specific test file
npm test -- JobsTable.test.tsx
```

### Building for Production

```bash
# Build production bundle
npm run build

# Start production server
npm run start

# Analyze bundle size
npm run build -- --analyze
```

---

## API Integration

### OpenCue REST Gateway

CueWeb communicates with OpenCue through the REST Gateway using JWT authentication.

#### API Client Setup

```typescript
// lib/api.ts
import { createJWTToken } from './auth';

class OpenCueAPI {
  private baseUrl: string;
  private jwtSecret: string;

  constructor() {
    this.baseUrl = process.env.NEXT_PUBLIC_OPENCUE_ENDPOINT!;
    this.jwtSecret = process.env.NEXT_JWT_SECRET!;
  }

  private async getAuthHeaders() {
    const token = createJWTToken(this.jwtSecret, 'cueweb-user');
    return {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    };
  }

  async fetchShows() {
    const headers = await this.getAuthHeaders();
    const response = await fetch(
      `${this.baseUrl}/show.ShowInterface/GetShows`,
      {
        method: 'POST',
        headers,
        body: JSON.stringify({}),
      }
    );
    return response.json();
  }
}
```

#### JWT Token Generation

```typescript
// lib/auth.ts
import jwt from 'jsonwebtoken';

export function createJWTToken(secret: string, userId: string): string {
  const payload = {
    sub: userId,
    exp: Math.floor(Date.now() / 1000) + (60 * 60), // 1 hour
  };

  return jwt.sign(payload, secret, { algorithm: 'HS256' });
}
```

### Job Comments

CueWeb implements the CueGUI Comments dialog (`cuegui/cuegui/Comments.py`) via four proxy routes that wrap the underlying gRPC services.

#### Proxy routes

| Browser route | Forwards to | Notes |
|---------------|-------------|-------|
| `POST /api/job/getcomments` | `job.JobInterface/GetComments` | Returns the `Comment` array flattened from `data.comments.comments`. |
| `POST /api/job/action/addcomment` | `job.JobInterface/AddComment` | Body: `{ job: { id, name }, new_comment: { user, subject, message } }`. |
| `POST /api/comment/action/save` | `comment.CommentInterface/Save` | Body: `{ comment: Comment }`. `comment.id` is required. |
| `POST /api/comment/action/delete` | `comment.CommentInterface/Delete` | Body: `{ comment: Comment }`. Only `comment.id` is read. |

#### Helpers

Located in `app/utils/` and consumed by the Comments page (`app/jobs/[job-name]/comments/page.tsx`):

```typescript
// app/utils/get_utils.ts
export type JobComment = {
  id: string;
  timestamp: number;  // unix seconds - mirrors comment.Comment in proto/src/comment.proto
  user: string;
  subject: string;
  message: string;
};
export async function getJobComments(job: Job): Promise<JobComment[]>;

// app/utils/action_utils.ts
export async function addJobComment(job: Job, username: string, subject: string, message: string): Promise<void>;
export async function saveJobComment(comment: JobComment): Promise<void>;
export async function deleteJobComment(comment: JobComment): Promise<void>;
```

#### Predefined comment macros

Macros are stored per-browser in `localStorage` under the `cueweb-comment-macros` key. Loading, upserting (with optional rename), and deleting are exposed by `app/utils/comment_macros.ts`:

```typescript
export type CommentMacro = { name: string; subject: string; message: string };
export function loadCommentMacros(): CommentMacro[];
export function upsertCommentMacro(macro: CommentMacro, replaceName?: string): CommentMacro[];
export function deleteCommentMacro(name: string): CommentMacro[];
```

#### Markdown rendering

Comment messages are rendered with [`react-markdown`](https://github.com/remarkjs/react-markdown) and sanitized with [`rehype-sanitize`](https://github.com/rehypejs/rehype-sanitize) - embedded HTML/scripts are stripped before render.

#### Viewer identity and authorization

The Comments page derives the signed-in user from the authenticated NextAuth session by fetching `/api/auth/session` on mount, applying the same `email → name` precedence used in `app/page.tsx`. URL query parameters are **never** used as an authorization signal.

The session-derived `currentUser` only drives client-side UI state:

- `isAuthor = comment.user === currentUser` enables/disables the editor and Delete button.
- `addJobComment(..., currentUser, ...)` stamps new-comment author from the session, not the URL.

**Authoritative ownership enforcement lives server-side in Cuebot.** The client-side gate is a convenience to avoid a doomed round-trip; Cuebot still rejects unauthorized save/delete attempts.

#### Comment indicator on the jobs table

The Job columns definition (`app/jobs/columns.tsx`) declares a dedicated **`comments`** column immediately after `name`. It is rendered as a sortable, icon-only column (lucide-react `StickyNote` + `ArrowUpDown` in the header, with `<span className="sr-only">Comments</span>` for screen readers) so jobs with comments can be pulled to the top in one click - mirroring CueGUI's Monitor Jobs column for comment presence.

The cell opens the Comments page with `?jobId=<id>` only - no user identifier is forwarded in the URL. Identity is resolved on the Comments page itself from the authenticated NextAuth session (`/api/auth/session`), and only Cuebot's server-side ownership check authorizes save/delete. Keeping PII out of the query string also avoids leakage into browser history, server logs, and shared links.

Both the indicator click and the context-menu "Comments" entry open the page with `window.open(url, "_blank", "noopener,noreferrer")` so the new tab cannot reach back via `window.opener` and the `Referer` header is suppressed.

### Data Fetching Patterns

#### Server-Side Rendering (SSR)

```typescript
// app/page.tsx
import { getShows } from '@/lib/api';

export default async function HomePage() {
  const shows = await getShows();

  return (
    <div>
      <JobsTable initialShows={shows} />
    </div>
  );
}
```

#### Client-Side Fetching

```typescript
// components/JobsTable.tsx
import { useEffect, useState } from 'react';
import { useAPI } from '@/lib/hooks/useAPI';

export function JobsTable() {
  const { data: jobs, loading, error, refetch } = useAPI('/jobs');

  useEffect(() => {
    const interval = setInterval(refetch, 30000); // Auto-refresh
    return () => clearInterval(interval);
  }, [refetch]);

  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorMessage error={error} />;

  return <DataTable data={jobs} />;
}
```

#### Error Handling

```typescript
// lib/api.ts
export class APIError extends Error {
  constructor(
    public status: number,
    public message: string,
    public code?: string
  ) {
    super(message);
    this.name = 'APIError';
  }
}

async function handleResponse(response: Response) {
  if (!response.ok) {
    const error = await response.json();
    throw new APIError(
      response.status,
      error.message || 'API request failed',
      error.code
    );
  }
  return response.json();
}
```

---

## Component Development

### Creating New Components

#### Component Structure

```typescript
// components/JobCard.tsx
import React from 'react';
import { Job } from '@/lib/types';

interface JobCardProps {
  job: Job;
  onPause: (jobId: string) => void;
  onKill: (jobId: string) => void;
  className?: string;
}

export function JobCard({ job, onPause, onKill, className }: JobCardProps) {
  return (
    <div className={`job-card ${className}`}>
      <h3>{job.name}</h3>
      <p>Status: {job.status}</p>
      <div className="actions">
        <button onClick={() => onPause(job.id)}>
          {job.isPaused ? 'Resume' : 'Pause'}
        </button>
        <button onClick={() => onKill(job.id)}>Kill</button>
      </div>
    </div>
  );
}
```

#### Component Testing

```typescript
// __tests__/JobCard.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { JobCard } from '@/components/JobCard';

const mockJob = {
  id: 'job-1',
  name: 'Test Job',
  status: 'RUNNING',
  isPaused: false,
};

describe('JobCard', () => {
  it('renders job information', () => {
    render(
      <JobCard
        job={mockJob}
        onPause={jest.fn()}
        onKill={jest.fn()}
      />
    );

    expect(screen.getByText('Test Job')).toBeInTheDocument();
    expect(screen.getByText('Status: RUNNING')).toBeInTheDocument();
  });

  it('calls onPause when pause button clicked', () => {
    const onPause = jest.fn();
    render(
      <JobCard
        job={mockJob}
        onPause={onPause}
        onKill={jest.fn()}
      />
    );

    fireEvent.click(screen.getByText('Pause'));
    expect(onPause).toHaveBeenCalledWith('job-1');
  });
});
```

### State Management

#### React Context for Global State

```typescript
// lib/context/JobsContext.tsx
import React, { createContext, useContext, useReducer } from 'react';

interface JobsState {
  jobs: Job[];
  selectedJobs: string[];
  filters: JobFilters;
}

type JobsAction =
  | { type: 'SET_JOBS'; payload: Job[] }
  | { type: 'UPDATE_JOB'; payload: Job }
  | { type: 'SELECT_JOB'; payload: string }
  | { type: 'SET_FILTERS'; payload: JobFilters };

const JobsContext = createContext<{
  state: JobsState;
  dispatch: React.Dispatch<JobsAction>;
} | null>(null);

export function JobsProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(jobsReducer, initialState);

  return (
    <JobsContext.Provider value={{ state, dispatch }}>
      {children}
    </JobsContext.Provider>
  );
}

export function useJobs() {
  const context = useContext(JobsContext);
  if (!context) {
    throw new Error('useJobs must be used within JobsProvider');
  }
  return context;
}
```

#### Custom Hooks

```typescript
// lib/hooks/useJobActions.ts
import { useCallback } from 'react';
import { useAPI } from './useAPI';
import { useToast } from './useToast';

export function useJobActions() {
  const { toast } = useToast();

  const pauseJob = useCallback(async (jobId: string) => {
    try {
      await fetch('/api/jobs/pause', {
        method: 'POST',
        body: JSON.stringify({ jobId }),
      });
      toast.success('Job paused successfully');
    } catch (error) {
      toast.error('Failed to pause job');
    }
  }, [toast]);

  const killJob = useCallback(async (jobId: string) => {
    try {
      await fetch('/api/jobs/kill', {
        method: 'POST',
        body: JSON.stringify({ jobId }),
      });
      toast.success('Job killed successfully');
    } catch (error) {
      toast.error('Failed to kill job');
    }
  }, [toast]);

  return { pauseJob, killJob };
}
```

---

## Styling and Theming

### Tailwind CSS Configuration

```javascript
// tailwind.config.js
module.exports = {
  content: [
    './app/**/*.{js,ts,jsx,tsx}',
    './components/**/*.{js,ts,jsx,tsx}',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Custom color palette
        primary: {
          50: '#eff6ff',
          500: '#3b82f6',
          900: '#1e3a8a',
        },
        // Status colors
        success: '#10b981',
        warning: '#f59e0b',
        error: '#ef4444',
        // Job status colors
        running: '#10b981',
        paused: '#6b7280',
        failed: '#ef4444',
        pending: '#f59e0b',
      },
      animation: {
        'fade-in': 'fadeIn 0.2s ease-in-out',
        'slide-up': 'slideUp 0.3s ease-out',
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/typography'),
  ],
};
```

### Theme Implementation

```typescript
// components/ThemeProvider.tsx
import { createContext, useContext, useEffect, useState } from 'react';

type Theme = 'light' | 'dark' | 'system';

const ThemeContext = createContext<{
  theme: Theme;
  setTheme: (theme: Theme) => void;
} | null>(null);

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setTheme] = useState<Theme>('system');

  useEffect(() => {
    const root = window.document.documentElement;

    if (theme === 'dark' ||
        (theme === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
  }, [theme]);

  return (
    <ThemeContext.Provider value={{ theme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}
```

### Component Styling Patterns

```typescript
// components/ui/Button.tsx
import { cva, type VariantProps } from 'class-variance-authority';

const buttonVariants = cva(
  // Base styles
  'inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50',
  {
    variants: {
      variant: {
        default: 'bg-primary text-primary-foreground hover:bg-primary/90',
        destructive: 'bg-destructive text-destructive-foreground hover:bg-destructive/90',
        outline: 'border border-input bg-background hover:bg-accent hover:text-accent-foreground',
        ghost: 'hover:bg-accent hover:text-accent-foreground',
      },
      size: {
        default: 'h-10 px-4 py-2',
        sm: 'h-9 rounded-md px-3',
        lg: 'h-11 rounded-md px-8',
        icon: 'h-10 w-10',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  }
);

interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

export function Button({ className, variant, size, ...props }: ButtonProps) {
  return (
    <button
      className={buttonVariants({ variant, size, className })}
      {...props}
    />
  );
}
```

---

## Configuration and Deployment

### Environment Configuration

#### Development Environment

```bash
# .env.local (for local development overrides)
NEXT_PUBLIC_OPENCUE_ENDPOINT=http://localhost:8448
NEXT_PUBLIC_URL=http://localhost:3000
NEXT_JWT_SECRET=dev-secret-very-long-key

# Debug settings
DEBUG=cueweb:*
NODE_ENV=development
NEXT_TELEMETRY_DISABLED=1

# Development database (if using local DB)
DATABASE_URL=postgresql://user:pass@localhost:5432/opencue_dev
```

#### Production Environment

```bash
# .env.production
NEXT_PUBLIC_OPENCUE_ENDPOINT=https://api.renderfarm.company.com
NEXT_PUBLIC_URL=https://cueweb.company.com
NEXT_JWT_SECRET=production-secret-key-very-long-and-secure

# Production optimizations
NODE_ENV=production
NEXT_TELEMETRY_DISABLED=1

# Monitoring
SENTRY_DSN=https://your-sentry-dsn
SENTRY_ENVIRONMENT=production

# Authentication
NEXT_PUBLIC_AUTH_PROVIDER=okta,google
NEXTAUTH_URL=https://cueweb.company.com
NEXTAUTH_SECRET=nextauth-production-secret

# OAuth credentials (from secure storage)
OKTA_CLIENT_ID=${OKTA_CLIENT_ID}
OKTA_CLIENT_SECRET=${OKTA_CLIENT_SECRET}
OKTA_ISSUER=https://company.okta.com
```

### Docker Deployment

#### Dockerfile

```dockerfile
# cueweb/Dockerfile
FROM node:18-alpine AS base

# Install dependencies only when needed
FROM base AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --only=production

# Build the app
FROM base AS builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# Production image
FROM base AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["node", "server.js"]
```

#### Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  cueweb:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_OPENCUE_ENDPOINT=http://rest-gateway:8448
      - NEXT_PUBLIC_URL=http://localhost:3000
      - NEXT_JWT_SECRET=${JWT_SECRET}
      - NEXTAUTH_SECRET=${NEXTAUTH_SECRET}
    depends_on:
      - rest-gateway
    networks:
      - opencue

  rest-gateway:
    image: opencue-rest-gateway:latest
    ports:
      - "8448:8448"
    environment:
      - CUEBOT_ENDPOINT=cuebot:8443
      - JWT_SECRET=${JWT_SECRET}
      - REST_PORT=8448
    networks:
      - opencue

networks:
  opencue:
    external: true
```

### Kubernetes Deployment

```yaml
# k8s/cueweb-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cueweb
  labels:
    app: cueweb
spec:
  replicas: 3
  selector:
    matchLabels:
      app: cueweb
  template:
    metadata:
      labels:
        app: cueweb
    spec:
      containers:
      - name: cueweb
        image: cueweb:latest
        ports:
        - containerPort: 3000
        env:
        - name: NEXT_PUBLIC_OPENCUE_ENDPOINT
          value: "http://rest-gateway:8448"
        - name: NEXT_PUBLIC_URL
          value: "https://cueweb.company.com"
        - name: NEXT_JWT_SECRET
          valueFrom:
            secretKeyRef:
              name: cueweb-secrets
              key: jwt-secret
        - name: NEXTAUTH_SECRET
          valueFrom:
            secretKeyRef:
              name: cueweb-secrets
              key: nextauth-secret
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /api/health
            port: 3000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /api/health
            port: 3000
          initialDelaySeconds: 5
          periodSeconds: 5

---
apiVersion: v1
kind: Service
metadata:
  name: cueweb
spec:
  selector:
    app: cueweb
  ports:
  - port: 3000
    targetPort: 3000
  type: ClusterIP
```