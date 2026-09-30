import asyncio
import csv
import re
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from fake_useragent import UserAgent 
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async

us = UserAgent()



def get_random_user_agent():
    return us.random

import re

def extract_price_bulletproof(prt=None, apart_soup=None):

    outer_selectors = [
        "p.data.text-title-5",
        "p[class*='text-title']",
        "data.text-title-5",
        "data",
        "div[class*='price']",
        "span[class*='price']",
        "p[class*='price']"
    ]
    
    if prt:
        for sel in outer_selectors:
            tag = prt.select_one(sel)
            if tag and tag.text.strip():
                txt = tag.text.strip()
                if re.search(r'\d', txt):
                    return clean_price_formal(txt)


    inner_selectors = [
        "data.text-title-2",
        ".text-title-2",
        "data[class*='text-title']",
        "div.flex-1 div.flex.items-center.gap-1\\.5x",
        "div.flex-1 div.flex.items-center",
        "div[class*='price']",
        "span[class*='price']",
        "h3[class*='price']",
        "h2[class*='price']"
    ]
    
    if apart_soup:
        for sel in inner_selectors:
            tag = apart_soup.select_one(sel)
            if tag and tag.text.strip():
                txt = tag.text.strip()
                if re.search(r'\d', txt):
                    return clean_price_formal(txt)

        meta_tag = apart_soup.select_one(
            "meta[property='og:price:amount'], meta[name='price'], meta[property='product:price:amount']"
        )
        if meta_tag and meta_tag.get("content"):
            return clean_price_formal(meta_tag["content"])

        fallback_tag = apart_soup.find(
            lambda tag: tag.name in ['data', 'span', 'div', 'p', 'h2', 'h3', 'b', 'strong']
            and tag.string
            and any(curr in tag.string.upper() for curr in ['EGP', 'ج.م', 'جنيه', 'LE'])
            and re.search(r'\d', tag.string)
            and len(tag.string.strip()) < 40
        )
        if fallback_tag:
            return clean_price_formal(fallback_tag.string.strip())

    return "N/A"



def clean_price_formal(text):
    if not text or text == "N/A":
        return "N/A"
    
    raw = str(text).strip()
    
    is_million = bool(re.search(r"مليون|million|\bm\b", raw, re.IGNORECASE))
    is_thousand = bool(re.search(r"ألف|الف|thousand|\bk\b", raw, re.IGNORECASE))
    
    clean_str = re.sub(r"(?i)EGP|EGP/M²|ج\.م|جنيه|مصري|Installment|Available", "", raw)
    
    clean_str = clean_str.replace(",", "").strip()
    
    match = re.search(r"\d+(?:\.\d+)?", clean_str)
    if not match:
        return "N/A"
        
    val = float(match.group())
    
    if is_million:
        val *= 1_000_000
    elif is_thousand:
        val *= 1_000
        
    if val.is_integer():
        return f"{int(val):,}"
    else:
        return f"{val:,}"
    



async def main():
    headers_csv = [
        "type","address","area_sqm","bedrooms","bathroom","view","Year Built","price","Listing_ID","link"
                    ]

    with open("aqarmap5.csv", "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(headers_csv)
            try:
                async with async_playwright() as p:

                    browser=await p.chromium.launch(
                    headless=False,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--start-maximized",])
                    
                    context = await browser.new_context(
                        user_agent=get_random_user_agent(),
                        viewport={"width": 1920, "height": 1080},
                        locale="en-US",
                    )
                        
                    search_page = await context.new_page()
                    await stealth_async(search_page)

                    for page_num in range(0, 50):
                        current_url = f"https://aqarmap.com.eg/en/for-sale/villa/?page={page_num}"
                        print(f"\n--- Start scraping Page {page_num}: {current_url} ---")
                        print(f"Start scraping For {current_url}")
                        await search_page.goto(
                            current_url, wait_until="domcontentloaded", timeout=60000
                        )
                        await search_page.wait_for_timeout(3000)


                        for i in range(1, 8):
                            await search_page.evaluate(f"window.scrollTo(0, document.body.scrollHeight * {i/7});")
                            await asyncio.sleep(0.7)

                        html_content = await search_page.content()
                        soup = BeautifulSoup(html_content, "html.parser")
                        apartments=soup.select("li.list-none")
                        try:
                            for prt in apartments:
                                
                                property_type = "Villas"


                                
                                bedroom_tag=prt.select_one("div:has(>.bedroom-icon)+span")
                                bedroom=bedroom_tag.text.strip() if bedroom_tag else "N/A"
                                
                                bathroom_tag=prt.select_one("div:has(>.bathroom-icon)+span")
                                bathroom=bathroom_tag.text.strip() if bathroom_tag else "N/A"
                                
                                
                                size_tag=prt.select_one("div:has(>.size-icon)+span")
                                size=size_tag.text.strip() if size_tag else "N/A"
                                size = size.replace("م²", "").replace("م2", "").replace("متر مربع", "").replace("m²","").replace("M²","").strip()
                                
                                
                                
                                link_tag = prt.select_one("a.embla__slide")
                                if not link_tag or not link_tag.get("href"):
                                    continue
                                link = link_tag["href"]
                                full_link = urljoin(current_url, link).replace("/ar/", "/en/")

                                print(f"Start scraping For {full_link} in bage {page_num}")

                                address = "N/A"
                                
                                view = "Unknown"
                                Year_Built = "Unknown"
                                Listing_ID = "N/A"
                                apart = await context.new_page()
                                await stealth_async(apart) 
                                await apart.goto(full_link, wait_until="domcontentloaded", timeout=60000)
                                await apart.wait_for_timeout(3000)

                                apart_html = await apart.content()
                                apart_soup = BeautifulSoup(apart_html, "html.parser")

                                address_tag=apart_soup.select_one("p.text-body-2.truncated-text")
                                address=address_tag.text.strip().replace("م²", "m²").strip() if address_tag else "N/A"



                                price = extract_price_bulletproof(prt=prt, apart_soup=apart_soup)



                                if price == "N/A":
                                    continue



                                view_tag= "NA"
                                view_tag=apart_soup.find("h4",string="View")
                                if  view_tag:
                                    view= view_tag.find_next_sibling("span").text


                                Year_Built_tag= "NA"
                                Year_Built_tag=apart_soup.find("h4",string="Year Built")
                                if  Year_Built_tag:
                                    Year_Built= Year_Built_tag.find_next_sibling("span").text


                                Listing_ID_tag= "NA"
                                Listing_ID_tag=apart_soup.find("h4",string="Listing ID")
                                if  Listing_ID_tag:
                                    Listing_ID= Listing_ID_tag.find_next_sibling("span").text


                                writer.writerow([property_type,address,size,bedroom,bathroom,view,Year_Built,price,Listing_ID,full_link])
                                await apart.close()
                        except Exception as e :
                            print(f"error in link {full_link}")
            except Exception as e :
                print(f"error in bage {page_num}")


if __name__ == "__main__":
    asyncio.run(main())