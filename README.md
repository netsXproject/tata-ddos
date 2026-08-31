# 🌀 TaTa DDoS – By netsX

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://python.org)
[![Rust 1.70+](https://img.shields.io/badge/rust-1.70+-orange.svg)](https://rust-lang.org)
[![Proxy Support](https://img.shields.io/badge/proxy-SOCKS4%2F5%2FHTTP-brightgreen)](https://github.com/nezX-project/tata-ddos)

> **Enterprise-grade stress-testing framework** – Simulate Black Friday traffic, DDoS attacks, and edge-case failures with full proxy rotation. Not for script kiddies.

![TaTa Banner](https://raw.githubusercontent.com/nezX-project/tata-ddos/main/assets/banner.png)

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
- **Distributed by design** – Redis + Kubernetes auto-scaling (optional).
- **Stealth king** – Poisson traffic shaping, TLS cipher rotation.
- **Live dashboard** – Real-time PPS, error rate, proxy stats.
- **Post-mortem AI** – Suggests firewall rules and mitigations.

---

## 📦 Installation

```bash
git clone https://github.com/nezX-project/tata-ddos.git
cd tata-ddos
python3 -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
cargo build --release  # Requires Rust installed
python3 setup.py install
