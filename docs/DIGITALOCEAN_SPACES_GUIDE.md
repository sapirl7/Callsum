# 🌊 Using DigitalOcean Spaces Instead of AWS S3

## Why Use DigitalOcean Spaces?

**Advantages:**
- 💰 **Cheaper** — $5/month for 250 GB (vs AWS S3 ~$6–10/month)
- 🌍 **Simpler pricing** — flat rate, no surprises
- 🔌 **S3-compatible** — works with boto3 out of the box

**Disadvantages:**
- ❌ No automatic Terraform management (Spaces must be created manually)
- ❌ Fewer regions than AWS
- ❌ No versioning or lifecycle policies via API

---

## 📋 Step-by-Step Instructions

### Step 1: Create a DigitalOcean account

1. Go to https://www.digitalocean.com
2. Sign up
3. Link a payment method

---

### Step 2: Create a Space

1. In the dashboard: **Manage → Spaces Object Storage**
2. Click **Create a Space**
3. **Choose a region:**
   - `fra1` — Frankfurt, Germany
   - `nyc3` — New York, USA
   - `sgp1` — Singapore
   - `sfo3` — San Francisco, USA
   - `ams3` — Amsterdam, Netherlands
4. **Space name:** `callsum-prod-<your-initials>`
   - ⚠️ Must match `s3_bucket_name` in terraform.tfvars
   - Must be globally unique
5. **Enable CDN:** No (not needed for private data)
6. Click **Create a Space**

**💰 Cost:** $5/month (includes 250 GB storage + 1 TB transfer)

---

### Step 3: Get API keys

1. In the dashboard: **API → Spaces Keys**
2. Click **Generate New Key**
3. **Name:** `callsum-production`
4. Click **Generate Key**
5. **Save:**
   - **Access Key** (e.g., `DO00ABC...XYZ`)
   - **Secret Key** (shown only once!)

⚠️ **IMPORTANT:** The Secret Key cannot be recovered! Save it in a secure location.

---

### Step 4: Configure Terraform

Edit `infrastructure/terraform/terraform.tfvars`:

```hcl
# === DIGITALOCEAN SPACES ===
use_digitalocean_spaces = true

# Endpoint (replace fra1 with your region)
s3_endpoint = "https://fra1.digitaloceanspaces.com"

# Keys from Step 3
s3_access_key = "DO00ABC...XYZ"
s3_secret_key = "your_secret_key_here"

# Space name (must match what was created in Step 2)
s3_bucket_name = "callsum-prod-your-initials"
```

---

### Step 5: Configure RunPod Environment Variables

In RunPod Endpoint Settings, add:

```bash
S3_ENDPOINT_URL=https://fra1.digitaloceanspaces.com
AWS_ACCESS_KEY_ID=DO00ABC...XYZ
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1  # Can be set to any value
```

---

### Step 6: Deploy

```bash
cd infrastructure/terraform
terraform init
terraform plan  # Verify that no AWS S3 bucket is being created
terraform apply
```

**Expected output:**
```
Plan: 14 to add, 0 to change, 0 to destroy.
# Should NOT include: aws_s3_bucket.callsum_storage
```

---

## ✅ Verification

### 1. CLI check

```bash
# Install s3cmd
brew install s3cmd  # macOS
# or
sudo apt install s3cmd  # Linux

# Configure
s3cmd --configure
# Enter DO Access Key and Secret
# Host: fra1.digitaloceanspaces.com
# S3 Endpoint: fra1.digitaloceanspaces.com

# Verify
s3cmd ls s3://callsum-prod-your-initials/
```

### 2. Python check

```python
import boto3

s3 = boto3.client(
    's3',
    endpoint_url='https://fra1.digitaloceanspaces.com',
    aws_access_key_id='DO00ABC...XYZ',
    aws_secret_access_key='your_secret_key',
    region_name='us-east-1'
)

response = s3.list_objects_v2(Bucket='callsum-prod-your-initials')
print(response)
```

### 3. Bot test

1. Send a voice message to the bot
2. Check DigitalOcean Spaces → your Space → Files
3. A folder `users/<user_id>/audio/new/` should appear

---

## 🔄 Migrating from AWS S3 to DigitalOcean Spaces

If you already have data in AWS S3:

### Option 1: AWS CLI (free)

```bash
aws s3 sync s3://old-aws-bucket s3://new-do-space \
  --endpoint-url https://fra1.digitaloceanspaces.com
```

### Option 2: rclone (recommended for large volumes)

```bash
brew install rclone  # macOS

rclone config
# Set up both AWS S3 and DO Spaces remotes

rclone copy aws-s3:old-bucket do-spaces:new-bucket
```

---

## 💰 Cost Comparison

### AWS S3

| Item | Cost |
|------|------|
| Storage (250 GB) | $5.75/month |
| PUT requests (10k) | $0.05 |
| GET requests (100k) | $0.04 |
| Transfer (100 GB) | $9.00 |
| **Total** | ~$15/month |

### DigitalOcean Spaces

| Item | Cost |
|------|------|
| Storage (250 GB) | $5/month |
| All requests | Included |
| Transfer (1 TB) | Included |
| **Total** | **$5/month** |

**Savings: ~$10/month (~66%)**

---

## 🛠 Troubleshooting

### Problem: "Access Denied"

**Cause:** Invalid credentials

**Solution:**
1. Verify Access Key and Secret Key are correct
2. Make sure the endpoint is correct (`https://region.digitaloceanspaces.com`)
3. Verify the Space exists and the name matches

### Problem: "NoSuchBucket"

**Cause:** Space not created or wrong name

**Solution:**
1. Create the Space via the DigitalOcean dashboard
2. Make sure `s3_bucket_name` in terraform.tfvars matches the Space name

### Problem: Presigned URLs not working

**Cause:** DigitalOcean requires virtual-hosted-style URLs

**Solution:** The code already handles this (boto3 does it automatically)

---

## 🔙 Switching back to AWS S3

```hcl
# terraform.tfvars
use_digitalocean_spaces = false

# Comment out DO credentials
# s3_endpoint = "..."
# s3_access_key = "..."
# s3_secret_key = "..."
```

```bash
terraform apply
```

Terraform will create an AWS S3 bucket and update Lambda environment variables.

---

## ✅ Readiness Checklist

- [ ] DigitalOcean account created
- [ ] Space created with the correct name
- [ ] API Keys obtained and saved
- [ ] `terraform.tfvars` updated
- [ ] RunPod environment variables configured
- [ ] `terraform apply` completed successfully
- [ ] Bot test passed
- [ ] Files appear in DigitalOcean Space
