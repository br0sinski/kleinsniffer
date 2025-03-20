import requests
from bs4 import BeautifulSoup
import time
from dataclasses import dataclass
from typing import List, Set, Optional
import logging
import colorlog
from rich.console import Console
from rich.progress import Progress
from rich.panel import Panel
from datetime import datetime
import sys
import re
from requests.exceptions import RequestException


from collections import deque
import select

def get_user_config() -> dict:
    console = Console()
    
    console.print(Panel.fit(
        "[bold cyan]Willkommen beim kleinsniffer[/]\n"
        "Bitte konfiguriere deine Suche:",
        border_style="green"
    ))
    
    config = {}
    
    while True:
        query = console.input("[bold cyan]Suchbegriff eingeben (z.B. 'nintendo switch'): [/]").strip()
        if query:
            config['query'] = query
            break
        console.print("[red]Suchbegriff darf nicht leer sein![/]")

    while True:
        try:
            min_price = int(console.input("[bold cyan]Mindestpreis in € eingeben: [/]"))
            max_price = int(console.input("[bold cyan]Maximalpreis in € eingeben: [/]"))
            if min_price < max_price:
                config['min_price'] = min_price
                config['max_price'] = max_price
                break
            console.print("[red]Mindestpreis muss kleiner als Maximalpreis sein![/]")
        except ValueError:
            console.print("[red]Bitte gültige Zahlen eingeben![/]")

    while True:
        try:
            interval = int(console.input("[bold cyan]Aktualisierungsintervall in Minuten eingeben: [/]"))
            if interval > 0:
                config['interval'] = interval
                break
            console.print("[red]Intervall muss größer als 0 sein![/]")
        except ValueError:
            console.print("[red]Bitte eine gültige Zahl eingeben![/]")

    while True:
        try:
            history = int(console.input("[bold cyan]Anzahl der Anzeigen in der Historie (Standard: 20): [/]") or "20")
            if history > 0:
                config['history_size'] = history
                break
            console.print("[red]Anzahl muss größer als 0 sein![/]")
        except ValueError:
            console.print("[red]Bitte eine gültige Zahl eingeben![/]")

    while True:
        try:
            initial = int(console.input("[bold cyan]Anzahl der initialen Anzeigen (Standard: 10): [/]") or "10")
            if initial > 0:
                config['initial_ads'] = initial
                break
            console.print("[red]Anzahl muss größer als 0 sein![/]")
        except ValueError:
            console.print("[red]Bitte eine gültige Zahl eingeben![/]")

    console.print("\n[bold green]Konfiguration:[/]")
    console.print(Panel.fit(
        f"[bold]Suchbegriff: [cyan]{config['query']}[/]\n"
        f"Preisspanne: [green]{config['min_price']}€ - {config['max_price']}€[/]\n"
        f"Aktualisierung alle [cyan]{config['interval']}[/] Minuten\n"
        f"Historie: [cyan]{config['history_size']}[/] Anzeigen\n"
        f"Initiale Anzeigen: [cyan]{config['initial_ads']}[/]",
        border_style="cyan"
    ))

    return config

    

@dataclass
class AdConfig:
    query: str
    min_price: int
    max_price: int
    interval: int
    history_size: int = 5
    initial_ads: int = 5
    base_url: str = "https://www.kleinanzeigen.de"

    def get_search_url(self) -> str:
        return f"{self.base_url}/s-{self.query.replace(' ', '-')}/k0"



@dataclass
class Advertisement:
    id: str
    title: str
    price: str
    link: str
    timestamp: datetime = datetime.now()


class KleinanzeigenScraper:
    def __init__(self, config: AdConfig):
        self.config = config
        self.seen_ads: Set[str] = set()
        self.ad_history = deque(maxlen=config.history_size)
        self.console = Console()
        self.setup_logging()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def setup_logging(self):
        handler = colorlog.StreamHandler()
        handler.setFormatter(colorlog.ColoredFormatter(
            '%(log_color)s%(asctime)s - %(levelname)s - %(message)s',
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red,bg_white',
            }
        ))
        logger = logging.getLogger()
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

    def extract_price(self, text: str) -> str:
        logging.debug(f"Extracting price from: {text}")
        price_match = re.search(r'(\d+[.,]?\d*)', text)
        if "VB" in text and price_match:
            price = price_match.group(1).replace(',', '.')
            return f"{price}€ VB"
        elif "VB" in text:
            return "VB"
        elif price_match:
            price = price_match.group(1).replace(',', '.')
            return price + "€"
        else:
            logging.warning(f"No price found in text: {text}")
            return "Preis nicht verfügbar"
    
    def fetch_page(self) -> Optional[BeautifulSoup]:
        try:
            url = self.config.get_search_url()
            logging.info(f"Abrufe URL: {url}")
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            return soup
        except RequestException as e:
            logging.error(f"Fehler beim Abrufen der Seite: {e}")
            return None


    def parse_advertisement(self, ad_element) -> Optional[Advertisement]:
        try:
            ad_id = ad_element.get('data-adid')
            if not ad_id:
                logging.warning("Keine Ad-ID gefunden")
                return None

            title_element = ad_element.find('h2', {'class': 'titlestring'}) or ad_element.find('a', {'class': 'ellipsis'})
            if not title_element:
                logging.warning(f"Kein Titel gefunden für Ad {ad_id}")
                return None
            title = title_element.get_text(strip=True)

            # Versuche, das Hauptelement für den Preis zu finden
            price_element = ad_element.find('p', {'class': 'aditem-main--middle--price'})
            if not price_element:
                # Wenn das Hauptelement nicht gefunden wird, suche nach alternativen Elementen
                price_element = ad_element.find('p', {'class': 'price'}) or ad_element.find('div', {'class': 'price-amount'}) or ad_element.find('p', {'class': 'aditem-main--middle--price-shipping--price'})

            if price_element:
                raw_price = price_element.get_text(strip=True)
                price = self.extract_price(raw_price)
            else:
                price = "Preis nicht verfügbar"
                logging.warning(f"Kein Preis gefunden für Ad {ad_id}")


            link_element = ad_element.find('a', {'class': 'ellipsis'})
            if not link_element:
                logging.warning(f"Kein Link gefunden für Ad {ad_id}")
                return None
            link = link_element.get('href')
            if not link.startswith("http"):
                link = self.config.base_url + link

            return Advertisement(
                id=ad_id,
                title=title,
                price=price,
                link=link
            )

        except Exception as e:
            logging.error(f"Fehler beim Parsen der Anzeige {ad_element}: {e}")
            return None
    

    def display_ad(self, ad: Advertisement):
        self.console.print(Panel.fit(
            f"[bold cyan]{ad.title}[/]\n"
            f"[green]{ad.price}[/]\n"
            f"[blue underline]{ad.link}[/]\n"
            f"[dim]Gefunden: {ad.timestamp.strftime('%H:%M:%S')}[/]",
            title="[bold]Anzeige[/]",
            border_style="cyan"
        ))

    def display_history(self):
        if not self.ad_history:
            self.console.print("[yellow]Noch keine Anzeigen in der Historie[/]")
            return

        self.console.print(f"\n[bold yellow]Letzte {len(self.ad_history)} Anzeigen:[/]")
        for ad in reversed(self.ad_history):
            self.display_ad(ad)

    def check_user_input(self):
        if select.select([sys.stdin], [], [], 0.0)[0]:
            sys.stdin.readline()
            self.display_history()
            self.console.print("\n[bold cyan]Drücke ENTER für Historie oder CTRL+C zum Beenden[/]")

    def fetch_initial_ads(self):
        self.console.print("\n[bold cyan]Lade erste Anzeigen...[/]")
        with Progress() as progress:
            task = progress.add_task("[cyan]Durchsuche Kleinanzeigen...", total=None)
            
            soup = self.fetch_page()
            if soup:
                ads = soup.find_all('article', {'class': 'aditem'}) or \
                    soup.find_all('div', {'class': 'ad-listitem'})
                initial_ads = []

                for ad_element in ads[:self.config.initial_ads]:
                    ad = self.parse_advertisement(ad_element)
                    if ad:  
                        self.seen_ads.add(ad.id)
                        initial_ads.append(ad)
                        self.ad_history.append(ad)

                progress.update(task, completed=100)

                if initial_ads:
                    self.console.print(f"\n[bold green]Aktuelle Anzeigen ({len(initial_ads)}):[/]")
                    for ad in initial_ads:
                        self.display_ad(ad)
                else:
                    self.console.print("[yellow]Keine Anzeigen gefunden[/]")
                    logging.warning("Keine Anzeigen konnten geparst werden")

    def run(self):
        self.console.print(Panel.fit(
            f"[bold]Suche nach: [cyan]{self.config.query}[/]\n"
            f"Preisspanne: [green]{self.config.min_price}€ - {self.config.max_price}€[/]\n"
            f"Aktualisierung alle [cyan]{self.config.interval}[/] Minuten\n"
            f"Zeige initial [cyan]{self.config.initial_ads}[/] Anzeigen[/]",
            title="[bold]kleinsniffer[/]",
            border_style="green"
        ))

        self.fetch_initial_ads()
        
        self.console.print("\n[bold cyan]Drücke ENTER für Historie oder CTRL+C zum Beenden[/]")
        
        try:
            while True:
                with Progress() as progress:
                    task = progress.add_task(
                        "[cyan]Durchsuche Kleinanzeigen...", 
                        total=None
                    )
                    
                    soup = self.fetch_page()
                    if not soup:
                        time.sleep(30) 
                        continue

                    ads = soup.find_all('article', {'class': 'aditem'})
                    new_ads = []

                    for ad_element in ads:
                        ad = self.parse_advertisement(ad_element)
                        if ad:
                            if ad.id not in self.seen_ads:
                                self.seen_ads.add(ad.id)
                                new_ads.append(ad)
                                self.ad_history.append(ad)

                    progress.update(task, completed=100)

                if new_ads:
                    self.console.print(f"\n[bold green]Gefundene neue Anzeigen ({len(new_ads)}):[/]")
                    for ad in new_ads:
                        self.display_ad(ad)
                else:
                    logging.info("Keine neuen Anzeigen gefunden")

                for _ in range(self.config.interval * 60):
                    self.check_user_input()
                    time.sleep(1)

        except KeyboardInterrupt:
            self.console.print("\n[bold yellow]Programm wird beendet...[/]")
            self.display_history()
            sys.exit(0)



if __name__ == "__main__":
    user_config = get_user_config()
    config = AdConfig(**user_config)
    scraper = KleinanzeigenScraper(config)
    scraper.run()