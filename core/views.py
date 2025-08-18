from django.http import HttpResponse

def home(request):
    """Simple home view that redirects users to main interfaces."""
    html = """
    <html>
    <head><title>Bangladesh Medicine Scraper</title></head>
    <body style="font-family: Arial; margin: 40px; text-align: center;">
        <h1>🏥 Bangladesh Medicine Scraper</h1>
        <p>Welcome to the medicine data management system</p>
        <div style="margin: 30px;">
            <a href="/admin/" style="margin: 10px; padding: 10px 20px; background: #007cba; color: white; text-decoration: none; border-radius: 5px;">📊 Admin Interface</a>
            <a href="/api/" style="margin: 10px; padding: 10px 20px; background: #28a745; color: white; text-decoration: none; border-radius: 5px;">🔗 API Endpoints</a>
        </div>
        <p><small>Medicine data from medex.com.bd</small></p>
    </body>
    </html>
    """
    return HttpResponse(html)
