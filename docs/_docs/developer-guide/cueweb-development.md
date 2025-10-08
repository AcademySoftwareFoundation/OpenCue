---
layout: default
title: CueWeb Development
parent: Developer Guide
nav_order: 84
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
│   ├── globals.css       # Global styles
│   ├── layout.tsx        # Root layout component
│   ├── page.tsx          # Home page
│   ├── login/            # Authentication pages
│   └── api/              # API routes
├── components/           # Reusable React components
│   ├── ui/               # Base UI components
│   ├── tables/           # Data table components
│   ├── dialogs/          # Modal dialogs
│   └── forms/            # Form components
├── lib/                  # Utility libraries
│   ├── auth.ts           # Authentication configuration
│   ├── api.ts            # API client functions
│   ├── utils.ts          # General utilities
│   └── types.ts          # TypeScript type definitions
├── public/               # Static assets
│   ├── icons/            # Application icons
│   └── images/           # Images and graphics
├── styles/               # Additional stylesheets
├── __tests__/            # Unit and integration tests
├── jest.config.js        # Jest testing configuration
├── next.config.js        # Next.js configuration
├── tailwind.config.js    # Tailwind CSS configuration
├── tsconfig.json         # TypeScript configuration
└── package.json          # Dependencies and scripts
```

### Key Components

#### Core Components

- **`JobsTable`**: Main jobs dashboard table
- **`JobDetails`**: Job detail panel with layers/frames
- **`FrameViewer`**: Frame log viewer component
- **`SearchBar`**: Job search and filtering
- **`ThemeProvider`**: Dark/light theme management

#### UI Components

- **`DataTable`**: Reusable table component with sorting/filtering
- **`Button`**: Standardized button component
- **`Dialog`**: Modal dialog wrapper
- **`Select`**: Dropdown selection component
- **`Toast`**: Notification system

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