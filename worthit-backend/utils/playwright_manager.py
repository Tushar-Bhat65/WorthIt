# utils/playwright_manager.py
import asyncio
from contextlib import asynccontextmanager
from typing import Optional
from playwright.async_api import async_playwright, Playwright, Browser, BrowserContext

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36"

class PlaywrightManager:
    def __init__(self, prewarm: int = 2, max_concurrent: int = 4, headless: bool = True):
        self.prewarm = prewarm
        self.max_concurrent = max_concurrent
        self.headless = headless

        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._pool: Optional[asyncio.Queue] = None
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._started = False

    async def start(self):
        if self._started:
            return
        self._playwright = await async_playwright().start()
        # launch a single shared browser process
        self._browser = await self._playwright.chromium.launch(headless=self.headless,
                                                               args=["--no-sandbox", "--disable-dev-shm-usage"])
        self._pool = asyncio.Queue()
        self._semaphore = asyncio.Semaphore(self.max_concurrent)
        # Pre-warm contexts
        for _ in range(self.prewarm):
            ctx = await self._make_context()
            await self._pool.put(ctx)
        self._started = True

    async def stop(self):
        if not self._started:
            return
        # Close any contexts left in pool
        while not self._pool.empty():
            ctx = await self._pool.get()
            try:
                await ctx.close()
            except Exception:
                pass
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        self._started = False

    async def _make_context(self) -> BrowserContext:
        assert self._browser is not None
        ctx = await self._browser.new_context(user_agent=USER_AGENT,
                                              locale="en-US",
                                              bypass_csp=True)
        # optionally set default timeout on context/page usage
        return ctx

    @asynccontextmanager
    async def acquire_context(self, timeout: float = 6.0):
        """
        Acquire a browser context (from pool or newly created). Caller must create/close pages.
        This also uses a semaphore to limit concurrency.
        """
        if not self._started:
            raise RuntimeError("PlaywrightManager not started")
        await self._semaphore.acquire()
        ctx: Optional[BrowserContext] = None
        try:
            try:
                # try to get a pre-warmed context quickly
                ctx = self._pool.get_nowait()
            except asyncio.QueueEmpty:
                # create a new context if pool empty
                ctx = await self._make_context()
            yield ctx
        finally:
            # return context to pool if pool size less than prewarm, else close
            try:
                if ctx is None:
                    return
                # prefer to reuse the warmed contexts
                if self._pool.qsize() < self.prewarm:
                    await self._pool.put(ctx)
                else:
                    try:
                        await ctx.clear_cookies()
                    except Exception:
                        pass
                    # close extra contexts to reduce memory
                    await ctx.close()
            finally:
                self._semaphore.release()
