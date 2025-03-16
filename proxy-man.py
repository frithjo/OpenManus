from itertools import cycle

import requests


class ProxyManager:
    def __init__(self):
        self.proxies = self.fetch_proxies()
        self.proxy_pool = cycle(self.proxies)

    def fetch_proxies(self):
        """Fetch a list of proxies from ProxyScrape."""
        url = "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=10000&country=all&ssl=yes&anonymity=all"
        response = requests.get(url)
        proxies = response.text.splitlines()
        return proxies

    def get_proxy(self):
        """Return the next proxy in the cycle."""
        return next(self.proxy_pool)


proxy_manager = ProxyManager()
