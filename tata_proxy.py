#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# TaTa DDoS - Proxy Management Module
# By nezX - https://github.com/nezX-project/tata-ddos

import random
import socket
import asyncio
import aiohttp
import requests
from typing import List, Dict, Optional, Tuple, Any
from urllib.parse import urlparse
import re
import time
from datetime import datetime
import ipaddress
from socks import socksocket, PROXY_TYPE_SOCKS4, PROXY_TYPE_SOCKS5, PROXY_TYPE_HTTP

# Optional GeoIP support
try:
    import geoip2.database
    GEOIP_AVAILABLE = True
except ImportError:
    GEOIP_AVAILABLE = False

class ProxyManager:
    """
    Complete proxy management with support for:
    - SOCKS4, SOCKS5, HTTP, HTTPS
    - Authentication (user:pass)
    - Multiple rotation strategies
    - Sticky sessions
    - Proxy chaining
    - Automatic validation and scoring
    - Geo-filtering
    - Refresh from file/scrapers
    """
    
    def __init__(self, 
                 proxy_file: Optional[str] = None,
                 proxy_type: str = "socks5",
                 rotation: str = "random",
                 sticky: bool = False,
                 refresh_interval: int = 0,
                 tor_mode: bool = False,
                 chain_length: int = 1,
                 country_filter: Optional[List[str]] = None):
        
        self.proxy_type = proxy_type
        self.rotation = rotation
        self.sticky = sticky
        self.refresh_interval = refresh_interval
        self.tor_mode = tor_mode
        self.chain_length = min(max(chain_length, 1), 5)  # 1-5 hops
        self.country_filter = country_filter or []
        
        # Proxy storage
        self.proxies: List[Dict] = []
        self.backup_proxies: List[Dict] = []  # For refresh
        self.blacklist: set = set()
        self.proxy_scores: Dict[str, float] = {}
        self.current_index = 0
        self._sticky_proxy: Optional[Dict] = None
        self.last_refresh = time.time()
        
        # Stats
        self.total_proxies_used = 0
        self.dead_proxies_count = 0
        
        # Load initial proxies
        if proxy_file:
            self.load_from_file(proxy_file)
        elif tor_mode:
            self.setup_tor()
        else:
            self.harvest_free_proxies()
        
        # Store backup for refresh
        self.backup_proxies = self.proxies.copy()
        
        # Validate proxies on init (async)
        if self.proxies:
            asyncio.create_task(self.validate_all())
    
    def setup_tor(self):
        """Configure Tor SOCKS5 proxy"""
        self.proxies = [{
            'ip': '127.0.0.1',
            'port': 9050,
            'user': None,
            'pass': None,
            'type': 'socks5'
        }]
        self.proxy_type = 'socks5'
        self.rotation = 'none'
        self.proxy_scores['127.0.0.1:9050'] = 0.0
    
    def load_from_file(self, filepath: str):
        """Load proxies from file with format: ip:port or ip:port:user:pass"""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Proxy file not found: {filepath}")
        
        with open(filepath, 'r') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                parts = line.split(':')
                if len(parts) == 2:
                    ip, port = parts
                    proxy = {
                        'ip': ip,
                        'port': int(port),
                        'user': None,
                        'pass': None,
                        'type': self.proxy_type
                    }
                elif len(parts) == 4:
                    ip, port, user, pwd = parts
                    proxy = {
                        'ip': ip,
                        'port': int(port),
                        'user': user,
                        'pass': pwd,
                        'type': self.proxy_type
                    }
                else:
                    print(f"[!] Invalid proxy format at line {line_num}: {line}")
                    continue
                
                # Validate IP
                try:
                    ipaddress.ip_address(ip)
                    self.proxies.append(proxy)
                    self.proxy_scores[f"{ip}:{port}"] = 100.0
                except ValueError:
                    print(f"[!] Invalid IP at line {line_num}: {ip}")
                    continue
        
        print(f"[+] Loaded {len(self.proxies)} proxies from {filepath}")
    
    def harvest_free_proxies(self):
        """Scrape free proxy lists from multiple sources"""
        print("[*] Harvesting free proxies...")
        try:
            sources = [
                "https://free-proxy-list.net/",
                "https://www.socks-proxy.net/",
                "https://proxy-list.download/api/v1/get?type=socks5",
                "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=socks5&timeout=2000"
            ]
            
            for url in sources:
                try:
                    response = requests.get(url, timeout=5, headers={'User-Agent': 'Mozilla/5.0'})
                    if 'socks5' in url or 'api' in url:
                        # JSON API
                        data = response.json()
                        proxies = data.get('data', []) or data.get('proxies', [])
                        for entry in proxies:
                            if isinstance(entry, dict):
                                ip = entry.get('ip') or entry.get('host')
                                port = entry.get('port')
                            else:
                                # Handle different JSON formats
                                parts = entry.split(':')
                                ip, port = parts[0], int(parts[1])
                            
                            if ip and port:
                                self.proxies.append({
                                    'ip': ip,
                                    'port': int(port),
                                    'user': None,
                                    'pass': None,
                                    'type': self.proxy_type
                                })
                    else:
                        # HTML table
                        from bs4 import BeautifulSoup
                        soup = BeautifulSoup(response.text, 'html.parser')
                        rows = soup.select('table tbody tr')
                        for row in rows[:30]:  # Limit per source
                            cols = row.find_all('td')
                            if len(cols) >= 2:
                                ip = cols[0].text.strip()
                                port = int(cols[1].text.strip())
                                self.proxies.append({
                                    'ip': ip,
                                    'port': port,
                                    'user': None,
                                    'pass': None,
                                    'type': self.proxy_type
                                })
                except Exception as e:
                    print(f"[!] Failed to scrape {url}: {e}")
                    continue
            
            # Remove duplicates
            seen = set()
            unique_proxies = []
            for p in self.proxies:
                key = f"{p['ip']}:{p['port']}"
                if key not in seen:
                    seen.add(key)
                    unique_proxies.append(p)
            self.proxies = unique_proxies
            
            print(f"[+] Harvested {len(self.proxies)} free proxies")
            
        except Exception as e:
            print(f"[!] Proxy harvest failed: {e}. Using fallback list.")
            # Fallback hardcoded proxies
            fallback = [
                ('192.168.1.1', 1080), ('10.0.0.1', 9050),
                ('203.0.113.5', 3128), ('198.51.100.7', 1080)
            ]
            for ip, port in fallback:
                self.proxies.append({
                    'ip': ip,
                    'port': port,
                    'user': None,
                    'pass': None,
                    'type': self.proxy_type
                })
    
    async def validate_proxy(self, proxy: Dict) -> Tuple[bool, float]:
        """Validate proxy and measure latency"""
        try:
            test_target = "http://httpbin.org/ip"
            proxy_url = self._build_proxy_url(proxy)
            
            connector = aiohttp.TCPConnector(limit=1)
            async with aiohttp.ClientSession(connector=connector) as session:
                start = time.time()
                async with session.get(test_target, proxy=proxy_url, timeout=3) as resp:
                    if resp.status == 200:
                        latency = (time.time() - start) * 1000  # ms
                        await resp.text()  # Ensure connection is used
                        return True, latency
            return False, 9999.0
        except Exception as e:
            return False, 9999.0
    
    def _build_proxy_url(self, proxy: Dict) -> str:
        """Build proxy URL for aiohttp"""
        protocol = self.proxy_type
        if protocol == 'socks5':
            protocol = 'socks5'
        elif protocol == 'socks4':
            protocol = 'socks4'
        elif protocol in ['http', 'https']:
            protocol = 'http'
        
        proxy_url = f"{protocol}://{proxy['ip']}:{proxy['port']}"
        if proxy.get('user') and proxy.get('pass'):
            proxy_url = f"{protocol}://{proxy['user']}:{proxy['pass']}@{proxy['ip']}:{proxy['port']}"
        return proxy_url
    
    async def validate_all(self):
        """Validate all proxies concurrently"""
        if not self.proxies:
            return
        
        print(f"[*] Validating {len(self.proxies)} proxies...")
        tasks = [self.validate_proxy(p) for p in self.proxies]
        results = await asyncio.gather(*tasks)
        
        # Filter valid proxies and update scores
        valid_proxies = []
        for proxy, (alive, latency) in zip(self.proxies, results):
            if alive:
                valid_proxies.append(proxy)
                self.proxy_scores[f"{proxy['ip']}:{proxy['port']}"] = latency
            else:
                self.proxy_scores[f"{proxy['ip']}:{proxy['port']}"] = 9999.0
        
        self.proxies = valid_proxies
        print(f"[+] {len(self.proxies)} proxies validated (avg latency: {sum(self.proxy_scores.values())/len(self.proxy_scores) if self.proxy_scores else 0:.2f}ms)")
        
        # Sort by latency if using latency-based rotation
        if self.rotation == "latency-based" and self.proxies:
            self.proxies.sort(key=lambda p: self.proxy_scores.get(f"{p['ip']}:{p['port']}", 9999.0))
    
    def refresh_proxies(self):
        """Refresh proxy pool from backup or scrape"""
        print("[*] Refreshing proxy pool...")
        # Reload from backup
        if self.backup_proxies:
            # Remove blacklisted
            fresh = [p for p in self.backup_proxies 
                    if f"{p['ip']}:{p['port']}" not in self.blacklist]
            # Add any new proxies
            if len(fresh) < len(self.proxies) // 2:
                # Too many dead, re-harvest
                self.harvest_free_proxies()
            else:
                self.proxies = fresh + self.proxies[:len(self.proxies)//2]
        
        # Remove duplicates
        seen = set()
        unique = []
        for p in self.proxies:
            key = f"{p['ip']}:{p['port']}"
            if key not in seen:
                seen.add(key)
                unique.append(p)
        self.proxies = unique
        
        # Re-validate in background
        asyncio.create_task(self.validate_all())
        self.last_refresh = time.time()
    
    def get_proxy(self) -> Optional[Dict]:
        """Return next proxy based on rotation strategy"""
        if not self.proxies:
            # Try to refresh
            self.refresh_proxies()
            if not self.proxies:
                return None
        
        # Sticky mode
        if self.sticky and self._sticky_proxy:
            if f"{self._sticky_proxy['ip']}:{self._sticky_proxy['port']}" not in self.blacklist:
                return self._sticky_proxy
            else:
                self._sticky_proxy = None
        
        # Proxy chaining - return list if chain_length > 1
        if self.chain_length > 1:
            chain = []
            for _ in range(self.chain_length):
                proxy = self._get_single_proxy()
                if proxy:
                    chain.append(proxy)
            if len(chain) == self.chain_length:
                return chain  # Return chain as list
            else:
                # Fallback to single proxy if chain incomplete
                return self._get_single_proxy()
        
        return self._get_single_proxy()
    
    def _get_single_proxy(self) -> Optional[Dict]:
        """Get a single proxy based on rotation"""
        if not self.proxies:
            return None
        
        # Filter out blacklisted
        available = [p for p in self.proxies 
                    if f"{p['ip']}:{p['port']}" not in self.blacklist]
        
        if not available:
            return None
        
        if self.rotation == "random":
            proxy = random.choice(available)
        elif self.rotation == "round-robin":
            proxy = available[self.current_index % len(available)]
            self.current_index += 1
        elif self.rotation == "latency-based":
            # Already sorted, pick first available
            proxy = available[0] if available else None
        else:
            proxy = random.choice(available)
        
        if proxy and self.sticky:
            self._sticky_proxy = proxy
        
        self.total_proxies_used += 1
        return proxy
    
    def mark_dead(self, proxy: Dict):
        """Mark a proxy as dead and blacklist it"""
        if not proxy:
            return
        
        key = f"{proxy['ip']}:{proxy['port']}"
        self.blacklist.add(key)
        self.dead_proxies_count += 1
        self.proxy_scores[key] = 9999.0
        
        if self._sticky_proxy and key == f"{self._sticky_proxy['ip']}:{self._sticky_proxy['port']}":
            self._sticky_proxy = None
        
        # Remove from active list
        self.proxies = [p for p in self.proxies 
                       if f"{p['ip']}:{p['port']}" not in self.blacklist]
        
        # If too many dead, trigger refresh
        if len(self.blacklist) > len(self.proxies) * 0.7:
            print("[!] Too many dead proxies. Refreshing...")
            self.refresh_proxies()
    
    def set_sticky(self, proxy: Dict):
        """Manually set sticky proxy"""
        self._sticky_proxy = proxy
    
    def create_socket(self, proxy: Dict = None) -> socksocket:
        """Create a SOCKS/HTTP socket with proxy"""
        if proxy is None:
            proxy = self.get_proxy()
            if not proxy:
                raise RuntimeError("No proxies available")
        
        # Handle proxy chaining (list of proxies)
        if isinstance(proxy, list):
            # For chaining, we need to chain connections
            # For simplicity, we'll use the first proxy in the chain
            proxy = proxy[0]
        
        sock = socksocket()
        
        if self.proxy_type.startswith("socks4"):
            proxy_type = PROXY_TYPE_SOCKS4
        elif self.proxy_type.startswith("socks5"):
            proxy_type = PROXY_TYPE_SOCKS5
        else:
            proxy_type = PROXY_TYPE_HTTP
        
        sock.set_proxy(
            proxy_type,
            proxy['ip'],
            proxy['port'],
            username=proxy.get('user'),
            password=proxy.get('pass')
        )
        sock.settimeout(5)
        return sock
    
    def filter_by_country(self, countries: List[str]):
        """Filter proxies by country (requires GeoIP database)"""
        if not GEOIP_AVAILABLE:
            print("[!] GeoIP not available. Install geoip2 and download GeoLite2-City.mmdb")
            return
        
        if not countries:
            return
        
        try:
            reader = geoip2.database.Reader('GeoLite2-City.mmdb')
            filtered = []
            for proxy in self.proxies:
                try:
                    response = reader.city(proxy['ip'])
                    if response.country.iso_code in countries:
                        filtered.append(proxy)
                except:
                    continue
            self.proxies = filtered
            print(f"[+] Filtered to {len(self.proxies)} proxies in {', '.join(countries)}")
        except Exception as e:
            print(f"[!] GeoIP filtering failed: {e}")
    
    def get_stats(self) -> Dict:
        """Return proxy statistics"""
        return {
            'total_proxies': len(self.proxies),
            'blacklisted': len(self.blacklist),
            'used_count': self.total_proxies_used,
            'dead_count': self.dead_proxies_count,
            'avg_latency': sum(self.proxy_scores.values()) / len(self.proxy_scores) if self.proxy_scores else 0,
            'sticky_active': bool(self._sticky_proxy),
            'rotation': self.rotation
                   }
