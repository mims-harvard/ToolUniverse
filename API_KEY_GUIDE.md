# API Key Registration Guide
**Purpose**: Step-by-step instructions for obtaining API keys for authenticated tools
**Tools Requiring Keys**: 7 tools (BioGRID + ICD-11)
**Cost**: FREE for all

---

## Quick Reference

| Tool Suite | Keys Required | Registration URL | Time to Approve | Cost |
|------------|---------------|------------------|-----------------|------|
| BioGRID (4 tools) | BIOGRID_ACCESS_KEY | https://webservice.thebiogrid.org/ | Instant | FREE |
| ICD-11 (3 tools) | ICD_CLIENT_ID + ICD_CLIENT_SECRET | https://icd.who.int/icdapi | ~24 hours | FREE |

---

## BioGRID API Key

### Tools Using This Key
1. BioGRID_get_interactions
2. BioGRID_get_chemical_interactions
3. BioGRID_search_by_pubmed
4. BioGRID_get_ptms

### Registration Process

#### Step 1: Navigate to Registration Page
Open your browser and go to:
```
https://webservice.thebiogrid.org/
```

#### Step 2: Click "Request an API Key"
- Located in the top navigation or main page
- No account creation required

#### Step 3: Fill Out the Form
**Required Information**:
- **Name**: Your full name
- **Email**: Valid email address (you'll receive the key here)
- **Organization**: Your institution/company
- **Purpose**: Brief description (example: "Protein interaction research for drug target discovery")
- **Account Type**: Select "Academic" or "Commercial"
  - Academic: For university/non-profit research
  - Commercial: For commercial entities

**Example Purpose Text**:
```
Using BioGRID data for systematic analysis of protein-protein
interactions in cancer research. Part of ToolUniverse bioinformatics
pipeline for target discovery.
```

#### Step 4: Submit and Receive Key
- Click "Submit Request"
- ✅ **Instant Approval**: API key sent to your email immediately
- Key format: Long alphanumeric string (e.g., `abcd1234efgh5678...`)

#### Step 5: Set Environment Variable

**Linux/Mac**:
```bash
# Temporary (current session only)
export BIOGRID_ACCESS_KEY="your_key_here"

# Permanent (add to ~/.bashrc or ~/.zshrc)
echo 'export BIOGRID_ACCESS_KEY="your_key_here"' >> ~/.bashrc
source ~/.bashrc
```

**Windows (Command Prompt)**:
```cmd
setx BIOGRID_ACCESS_KEY "your_key_here"
```

**Windows (PowerShell)**:
```powershell
[System.Environment]::SetEnvironmentVariable("BIOGRID_ACCESS_KEY", "your_key_here", "User")
```

**Python (alternative)**:
```python
import os
os.environ["BIOGRID_ACCESS_KEY"] = "your_key_here"
```

#### Step 6: Verify Setup

**Test Command**:
```bash
curl "https://webservice.thebiogrid.org/interactions/?searchNames=true&geneList=TP53&accesskey=YOUR_KEY&format=json" | head -20
```

**Python Test**:
```python
from tooluniverse import ToolUniverse
tu = ToolUniverse()
tu.load_tools()

# Should succeed with valid key
result = tu.tools.BioGRID_get_interactions(
    gene_names=["TP53"],
    organism="9606",
    limit=10
)
print(result)
```

**Expected Success**: JSON response with interaction data

### Rate Limits
- **Limit**: 10,000 requests per day
- **Recommendation**: Cache results when possible
- **Monitoring**: Check response headers for usage stats

### Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| "Invalid access key" | Wrong key or not set | Verify environment variable is set correctly |
| "Rate limit exceeded" | >10,000 requests/day | Wait 24 hours or contact BioGRID for increase |
| "No data returned" | Invalid gene name | Check gene symbol spelling (use official symbols) |

---

## ICD-11 API Credentials

### Tools Using These Keys
1. ICD11_search_diseases
2. ICD11_get_entity
3. ICD11_browse_hierarchy

### Registration Process

#### Step 1: Navigate to WHO ICD API Portal
Open your browser and go to:
```
https://icd.who.int/icdapi
```

#### Step 2: Create Account
- Click "Register" or "Sign Up"
- Fill in required information:
  - Email address
  - Password
  - Name
  - Organization
  - Country
- Verify your email address (check inbox/spam)

#### Step 3: Register an Application
After logging in:

1. Navigate to "My Applications" or "API Management"
2. Click "Register a new application"
3. Fill out application form:

**Required Information**:
- **Application Name**: Your project name (e.g., "ToolUniverse Bioinformatics Pipeline")
- **Description**: Purpose of API usage
  ```
  Using ICD-11 API for disease classification and coding in biomedical
  research applications. Part of ToolUniverse research toolkit for
  clinical data standardization.
  ```
- **Application Type**: Select "Research" or "Clinical"
- **Redirect URL**: Can leave default or use `http://localhost` (not used for API calls)

#### Step 4: Obtain Credentials
After submitting your application (approval ~24 hours):

1. Go to "My Applications"
2. Select your registered application
3. View credentials:
   - **Client ID**: UUID format (e.g., `12345678-1234-1234-1234-123456789abc`)
   - **Client Secret**: Long alphanumeric string

⚠️ **Keep Client Secret confidential** - Do not share or commit to version control

#### Step 5: Set Environment Variables

**Linux/Mac**:
```bash
# Temporary
export ICD_CLIENT_ID="your_client_id_here"
export ICD_CLIENT_SECRET="your_client_secret_here"

# Permanent (add to ~/.bashrc or ~/.zshrc)
cat <<EOF >> ~/.bashrc
export ICD_CLIENT_ID="your_client_id_here"
export ICD_CLIENT_SECRET="your_client_secret_here"
EOF
source ~/.bashrc
```

**Windows (Command Prompt)**:
```cmd
setx ICD_CLIENT_ID "your_client_id_here"
setx ICD_CLIENT_SECRET "your_client_secret_here"
```

**Windows (PowerShell)**:
```powershell
[System.Environment]::SetEnvironmentVariable("ICD_CLIENT_ID", "your_client_id_here", "User")
[System.Environment]::SetEnvironmentVariable("ICD_CLIENT_SECRET", "your_client_secret_here", "User")
```

**.env file (recommended for projects)**:
```bash
# Create .env file in project root
echo "ICD_CLIENT_ID=your_client_id_here" > .env
echo "ICD_CLIENT_SECRET=your_client_secret_here" >> .env

# Add .env to .gitignore
echo ".env" >> .gitignore
```

#### Step 6: Test OAuth2 Token Generation

**Manual Test (curl)**:
```bash
curl -X POST "https://icdaccessmanagement.who.int/connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=YOUR_CLIENT_ID" \
  -d "client_secret=YOUR_CLIENT_SECRET" \
  -d "scope=icdapi_access" \
  -d "grant_type=client_credentials"
```

**Expected Response**:
```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIsImtpZCI6...",
  "expires_in": 3600,
  "token_type": "Bearer",
  "scope": "icdapi_access"
}
```

**Python Test**:
```python
from tooluniverse import ToolUniverse
tu = ToolUniverse()
tu.load_tools()

# Should succeed with valid credentials
result = tu.tools.ICD11_search_diseases(
    query="diabetes",
    flatResults=True
)
print(result)
```

### Authentication Flow
The ICD-11 API uses OAuth2 Client Credentials flow:

1. **Tool automatically requests token** using CLIENT_ID + CLIENT_SECRET
2. **Token cached** for ~55 minutes (expires after 60 min)
3. **Auto-refresh** when token expires
4. **No manual token management** required by user

### Rate Limits
- **Limit**: Not publicly specified; "reasonable use" expected
- **Token Validity**: 60 minutes (3600 seconds)
- **Recommendation**: Tool handles token caching automatically

### Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| "Invalid client credentials" | Wrong CLIENT_ID or CLIENT_SECRET | Verify credentials in WHO portal |
| "Token expired" | Token > 60 min old | Tool should auto-refresh; check implementation |
| "Scope not granted" | Missing icdapi_access scope | Re-register application with correct scope |
| "Application not approved" | Pending approval | Wait 24 hours; check email for approval notice |

---

## Security Best Practices

### Do NOT:
- ❌ Commit API keys to Git repositories
- ❌ Share API keys publicly (Slack, email, etc.)
- ❌ Use production keys in development/testing
- ❌ Hard-code keys in source code

### DO:
- ✅ Use environment variables
- ✅ Add `.env` to `.gitignore`
- ✅ Use separate keys for dev/prod
- ✅ Rotate keys periodically (every 6-12 months)
- ✅ Use secret management tools (AWS Secrets Manager, HashiCorp Vault)

### Recommended .gitignore Entries
```gitignore
# API Keys and Secrets
.env
.env.local
.env.*.local
*.key
*_secret.txt
api_keys.json
credentials.json
```

---

## Environment Variable Verification

### Check if Variables are Set

**Linux/Mac/Windows (all shells)**:
```bash
echo $BIOGRID_ACCESS_KEY
echo $ICD_CLIENT_ID
echo $ICD_CLIENT_SECRET
```

**Python Script**:
```python
import os

keys = {
    "BIOGRID_ACCESS_KEY": os.getenv("BIOGRID_ACCESS_KEY"),
    "ICD_CLIENT_ID": os.getenv("ICD_CLIENT_ID"),
    "ICD_CLIENT_SECRET": os.getenv("ICD_CLIENT_SECRET")
}

for name, value in keys.items():
    if value:
        print(f"✅ {name}: Set ({len(value)} chars)")
    else:
        print(f"❌ {name}: NOT SET")
```

---

## Integration with ToolUniverse

### Automatic Key Loading
ToolUniverse tools automatically check for required environment variables:

**BioGRID Example**:
```python
from tooluniverse import ToolUniverse
tu = ToolUniverse()
tu.load_tools()

# If BIOGRID_ACCESS_KEY not set, tool will raise helpful error:
# ValueError: BioGRID API key is required. Please provide 'api_key'
# parameter or set BIOGRID_ACCESS_KEY environment variable.
# Register at: https://webservice.thebiogrid.org/
```

**ICD-11 Example**:
```python
# If ICD_CLIENT_ID/SECRET not set, tool will raise error:
# "ICD API authentication required. Please set ICD_CLIENT_ID and
# ICD_CLIENT_SECRET environment variables. Register for free credentials
# at: https://icd.who.int/icdapi"
```

### Manual Key Passing (Alternative)
You can also pass keys directly as function arguments:

```python
# BioGRID (not recommended - use env var)
result = tu.tools.BioGRID_get_interactions(
    gene_names=["TP53"],
    api_key="your_key_here",  # Directly provided
    organism="9606"
)

# ICD-11 uses env vars only (no direct passing)
```

---

## FAQ

### Q: Do these keys cost money?
**A**: No, all registrations are FREE for academic and reasonable commercial use.

### Q: How long does approval take?
**A**:
- BioGRID: **Instant** (key sent to email immediately)
- ICD-11: **~24 hours** (manual approval by WHO team)

### Q: Can I use these keys on multiple machines?
**A**: Yes, but:
- Set the environment variables on each machine
- Respect rate limits (shared across all your machines)
- Consider key rotation for security

### Q: What if I lose my API key?
**A**:
- BioGRID: Request a new key (instant)
- ICD-11: Log into WHO portal and view credentials under "My Applications"

### Q: Can I use these keys in CI/CD pipelines?
**A**: Yes, store as CI secrets:
- GitHub Actions: Settings → Secrets → Actions secrets
- GitLab CI: Settings → CI/CD → Variables
- Jenkins: Credentials → Secret text
- Travis CI: Settings → Environment Variables

---

## Support & Resources

### BioGRID Support
- **Documentation**: https://wiki.thebiogrid.org/doku.php/biogridrest
- **Email**: support@thebiogrid.org
- **Forum**: https://thebiogrid.org/forums/

### ICD-11 Support
- **Documentation**: https://icd.who.int/docs/icd-api/APIDoc-Version2/
- **Email**: icd@who.int
- **Forum**: https://icd.who.int/dev11/f/en

---

## Testing Checklist

Before using tools in production, verify:

- [ ] BioGRID key obtained and set as environment variable
- [ ] ICD-11 credentials obtained and set as environment variables
- [ ] Environment variables persist across terminal sessions
- [ ] Keys work with test API calls (curl or Python)
- [ ] Keys added to `.gitignore` (if using .env files)
- [ ] Team members have their own keys (do not share)
- [ ] Production keys separate from development keys (if applicable)

---

## Summary

**Tools Ready After Setup**: 32/32 tools ✅
- 22 public API tools (no setup needed)
- 7 authenticated tools (BioGRID + ICD-11, FREE registration)
- 3 uncertain tools (ProteinsPlus, pending verification)

**Total Setup Time**: ~15 minutes (BioGRID instant + ICD-11 ~24hr approval)

**Recommendation**: Register for both keys immediately to minimize waiting time.

---

**Guide Complete**
