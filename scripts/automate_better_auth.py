import subprocess
import os
import sys
import secrets

# Génère un secret aléatoire style AY7HaJcIp6l3WNg0rggTa9FOhHGATVQe
def generate_secret(length=32):
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def run_cmd(cmd, cwd=None):
    print(f"> {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd)
    if result.returncode != 0:
        print(f"Erreur lors de l'exécution de : {cmd}")
        sys.exit(1)

def creer_env(path, secret, db_url):
    contenu = f"""BETTER_AUTH_SECRET={secret}
DATABASE_URL="{db_url}"
BETTER_AUTH_URL=http://localhost:3000
"""
    with open(os.path.join(path, ".env"), "w") as f:
        f.write(contenu)
    print(".env créé")

def creer_prisma_schema(path, db_provider):
    contenu = f"""
generator client {{
  provider = "prisma-client-js"
}}

datasource db {{
  provider = "{db_provider}"
  url      = env("DATABASE_URL")
}}

model User {{
  id    String @id @default(cuid())
  email String @unique
}}
"""
    prisma_path = os.path.join(path, "prisma")
    os.makedirs(prisma_path, exist_ok=True)
    with open(os.path.join(prisma_path, "schema.prisma"), "w") as f:
        f.write(contenu.strip())
    print("Prisma schema créé avec un modèle User simple")

def creer_prisma_client_ts(path):
    contenu = """
import { PrismaClient } from "@prisma/client";

declare global {
  // Evite multiples instances de PrismaClient en dev (HMR)
  // eslint-disable-next-line no-var
  var prisma: PrismaClient | undefined;
}

export const prisma =
  global.prisma ??
  new PrismaClient({
    log: process.env.NODE_ENV === "development" ? ["query", "error", "warn"] : [],
  });

if (process.env.NODE_ENV !== "production") global.prisma = prisma;
"""
    lib_dir = os.path.join(path, "lib")
    os.makedirs(lib_dir, exist_ok=True)
    with open(os.path.join(lib_dir, "prisma.ts"), "w") as f:
        f.write(contenu.strip())
    print("lib/prisma.ts créé")


def creer_auth_ts(path, db_provider):
    contenu = """
import { betterAuth } from "better-auth";
import { prisma } from "@/lib/prisma";
import { prismaAdapter } from "better-auth/adapters/prisma";

export const auth = betterAuth({
  database: prismaAdapter(prisma, {
    provider: "%s",
  }),
  emailAndPassword: {
    enabled: true,
  },
  socialProviders: {
    github: {
      clientId: process.env.GITHUB_CLIENT_ID as string,
      clientSecret: process.env.GITHUB_CLIENT_SECRET as string,
    },
  },
});
""" % db_provider

    lib_dir = os.path.join(path, "lib")
    os.makedirs(lib_dir, exist_ok=True)
    with open(os.path.join(lib_dir, "auth.ts"), "w") as f:
        f.write(contenu.strip())
    print("auth.ts créé")

def creer_route_api(path):
    route_dir = os.path.join(path, "app", "api", "auth", "[...all]")
    os.makedirs(route_dir, exist_ok=True)
    contenu = """
import { auth } from "@/lib/auth";
import { toNextJsHandler } from "better-auth/next-js";

export const { POST, GET } = toNextJsHandler(auth);
"""
    with open(os.path.join(route_dir, "route.ts"), "w") as f:
        f.write(contenu.strip())
    print("route.ts API créé")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Automatise Better Auth config")
    parser.add_argument("path", help="Chemin du projet (répertoire de travail)")
    parser.add_argument("--db", choices=["mysql", "postgresql"], default="mysql", help="Choix de la base de données")
    parser.add_argument("--pm", choices=["pnpm", "npm", "yarn"], default="pnpm", help="Gestionnaire de paquets à utiliser")
    args = parser.parse_args()

    path = args.path
    db_provider = "mysql" if args.db == "mysql" else "postgresql"
    secret = generate_secret()
    pm = args.pm
    db_user = input("Entrez le nom d'utilisateur de la base de données: ") or "root"
    db_password = input("Entrez le mot de passe de la base de données: ") or ""
    db_name = input("Entrez le nom de la base de données: ") or "better_auth"
    db_host = input("Entrez l'hôte de la base de données: ") or "localhost"
    db_port = 3306 if db_provider == "mysql" else 5432

    # Construire DATABASE_URL basique selon le choix DB
    if db_provider == "mysql":
        # Exemple générique, à adapter par l'utilisateur
        db_url = f"mysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    else:
        db_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

    print(f"Travail dans: {path}")
    print(f"Base de données: {db_provider}")
    print(f"Gestionnaire de paquets: {pm}")
    print(f"Secret généré: {secret}")

    # 1) Installer better-auth
    run_cmd(f"{pm} install better-auth @prisma/client", cwd=path)
    run_cmd(f"{pm} install -D prisma", cwd=path)

    # 2) Créer .env
    creer_env(path, secret, db_url)

    # 3) Créer schema prisma avec User
    creer_prisma_schema(path, db_provider)

    # 4) Créer prisma client
    creer_prisma_client_ts(path)

    # 5) Générer prisma client
    run_cmd(f"{"pnpm dlx " if pm == "pnpm" else "npx "} prisma generate", cwd=path)

    # 6) Créer auth.ts
    creer_auth_ts(path, db_provider)

    # 7) Créer route.ts API
    creer_route_api(path)

    # 8) Générer fichiers better-auth (npx @better-auth/cli generate)
    run_cmd(f"{"pnpm dlx " if pm == "pnpm" else "npx "} @better-auth/cli generate", cwd=path)

    # 9) Lancer migration prisma
    run_cmd(f"{"pnpm dlx " if pm == "pnpm" else "npx "} prisma migrate dev --name init", cwd=path)

    print("=== Automatisation terminée ===")

if __name__ == "__main__":
    main()
