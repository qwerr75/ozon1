from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from playwright.async_api import async_playwright
import asyncio
import uvicorn

app = FastAPI()

class ParseRequest(BaseModel):
    url: str

@app.post("/parse")
async def parse(request: ParseRequest):
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
            page = await browser.new_page()

            # Маскировка под реального пользователя
            await page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            """)

            await page.goto(request.url, wait_until="domcontentloaded", timeout=15000)

            # Ждём появление заголовка
            await page.wait_for_selector("h1", timeout=10000)

            # Название
            title = await page.text_content("h1") or "Неизвестно"

            # Цена
            price = None
            price_elem = await page.query_selector("[data-widget='webPrice']")
            if price_elem:
                price_text = await price_elem.text_content()
                import re
                price_match = re.search(r'(\d[\d\s]*)\s*[₽руб]', price_text or "")
                if price_match:
                    price = int(price_match.group(1).replace(" ", ""))

            # Рейтинг
            rating = None
            rating_elem = await page.query_selector("span[data-widget='webReviewRating']")
            if rating_elem:
                rating_text = await rating_elem.text_content()
                rating_match = re.search(r'(\d+\.\d+|\d+)', rating_text or "")
                if rating_match:
                    rating = float(rating_match.group(1))

            await browser.close()

            return {
                "success": True,
                "data": {
                    "title": title.strip(),
                    "price": price,
                    "rating": rating,
                    "url": request.url
                }
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
