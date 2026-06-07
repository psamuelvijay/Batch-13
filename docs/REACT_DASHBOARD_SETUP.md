# 🖥️ React Dashboard Setup Guide

## Overview

The dashboard is a React SPA that polls the FastAPI backend every 2 seconds and displays:
- Real-time device tracking stats
- Violation counts per device
- Quarantine status and controls
- Merkle chain integrity verification
- Time-series violation chart

## Tech Stack

- React 19
- Recharts (line chart)
- Lucide React (icons)
- Axios (HTTP client)

## Installation

```bash
cd dashboard
npm install
npm start
```

Runs at http://localhost:3000

## Environment

The API URL is hardcoded in `src/Dashboard.js`:
```js
const API_URL = 'http://localhost:8000';
```

Change this if your backend runs on a different host or port.

## Available Scripts

| Command | Description |
|---------|-------------|
| `npm start` | Development server (hot reload) |
| `npm run build` | Production build to `build/` |
| `npm test` | Run tests |

## Dashboard Panels

### Metric Cards
- **Devices Tracked** — unique UIDs seen
- **Total Violations** — sum of all violations
- **Quarantined Devices** — actively blocked devices
- **Merkle Chain** — total signed entries

### Violation History Chart
- Updates every 2 seconds
- Shows total violations and quarantine count over time
- Keeps last 30 data points

### Cryptographic Verification Panel
- Displays current Merkle root hash
- "Verify Chain" button calls `/verify-logs`
- Shows HLF queue size

### Device Violation Table
- Sorted by violation count (highest first)
- Color-coded: blue (1), yellow (2), red (3+)
- Quarantined devices show "Release" button

## CORS

The FastAPI backend already allows `http://localhost:3000`. If you change the React port, update `allow_origins` in `backend/telemetry_api_v3.py`.

## Production Build

```bash
npm run build
```

Serve the `build/` folder with any static file server:
```bash
npx serve -s build
```
