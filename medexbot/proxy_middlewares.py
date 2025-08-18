from w3lib.http import basic_auth_header
from scrapy.utils.project import get_project_settings

class ProxyMiddleware:
    def process_request(self, request, spider):
        settings = get_project_settings()
        host = settings.get('PROXY_HOST')
        port = settings.get('PROXY_PORT')
        user = settings.get('PROXY_USER')
        password = settings.get('PROXY_PASSWORD')
        scheme = settings.get('PROXY_SCHEME', 'http')

        # Only set a proxy if both host and port are configured
        if host and port:
            request.meta['proxy'] = f"{scheme}://{host}:{port}"
            # Only add auth header if username & password are provided
            if user and password:
                request.headers["Proxy-Authorization"] = basic_auth_header(user, password)
            spider.logger.debug(f"Proxy enabled: {request.meta['proxy']}")
        else:
            # No proxy configured — do nothing
            spider.logger.debug("Proxy disabled (no PROXY_HOST/PROXY_PORT).")
