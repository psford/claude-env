# Deploying Stock Analyzer to Oracle Cloud Free Tier

This guide walks through deploying the .NET 8 Stock Analyzer app to Oracle Cloud Infrastructure (OCI) Always Free tier using Docker on Ubuntu.

---

## Why Oracle Cloud?

| Feature | Oracle Always Free | Azure/AWS Free |
|---------|-------------------|----------------|
| Duration | **Forever** | 12 months |
| ARM VM | 4 OCPUs, 24GB RAM | Limited |
| Storage | 200GB block storage | Limited |
| Egress | **10TB/month** | ~100GB/month |
| Credit card | Required (not charged) | Required |

Oracle's free tier is the most generous and doesn't expire.

---

## Prerequisites

- Oracle Cloud account ([sign up free](https://www.oracle.com/cloud/free/))
- Credit card (for verification only - won't be charged for Always Free resources)
- Basic familiarity with Linux command line
- SSH client (built into Windows 10+, macOS, Linux)

---

## Recommended OS: Ubuntu 22.04 LTS

This guide uses **Ubuntu 22.04 LTS (Jammy Jellyfish)** for the following reasons:

| Factor | Ubuntu 22.04 LTS |
|--------|------------------|
| Support | Until April 2027 |
| ARM64 | Excellent support |
| Docker | Official packages available |
| Documentation | Extensive community resources |
| Stability | Battle-tested in production |

**Alternative:** Ubuntu 24.04 LTS is also available with support until 2029, but 22.04 has more established documentation and proven stability.

---

## Part 1: Create Oracle Cloud Account

1. Go to [oracle.com/cloud/free](https://www.oracle.com/cloud/free/)
2. Click **Start for free**
3. Fill in account details
4. Select your **Home Region** (choose closest to your users - cannot be changed later)
5. Complete phone/credit card verification
6. Wait for account provisioning (can take a few minutes)

---

## Part 2: Create ARM VM Instance

### 2.1 Navigate to Compute

1. Log into [Oracle Cloud Console](https://cloud.oracle.com/)
2. Click hamburger menu (top-left) > **Compute** > **Instances**
3. Click **Create instance**

### 2.2 Configure Instance

| Setting | Value |
|---------|-------|
| Name | `stock-analyzer` |
| Compartment | (default) |
| Placement | (default) |

### 2.3 Image and Shape

1. Click **Edit** in the "Image and shape" section
2. Click **Change image**
   - Click **Ubuntu** in the image list
   - Select **Canonical Ubuntu 22.04** (aarch64 version for ARM)
   - Click **Select image**
3. Click **Change shape**
   - Select **Ampere** (ARM processor)
   - Shape: **VM.Standard.A1.Flex**
   - OCPUs: **2** (save some for future use)
   - Memory: **12 GB**
   - Click **Select shape**

### 2.4 Networking

1. Under "Primary VNIC information":
   - Select **Create new virtual cloud network**
   - Select **Create new public subnet**
   - Check **Assign a public IPv4 address**

### 2.5 SSH Keys

1. Under "Add SSH keys":
   - Select **Generate a key pair for me**
   - Click **Save private key** (save as `oracle-vm-key.key`)
   - Click **Save public key** (optional backup)

   **IMPORTANT:** Keep the private key safe! You cannot download it again.

### 2.6 Boot Volume

- Leave defaults (50GB is sufficient)
- Check **Use in-transit encryption**

### 2.7 Create

Click **Create** and wait for the instance to reach **RUNNING** state (1-2 minutes).

---

## Part 3: Configure Network Security

### 3.1 Open Ports

1. Click on your instance name
2. Under **Primary VNIC**, click the **Subnet** link
3. Click the **Security List** (default security list)
4. Click **Add Ingress Rules**

Add these rules:

| Source CIDR | Protocol | Dest Port | Description |
|-------------|----------|-----------|-------------|
| `0.0.0.0/0` | TCP | 80 | HTTP |
| `0.0.0.0/0` | TCP | 443 | HTTPS |
| `0.0.0.0/0` | TCP | 5000 | .NET Kestrel |

Click **Add Ingress Rules** for each.

---

## Part 4: Connect to VM

### 4.1 Get Public IP

1. Go to **Compute** > **Instances**
2. Copy the **Public IP address**

### 4.2 SSH Connect

```bash
# Fix key permissions (required on first use)
chmod 400 oracle-vm-key.key

# Connect (Ubuntu uses 'ubuntu' user)
ssh -i oracle-vm-key.key ubuntu@<PUBLIC_IP>
```

On Windows (PowerShell):
```powershell
# Connect
ssh -i oracle-vm-key.key ubuntu@<PUBLIC_IP>
```

---

## Part 5: Install Docker

Run these commands on the VM:

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install prerequisites
sudo apt install -y ca-certificates curl gnupg lsb-release

# Add Docker's official GPG key
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Add Docker repository
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Start Docker
sudo systemctl start docker
sudo systemctl enable docker

# Add current user to docker group (avoids needing sudo)
sudo usermod -aG docker $USER

# Log out and back in for group change to take effect
exit
```

Reconnect via SSH, then verify:
```bash
docker --version
docker run hello-world
```

---

## Part 6: Deploy Stock Analyzer

### 6.1 Create Dockerfile

On your local machine, create `Dockerfile` in the `stock_analyzer_dotnet` folder:

```dockerfile
# Build stage
FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
WORKDIR /src

# Copy csproj files and restore
COPY src/StockAnalyzer.Api/StockAnalyzer.Api.csproj src/StockAnalyzer.Api/
COPY src/StockAnalyzer.Core/StockAnalyzer.Core.csproj src/StockAnalyzer.Core/
RUN dotnet restore src/StockAnalyzer.Api/StockAnalyzer.Api.csproj

# Copy everything else and build
COPY . .
RUN dotnet publish src/StockAnalyzer.Api/StockAnalyzer.Api.csproj -c Release -o /app/publish

# Runtime stage
FROM mcr.microsoft.com/dotnet/aspnet:8.0 AS runtime
WORKDIR /app
COPY --from=build /app/publish .

# Expose port
EXPOSE 5000

# Set environment
ENV ASPNETCORE_URLS=http://+:5000
ENV ASPNETCORE_ENVIRONMENT=Production

ENTRYPOINT ["dotnet", "StockAnalyzer.Api.dll"]
```

### 6.2 Create docker-compose.yml

```yaml
version: '3.8'

services:
  stock-analyzer:
    build: .
    container_name: stock-analyzer
    ports:
      - "5000:5000"
    environment:
      - ASPNETCORE_ENVIRONMENT=Production
      - Finnhub__ApiKey=${FINNHUB_API_KEY}
    restart: unless-stopped
```

### 6.3 Transfer Files to VM

Option A - Using Git (recommended):
```bash
# On VM
cd ~
git clone <your-repo-url> stock-analyzer
cd stock-analyzer/stock_analyzer_dotnet
```

Option B - Using SCP:
```bash
# On local machine
scp -i oracle-vm-key.key -r ./stock_analyzer_dotnet ubuntu@<PUBLIC_IP>:~/
```

### 6.4 Configure API Keys

On the VM:
```bash
cd ~/stock_analyzer_dotnet  # or wherever you cloned/copied

# Create .env file for secrets
cat > .env << 'EOF'
FINNHUB_API_KEY=your_finnhub_api_key_here
EOF
```

### 6.5 Build and Run

```bash
# Build Docker image
docker compose build

# Start container
docker compose up -d

# Check logs
docker compose logs -f

# Verify running
docker ps
```

### 6.6 Configure Firewall

Ubuntu uses `iptables` by default on Oracle Cloud. Open the required port:

```bash
# Open port 5000
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 5000 -j ACCEPT

# Save the rules to persist across reboots
sudo netfilter-persistent save
```

Alternatively, you can use `ufw` (Uncomplicated Firewall):
```bash
# Install ufw if not present
sudo apt install -y ufw

# Allow SSH (important - do this first!)
sudo ufw allow 22/tcp

# Allow app port
sudo ufw allow 5000/tcp

# Enable firewall
sudo ufw enable

# Verify
sudo ufw status
```

---

## Part 7: Test Deployment

Open in browser:
```
http://<PUBLIC_IP>:5000
```

You should see the Stock Analyzer dashboard!

---

## Part 8: Set Up HTTPS (Optional but Recommended)

### 8.1 Get a Domain

- Free options: [Freenom](https://freenom.com), [DuckDNS](https://www.duckdns.org/)
- Point A record to your VM's public IP

### 8.2 Install Caddy (Auto-HTTPS)

Caddy automatically obtains and renews SSL certificates:

```bash
# Install Caddy
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update
sudo apt install -y caddy

# Create Caddyfile
sudo tee /etc/caddy/Caddyfile << 'EOF'
yourdomain.com {
    reverse_proxy localhost:5000
}
EOF

# Open HTTPS ports in firewall (using iptables)
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo netfilter-persistent save

# Or using ufw:
# sudo ufw allow 80/tcp
# sudo ufw allow 443/tcp

# Start Caddy
sudo systemctl enable caddy
sudo systemctl start caddy
```

Now access via `https://yourdomain.com`

---

## Maintenance Commands

```bash
# View logs
docker compose logs -f

# Restart app
docker compose restart

# Update app (after git pull or file changes)
docker compose down
docker compose build --no-cache
docker compose up -d

# Check resource usage
docker stats

# SSH to container for debugging
docker exec -it stock-analyzer /bin/bash
```

---

## Avoiding Idle Reclamation

Oracle may reclaim Always Free instances that are idle (CPU < 20% for 7 days).

Options to prevent this:
1. **Actual usage** - Regular visitors keep it active
2. **Health check cron** - Add a cron job that hits an endpoint
3. **Uptime monitor** - Use [UptimeRobot](https://uptimerobot.com/) (free) to ping your site every 5 minutes

```bash
# Option 2: Add cron job
crontab -e

# Add this line (pings every 5 minutes)
*/5 * * * * curl -s http://localhost:5000/api/health > /dev/null
```

---

## Troubleshooting

### Container won't start
```bash
docker compose logs
```

### Can't connect from browser
1. Check OCI security list has ingress rule for port 5000
2. Check VM firewall: `sudo iptables -L INPUT -n` or `sudo ufw status`
3. Check container is running: `docker ps`

### Out of memory
Reduce container memory or use smaller VM shape.

### SSH connection refused
- Verify public IP is correct
- Ensure you're using `ubuntu` user: `ssh -i oracle-vm-key.key ubuntu@<IP>`
- Check security list has port 22 open (default)
- Verify key file permissions: `chmod 400 oracle-vm-key.key`

---

## Cost Summary

| Resource | Cost |
|----------|------|
| ARM VM (4 OCPU, 24GB) | **Free forever** |
| 200GB storage | **Free forever** |
| 10TB egress/month | **Free forever** |
| Public IP | **Free** (1 reserved) |
| **Total** | **$0/month** |

---

## References

- [Oracle Always Free Resources](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm)
- [Oracle Cloud Free Tier](https://www.oracle.com/cloud/free/)
- [Run Docker on OCI Free Tier](https://medium.com/oracledevs/run-always-free-docker-container-on-oracle-cloud-infrastructure-c88e36b65610)
- [.NET on OCI](https://blogs.oracle.com/cloud-infrastructure/post/running-net-applications-in-oracle-cloud-infrastructure-quickly-and-easily)
