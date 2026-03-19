"""Server-side PDF generation using Playwright headless Chrome (mobile only)."""
import asyncio
import logging

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from playwright.async_api import async_playwright

from apps.tally.models import TallyInfo
from ._old_shared import _can_view_tally
from .detail import _paginate_containers

logger = logging.getLogger(__name__)


@login_required(login_url='login')
async def tally_pdf_download(request, pk):
    """Generate PDF from tally digital view using headless Chrome (mobile only)."""
    try:
        # Verify tally exists and user has permission
        tally = await asyncio.to_thread(
            get_object_or_404,
            TallyInfo.objects.prefetch_related("containers"),
            pk=pk
        )

        has_permission = await asyncio.to_thread(_can_view_tally, request.user, tally)
        if not has_permission:
            return HttpResponse('Permission denied', status=403)

        logger.info(f"Generating PDF for tally {pk} (mobile)")

        # Get session cookie for authentication
        session_cookie = request.COOKIES.get('sessionid')
        if not session_cookie:
            logger.error("No session cookie found")
            return HttpResponse('Authentication required', status=401)

        # Use public Railway URL instead of localhost to avoid worker deadlock
        public_url = f'https://eshipping-production.up.railway.app/tallies/{pk}/view/'

        async with async_playwright() as p:
            # Launch headless Chrome
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                ]
            )

            # Create context with session cookie for authentication
            context = await browser.new_context(
                viewport={'width': 1024, 'height': 1754}
            )

            # Set session cookie
            await context.add_cookies([{
                'name': 'sessionid',
                'value': session_cookie,
                'domain': 'eshipping-production.up.railway.app',
                'path': '/',
                'secure': True,
                'httpOnly': True,
            }])

            page = await context.new_page()

            # Navigate to the authenticated page
            await page.goto(public_url, wait_until='networkidle', timeout=30000)

            logger.info("Page loaded successfully with authentication")

            # Debug screenshot to verify rendering
            await page.screenshot(path='/tmp/debug_render.png', full_page=True)
            logger.info("Debug screenshot saved to /tmp/debug_render.png")

            # Wait for rendering
            await asyncio.sleep(2)

            # Hide action buttons and page indicators
            await page.evaluate("""
                () => {
                    const buttons = document.querySelector('.action-buttons');
                    const indicators = document.querySelectorAll('.page-indicator');
                    if (buttons) buttons.style.display = 'none';
                    indicators.forEach(el => el.style.display = 'none');
                }
            """)

            # Generate PDF
            pdf_bytes = await page.pdf(
                format='A4',
                print_background=True,
                margin={'top': '0', 'right': '0', 'bottom': '0', 'left': '0'}
            )

            await browser.close()

            logger.info(f"PDF generated successfully, size: {len(pdf_bytes)} bytes")

        # Return PDF as download
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="TALLY_{tally.tally_number}.pdf"'
        return response

    except Exception as e:
        logger.exception(f"PDF generation failed for tally {pk}")
        return HttpResponse(f'PDF generation failed: {str(e)}', status=500)
