# HTTPS Domain Cutover

Use this after a real domain or subdomain is available.

## DNS

Create an A record:

```text
mpesa.example.com -> 54.193.78.115
```

Wait until DNS resolves:

```bash
dig +short mpesa.example.com
```

## AWS Security Group

Allow:

```text
80/tcp  from 0.0.0.0/0
443/tcp from 0.0.0.0/0
```

Keep Grafana direct port `3000` restricted or closed. The preferred Grafana URL
is the Nginx subpath:

```text
https://mpesa.example.com/grafana/
```

## Run On EC2

```bash
ssh -i ~/Downloads/my-data-key.pem ec2-user@54.193.78.115
cd ~/Real_Time_Transaction_Streaming-MPESA-

DOMAIN=mpesa.example.com \
EMAIL=admin@example.com \
ADMIN_CIDR=YOUR_PUBLIC_IP/32 \
bash deploy/scripts/setup_https.sh
```

The script:

- verifies DNS points to `54.193.78.115`
- installs Nginx/Certbot packages if needed
- issues a Let's Encrypt certificate
- configures HTTPS reverse proxying
- updates `.env` callback and Grafana URLs
- recreates the affected containers

## Daraja URLs

Register these after the cutover:

```text
https://mpesa.example.com/webhook/c2b/validation
https://mpesa.example.com/webhook/c2b/confirmation
https://mpesa.example.com/webhook/stk/callback
```
