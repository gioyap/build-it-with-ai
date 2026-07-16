# Build It With AI — Submission

This repository contains two projects built as part of the "Build It With AI" assessment.

## Repository Structure

```
/project-a-manual/        Manually built project
  /docs/                  Planning notes, architecture decisions
  /backend/
  /frontend/
  /tests/
/project-b-ai-assisted/   URL Shortener, built with AI coding tools
  /docs/                  Planning notes + AI usage log
  /prompts/               Every prompt used, with model name
  /backend/               FastAPI + Python + SQLite
  /frontend/              Next.js + React
  /tests/                 Backend tests
/resume.pdf
/README.md                This file
```

## Project A — Manual

_Overview to be added._

## Project B — AI-Assisted: URL Shortener

A small application that takes long URLs, generates short codes, redirects users,
and tracks how many times each short link has been clicked.

- **Backend:** FastAPI + Python, persisting to SQLite. Endpoints to create short
  URLs (API-key protected), publicly redirect short codes, and report click stats.
- **Frontend:** Next.js + React. A form to shorten URLs and a dashboard showing
  created URLs and their click counts.
- **AI usage:** Built with AI coding tools. The full session transcript and the
  prompts used live in `project-b-ai-assisted/prompts/`, with model choices
  documented in `project-b-ai-assisted/docs/`.

See each project's own `docs/` folder for the thinking behind the approach —
requirements understanding, alternatives considered, and tradeoffs.

## Approach Overview

_A short narrative on how both projects were approached will be added as the work
progresses._
