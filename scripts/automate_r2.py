#!/usr/bin/env python3
"""
scripts/automate_r2.py
Automate Cloudflare R2 (S3-compatible) scaffolding for a Next.js app.
Usage:
  python automate_r2.py /path/to/nextjs/project --mode presign --pm pnpm
Modes: presign, direct, both
Package manager default: pnpm (falls back to npm if pnpm not found)
"""

import argparse
import os
import subprocess
import sys
import shutil
import textwrap

# ------------ Helpers ------------
def run_cmd(cmd, cwd=None):
    print(f"> {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd)
    if result.returncode != 0:
        print(f"[ERROR] Command failed: {cmd}")
        sys.exit(1)

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

def write_file(path, content):
    ensure_dir(os.path.dirname(path))
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[OK] Wrote {path}")

# ------------ Templates ------------
ENV_TEMPLATE = """# Cloudflare R2 / S3 configuration
AWS_S3_BUCKET=
R2_URL= # public base URL e.g. https://<bucket>.<account_id>.r2.cloudflarestorage.com
AWS_REGION=auto
AWS_S3_ENDPOINT= # e.g. https://<account_id>.r2.cloudflarestorage.com
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
"""

LIB_S3_PRESIGN = textwrap.dedent("""\
  import { S3Client, PutObjectCommand } from "@aws-sdk/client-s3";
  import { getSignedUrl } from "@aws-sdk/s3-request-presigner";

  const bucket = process.env.AWS_S3_BUCKET as string;
  const publicBaseUrl = process.env.R2_URL;
  const region = process.env.AWS_REGION as string;

  export const s3 = new S3Client({
    region,
    endpoint: process.env.AWS_S3_ENDPOINT || undefined,
    credentials: process.env.AWS_ACCESS_KEY_ID
      ? {
          accessKeyId: process.env.AWS_ACCESS_KEY_ID as string,
          secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY as string,
        }
      : undefined,
  });

  export interface PresignParams {
    key: string;
    contentType: string;
    expiresIn?: number;
  }

  export async function createPresignedPutUrl({ key, contentType, expiresIn = 300 }: PresignParams) {
    const command = new PutObjectCommand({ Bucket: bucket, Key: key, ContentType: contentType });
    const url = await getSignedUrl(s3, command, { expiresIn });
    const publicUrl = `${publicBaseUrl}/${key}`;
    return { url, key, publicUrl };
  }
""")

LIB_S3_DIRECT = textwrap.dedent("""\
  import { S3Client, PutObjectCommand } from "@aws-sdk/client-s3";

  const bucket = process.env.AWS_S3_BUCKET as string;
  const publicBaseUrl = process.env.R2_URL;
  const region = process.env.AWS_REGION as string;

  export const s3 = new S3Client({
    region,
    endpoint: process.env.AWS_S3_ENDPOINT || undefined,
    credentials: process.env.AWS_ACCESS_KEY_ID
      ? {
          accessKeyId: process.env.AWS_ACCESS_KEY_ID as string,
          secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY as string,
        }
      : undefined,
  });

  export interface DirectUploadParams {
    key: string;
    contentType: string;
    body: Uint8Array | Buffer | string;
  }

  export async function uploadDirect({ key, contentType, body }: DirectUploadParams) {
    const command = new PutObjectCommand({
      Bucket: bucket,
      Key: key,
      ContentType: contentType,
      Body: body,
    });
    await s3.send(command);
    const publicUrl = `${publicBaseUrl}/${key}`;
    return { key, publicUrl };
  }
""")

LIB_S3_BOTH = textwrap.dedent("""\
  import { S3Client, PutObjectCommand } from "@aws-sdk/client-s3";
  import { getSignedUrl } from "@aws-sdk/s3-request-presigner";

  const bucket = process.env.AWS_S3_BUCKET as string;
  const publicBaseUrl = process.env.R2_URL;
  const region = process.env.AWS_REGION as string;

  export const s3 = new S3Client({
    region,
    endpoint: process.env.AWS_S3_ENDPOINT || undefined,
    credentials: process.env.AWS_ACCESS_KEY_ID
      ? {
          accessKeyId: process.env.AWS_ACCESS_KEY_ID as string,
          secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY as string,
        }
      : undefined,
  });

  export interface PresignParams {
    key: string;
    contentType: string;
    expiresIn?: number;
  }

  export async function createPresignedPutUrl({ key, contentType, expiresIn = 300 }: PresignParams) {
    const command = new PutObjectCommand({ Bucket: bucket, Key: key, ContentType: contentType });
    const url = await getSignedUrl(s3, command, { expiresIn });
    const publicUrl = `${publicBaseUrl}/${key}`;
    return { url, key, publicUrl };
  }

  export interface DirectUploadParams {
    key: string;
    contentType: string;
    body: Uint8Array | Buffer | string;
  }

  export async function uploadDirect({ key, contentType, body }: DirectUploadParams) {
    const command = new PutObjectCommand({
      Bucket: bucket,
      Key: key,
      ContentType: contentType,
      Body: body,
    });
    await s3.send(command);
    const publicUrl = `${publicBaseUrl}/${key}`;
    return { key, publicUrl };
  }
""")

# API route for presign mode (Next.js app router)
API_ROUTE_PRESIGN = textwrap.dedent("""\
  import { NextRequest, NextResponse } from "next/server";
  import * as z from "zod";
  import { createPresignedPutUrl } from "@/lib/s3";

  const schema = z.object({
    key: z.string().min(3),
    contentType: z.string().min(3),
    expiresIn: z.number().optional(),
  });

  export async function POST(req: NextRequest) {
    try {
      const body = await req.json();
      const { key, contentType, expiresIn } = schema.parse(body);
      const data = await createPresignedPutUrl({ key, contentType, expiresIn });
      return NextResponse.json(data);
    } catch (err: any) {
      return NextResponse.json({ error: err.message ?? "Invalid request" }, { status: 400 });
    }
  }
""")

# API route for direct mode: expects JSON body with key, contentType, fileBase64
API_ROUTE_DIRECT = textwrap.dedent("""\
  import { NextRequest, NextResponse } from "next/server";
  import * as z from "zod";
  import { uploadDirect } from "@/lib/s3";

  const schema = z.object({
    key: z.string().min(3),
    contentType: z.string().min(3),
    fileBase64: z.string().min(1),
  });

  export async function POST(req: NextRequest) {
    try {
      const body = await req.json();
      const { key, contentType, fileBase64 } = schema.parse(body);

      // decode base64 payload -> Buffer
      const buffer = Buffer.from(fileBase64, "base64");
      const data = await uploadDirect({ key, contentType, body: buffer });
      return NextResponse.json(data);
    } catch (err: any) {
      return NextResponse.json({ error: err.message ?? "Invalid request" }, { status: 400 });
    }
  }
""")

# API route for both: offers both endpoints depending on "mode" field in JSON
API_ROUTE_BOTH = textwrap.dedent("""\
  import { NextRequest, NextResponse } from "next/server";
  import * as z from "zod";
  import { createPresignedPutUrl, uploadDirect } from "@/lib/s3";

  const schema = z.object({
    mode: z.enum(["presign", "direct"]).default("presign"),
    key: z.string().min(3),
    contentType: z.string().min(3),
    expiresIn: z.number().optional(),
    fileBase64: z.string().optional(),
  });

  export async function POST(req: NextRequest) {
    try {
      const body = await req.json();
      const { mode, key, contentType, expiresIn, fileBase64 } = schema.parse(body);

      if (mode === "presign") {
        const data = await createPresignedPutUrl({ key, contentType, expiresIn });
        return NextResponse.json(data);
      } else {
        if (!fileBase64) throw new Error("fileBase64 is required for direct mode");
        const buffer = Buffer.from(fileBase64, "base64");
        const data = await uploadDirect({ key, contentType, body: buffer });
        return NextResponse.json(data);
      }
    } catch (err: any) {
      return NextResponse.json({ error: err.message ?? "Invalid request" }, { status: 400 });
    }
  }
""")

# ------------ Main script ------------
def main():
    parser = argparse.ArgumentParser(description="Automate Cloudflare R2 (S3) scaffolding in a Next.js project.")
    parser.add_argument("project_path", help="Path to the Next.js project root")
    parser.add_argument("--mode", choices=["presign", "direct", "both"], default="presign", help="Upload mode to scaffold")
    parser.add_argument("--pm", choices=["pnpm", "npm", "yarn"], default="pnpm", help="Package manager to use (pnpm default)")
    args = parser.parse_args()

    project = os.path.abspath(args.project_path)
    mode = args.mode
    pm = args.pm

    if not os.path.isdir(project):
        print(f"[ERROR] Project path does not exist: {project}")
        sys.exit(1)

    # verify package manager availability; fallback to npm if pnpm not found
    if pm == "pnpm" and shutil.which("pnpm") is None:
        print("[WARN] pnpm not found on PATH, falling back to npm.")
        pm = "npm"
    elif pm == "yarn" and shutil.which("yarn") is None:
        print("[WARN] yarn not found on PATH, falling back to npm.")
        pm = "npm"

    # dependencies to install
    deps = ["@aws-sdk/client-s3", "@aws-sdk/s3-request-presigner", "zod"]

    print(f"[INFO] Project: {project}")
    print(f"[INFO] Mode: {mode}")
    print(f"[INFO] Package manager: {pm}")

    # 1) Install dependencies
    if pm == "pnpm":
        install_cmd = f"pnpm add {' '.join(deps)}"
    elif pm == "yarn":
        install_cmd = f"yarn add {' '.join(deps)}"
    else:
        install_cmd = f"npm install {' '.join(deps)} --save"

    run_cmd(install_cmd, cwd=project)

    # 2) Create .env template
    env_path = os.path.join(project, ".env")
    if os.path.exists(env_path):
        print(f"[WARN] .env already exists at {env_path} - not overwriting")
    else:
        write_file(env_path, ENV_TEMPLATE)

    # 3) Create lib/s3.ts according to mode
    lib_dir = os.path.join(project, "lib")
    ensure_dir(lib_dir)
    s3_path = os.path.join(lib_dir, "s3.ts")

    if mode == "presign":
        write_file(s3_path, LIB_S3_PRESIGN)
    elif mode == "direct":
        write_file(s3_path, LIB_S3_DIRECT)
    else:  # both
        write_file(s3_path, LIB_S3_BOTH)

    # 4) Create API route file
    api_route_dir = os.path.join(project, "app", "api", "upload")
    ensure_dir(api_route_dir)
    api_route_path = os.path.join(api_route_dir, "route.ts")

    if mode == "presign":
        write_file(api_route_path, API_ROUTE_PRESIGN)
    elif mode == "direct":
        write_file(api_route_path, API_ROUTE_DIRECT)
    else:
        write_file(api_route_path, API_ROUTE_BOTH)

    # 5) Show next steps
    print("\n[FINISHED] R2 scaffolding created.\n")
    print("Next steps:")
    print(f"  1) Fill .env at: {env_path} with your R2 credentials and bucket name.")
    print("     - AWS_S3_BUCKET, AWS_S3_ENDPOINT, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, R2_URL")
    print("  2) In Next.js you can call POST /api/upload with JSON depending on chosen mode:")
    if mode == "presign":
        print('     { "key":"path/to/file.jpg", "contentType":"image/jpeg" } -> returns { url, key, publicUrl }')
    elif mode == "direct":
        print('     { "key":"path/to/file.jpg", "contentType":"image/jpeg", "fileBase64":"<base64>" } -> server uploads and returns { key, publicUrl }')
    else:
        print('     For mode "both": pass "mode":"presign" or "direct". For direct include fileBase64.')
    print("  3) Test the endpoint and integrate client-side upload logic (presigned: upload directly from browser to R2)\n")
    print("[TIP] If you need a front-end example, I can add a minimal React/Next snippet that uses fetch + presigned URL upload.\n")
    print("[DONE]")

if __name__ == "__main__":
    main()
