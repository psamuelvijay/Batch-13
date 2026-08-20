# 📝 How to Rename GitHub Repository

## Current Repository
- **Name**: Batch-13
- **URL**: https://github.com/psamuelvijay/Batch-13

## Recommended New Name
`PhantomGuard-IoT-IDS` or `PhantomGuard`

---

## Step-by-Step Instructions

### 1. Rename on GitHub (Web Interface)

1. Go to https://github.com/psamuelvijay/Batch-13
2. Click the **Settings** tab (top right)
3. Scroll down to **Repository name** section
4. Change `Batch-13` to `PhantomGuard-IoT-IDS`
5. Click **Rename** button
6. GitHub will show a confirmation that redirects are set up

### 2. Update Local Repository

Open PowerShell in your project folder and run:

```bash
cd "e:\My_Projects\Mini Project"
git remote set-url origin https://github.com/psamuelvijay/PhantomGuard-IoT-IDS.git
```

Verify the change:
```bash
git remote -v
```

Should show:
```
origin  https://github.com/psamuelvijay/PhantomGuard-IoT-IDS.git (fetch)
origin  https://github.com/psamuelvijay/PhantomGuard-IoT-IDS.git (push)
```

### 3. Test the Connection

```bash
git fetch origin
```

If no errors, the rename is successful! ✅

---

## Alternative Repository Names

If `PhantomGuard-IoT-IDS` is taken or too long, try:

- `PhantomGuard`
- `IoT-Behavioral-IDS`
- `IoT-Phantom-Detection`
- `Behavioral-IoT-Security`
- `PhantomGuard-Security`

---

## Why Rename?

- **Professional**: "Batch-13" doesn't describe the project
- **Searchable**: "PhantomGuard-IoT-IDS" tells reviewers what it does
- **Portfolio**: Better for showcasing to future employers/academics
- **SEO**: More discoverable on GitHub search

---

## Note

GitHub automatically sets up redirects, so:
- Old links (`github.com/psamuelvijay/Batch-13`) still work
- No need to update documentation immediately
- Collaborators' clones continue working

But updating the README and local remote is recommended for clarity.

---

**Current Status**: Repository name is still `Batch-13` — rename when ready! ✅
