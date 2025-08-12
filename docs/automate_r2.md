# 🚀 Automatisation Cloudflare R2 pour Next.js avec AWS SDK

## 🎯 Objectif

Ce script Python automatise l’installation et la configuration de **Cloudflare R2** dans un projet **Next.js**, en utilisant **AWS SDK v3** et offrant le choix entre deux méthodes d’upload :  

- **Presigned URL** : upload direct depuis le navigateur vers R2.  
- **S3 Direct Client** : upload depuis le backend uniquement.  

---

## ⚙️ Fonctionnalités

- 📦 Installation automatique des dépendances :
  - `@aws-sdk/client-s3`
  - `@aws-sdk/s3-request-presigner` *(si Presigned URL)*
  - `zod` pour la validation
- 📝 Génération d’un fichier `.env` préconfiguré avec :
  - `AWS_S3_BUCKET`
  - `AWS_REGION`
  - `AWS_S3_ENDPOINT`
  - `AWS_ACCESS_KEY_ID`
  - `AWS_SECRET_ACCESS_KEY`
  - `R2_URL`
- 📂 Création automatique des fichiers TypeScript :
  - Librairie `lib/s3.ts`
  - Routes API `/api/upload/...` adaptées au mode choisi
- 🔄 Choix interactif **depuis le script Python** :
  - Mode **Presigned URL**
  - Mode **S3 Direct**

---

## 📦 Installation

```bash
python automate_r2.py CHEMIN_PROJET [--mode presign|direct] [--pm pnpm|npm|yarn]
