# LinkedIn Authority Mentor

> Dockerized Agentic AI that replaces n8n + Make.com for automated LinkedIn authority-building content posting.

## 🏗️ Architecture

```
Schedule Trigger (Mon/Wed/Fri 6PM IST)
    │
    ▼
Google Sheets → Read unprocessed row
    │
    ▼
Agent 1: Content Strategist → Generate structured outline
    │
    ▼
Agent 2: Post Formatter → Polish into LinkedIn post
    │
    ▼
Google Sheets → Write back + mark "Done"
    │
    ▼
LinkedIn API → Post to LinkedIn (PUBLIC)
```

## 🚀 Quick Start

### 1. Setup Environment

```bash
cd app/agent/linkedin-authority-mentor
cp .env.example .env
# Edit .env with your actual credentials
```

### 2. Build Docker Image

```bash
docker build -t linkedin-authority-mentor .
```

### 3. Verify Configuration (Optional)

```bash
docker run --env-file .env linkedin-authority-mentor --verify
```

### 4. Test without Google/LinkedIn (Dry Run)

You can test the entire AI pipeline (Agent 1 & 2) without any Google Sheets credentials or LinkedIn tokens. This uses a local CSV file (`data/test_queries.csv`) as the data source and skips the final post to LinkedIn.

```bash
# Run locally (requires OPENAI_API_KEY)
python -m src.main --dry-run

# Run in Docker
docker run --env-file .env linkedin-authority-mentor --dry-run
```

### 5. Test Run (one-off - Requires Credentials)

```bash
docker run --env-file .env linkedin-authority-mentor --run-now
```

### 5. Start Scheduler (production)

```bash
docker-compose up -d
```

## 📋 Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | ✅ | — | OpenAI API key |
| `OPENAI_MODEL` | — | `gpt-4o-mini` | Model to use |
| `GOOGLE_SHEETS_CREDENTIALS_B64` | ✅ | — | Base64-encoded service account JSON |
| `GOOGLE_SHEET_ID` | — | `1D9YE8q...` | Google Sheet document ID |
| `GOOGLE_SHEET_NAME` | — | `Linkedin Authority-Metor` | Worksheet tab name |
| `LINKEDIN_ACCESS_TOKEN` | ✅ | — | LinkedIn OAuth2 token |
| `LINKEDIN_PERSON_URN` | ✅ | — | Your LinkedIn person URN |
| `SCHEDULE_DAYS` | — | `mon,wed,fri` | Days to post |
| `SCHEDULE_HOUR` | — | `18` | Hour (24h format) |
| `SCHEDULE_TIMEZONE` | — | `Asia/Kolkata` | Timezone |

### Encoding Google Service Account Key

```bash
# On Linux/Mac:
base64 -w 0 service-account.json

# On Windows (PowerShell):
[Convert]::ToBase64String([IO.File]::ReadAllBytes("service-account.json"))
```

## 🔑 Getting LinkedIn Credentials

1. Go to [LinkedIn Developer Portal](https://developer.linkedin.com)
2. Create a new app
3. Request the `w_member_social` permission
4. Generate an OAuth2 access token
5. Get your person URN from the userinfo endpoint

## 📦 Deployment

### Render (Background Worker)

1. Push to GitHub
2. Create a new **Background Worker** on Render
3. Set **Docker** as the build type
4. Add environment variables in Render dashboard
5. Deploy

### AWS (ECS/Fargate)

1. Push image to ECR
2. Create ECS task definition
3. Run as a long-running service
