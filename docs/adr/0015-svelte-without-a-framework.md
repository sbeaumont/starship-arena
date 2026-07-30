# 0015. Svelte 5 and Vite, without SvelteKit

**Status:** Accepted

## Context

The game UI is one interactive view: a tactical map with dragging, plus a few reference pages. It
talks to a JSON API that already exists.

There's no server-side rendering to do, no routing beyond which view is open, and no SEO to care
about behind a password.

The author is learning JavaScript, and the map is heavily SVG.

## Decision

Svelte 5 with Vite. No SvelteKit, no router, no state library.

The build produces static files, committed to `game-ui/dist`.

## Consequences

Svelte's templates are SVG-native, so the map is written as markup rather than as imperative
drawing calls. That matters for a UI that is mostly SVG.

Minimal ceremony to read, which suits both learning and a small codebase. Runes (`$state`,
`$derived`) are the only framework concept in play.

No router means [view state lives in the URL](0016-the-view-lives-in-the-url.md) and is read
directly.

A production build is a manual step, and the output is committed because [the host has no
build](0007-one-wsgi-application.md).

Anything SvelteKit would have given (server routes, SSR, file-based routing) has to be done by
hand if it's ever wanted. None of it is wanted.

## Alternatives rejected

**SvelteKit.** Brings routing, SSR and a server runtime. The host runs no Node, so the server half
is dead weight, and the routing is one query parameter here.

**React or Vue.** More ceremony per component and less pleasant SVG. No advantage for a single
interactive view.

**No framework at all.** The drag-to-plan prototype was written in vanilla JS and worked. It didn't
survive contact with real state: selection, layers, orders per tick and live validation are what
components are for.
