# Google Cloud Run Deployment Guide

## Prerequisites
1. Google Cloud account (free tier with $300 credits)
2. `gcloud` CLI installed locally
3. Docker installed (for testing locally)
4. Project code pushed to GitHub

## Step-by-Step Deployment

### 1. Set Up Google Cloud Project
```bash
# Install gcloud CLI from: https://cloud.google.com/sdk/docs/install

# Authenticate
gcloud auth login

# Create a new project
gcloud projects create finanza-app --name="Finanza Financial Services"

# Set project as default
gcloud config set project finanza-app

# Enable required APIs
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  containerregistry.googleapis.com \
  compute.googleapis.com \
  sql-component.googleapis.com
```

### 2. Set Up Cloud SQL Database (Optional but recommended)
```bash
# Create a PostgreSQL instance
gcloud sql instances create finanza-db \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=us-central1

# Create database
gcloud sql databases create finanza --instance=finanza-db

# Get connection name (for environment variables)
gcloud sql instances describe finanza-db --format='value(connectionName)'
```

### 3. Build and Deploy

#### Option A: Using gcloud deploy
```bash
# Build and deploy directly
gcloud run deploy finanza \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars DATABASE_URL="postgresql://user:password@/finanza?host=/cloudsql/PROJECT_ID:us-central1:finanza-db"
```

#### Option B: Using Cloud Build (from GitHub)
```bash
# Connect GitHub repository to Cloud Build
gcloud builds connect --repository-name=finanza --repository-owner=Supremeboss232

# Trigger deployment
gcloud builds submit --config=cloudbuild.yaml
```

### 4. Configure Environment Variables
```bash
# Create .env.prod for production
cat > .env.prod << EOF
DATABASE_URL=postgresql://user:password@/finanza?host=/cloudsql/CONNECTION_NAME
SECRET_KEY=your-random-secret-key-here
DEBUG=false
ENV=production
EOF
```

### 5. Set Up Custom Domain (Optional)
```bash
# Map your domain to Cloud Run
gcloud run services update finanza \
  --region us-central1 \
  --update-secrets DATABASE_URL=DATABASE_URL:latest
```

## Cost Estimation
- **Cloud Run**: ~$0-5/month (free tier generous, pay-as-you-go)
- **Cloud SQL (db-f1-micro)**: ~$8/month
- **Storage**: ~$0.02/month
- **Total**: ~$8-15/month (or less with free tier)

## Monitoring Logs
```bash
# View logs
gcloud run services describe finanza --region us-central1

# Stream logs in real-time
gcloud run logs read finanza --region us-central1 --follow
```

## Environment Variables Reference
Your app should read these from environment:
- `DATABASE_URL` - PostgreSQL connection string
- `SECRET_KEY` - JWT secret key
- `DEBUG` - Set to `false` in production
- `ENV` - Set to `production`

## Health Check
Cloud Run will automatically health check your app at `/`. Make sure your FastAPI app responds to health checks.

## Scaling
Cloud Run automatically scales based on traffic:
- Min instances: 0 (scales down after traffic stops)
- Max instances: 100 (configurable)
- Memory: 512MB (configurable)
- CPU: 1 vCPU (configurable)

## Next Steps
1. Complete the setup steps above
2. Test locally: `docker build -t finanza . && docker run -p 8080:8080 finanza`
3. Deploy to Cloud Run
4. Monitor performance in Google Cloud Console
5. Set up CI/CD pipeline for automatic deployments on git push

## Troubleshooting

### App times out
- Increase timeout: `gcloud run services update finanza --timeout=300`
- Check database connection

### High memory usage
- Profile with: `gcloud run services describe finanza --region us-central1`
- Increase memory allocation if needed

### Cold start too slow
- Set min instances: `gcloud run services update finanza --min-instances=1`

## Support
- Google Cloud Docs: https://cloud.google.com/run/docs
- FastAPI on Cloud Run: https://cloud.google.com/run/docs/quickstarts/build-and-deploy
