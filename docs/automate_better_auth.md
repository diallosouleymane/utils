# Better Auth Automation for Next.js with Prisma (The Script) [../scripts/automate_better_auth.py]

## Purpose

This Python script automates the installation and configuration of **Better Auth** in a Next.js project using Prisma ORM with MySQL or PostgreSQL and Shadcn ui.

---

## Features

- Installs dependencies: `better-auth`, `prisma`, `@prisma/client`  
- Generates a `.env` file with a randomly generated secret and database URL  
- Creates a minimal Prisma schema with a `User` model  
- Runs Prisma client generation (`prisma generate`)  
- Creates an optimized Prisma singleton (`lib/prisma.ts`)  
- Creates the Better Auth instance (`lib/auth.ts`)  
- Sets up the Next.js API route for authentication (`app/api/auth/[...all]/route.ts`)  
- Runs Better Auth CLI generation (`@better-auth/cli generate`)  
- Runs Prisma migration (`prisma migrate dev`)

---

## Usage

```bash
python automate_better_auth.py PROJECT_PATH [--db mysql|postgresql] [--pm pnpm|npm|yarn]
