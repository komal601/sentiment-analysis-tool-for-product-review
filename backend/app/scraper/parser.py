import hashlib
import re
from datetime import datetime
from bs4 import BeautifulSoup

from app.schemas import RawReview


def _normalize_date(raw_date: str) -> str:
    """Parse various e-commerce date formats into YYYY-MM-DD."""
    if not raw_date:
        return "2026-01-01"

    raw_clean = raw_date.strip()

    # Look for "Reviewed in India on 14 August 2026"
    match = re.search(r"on\s+(\d{1,2}\s+[A-Za-z]+\s+\d{4})", raw_clean, re.IGNORECASE)
    if match:
        clean_str = match.group(1)
        for fmt in ("%d %B %Y", "%d %b %Y"):
            try:
                return datetime.strptime(clean_str, fmt).strftime("%Y-%m-%d")
            except ValueError:
                pass

    # Look for "12 Aug, 2026" or "12 August 2026"
    match = re.search(r"(\d{1,2})\s+([A-Za-z]+),?\s+(\d{4})", raw_clean)
    if match:
        day, month, year = match.groups()
        for fmt in ("%d %b %Y", "%d %B %Y"):
            try:
                return datetime.strptime(f"{day} {month} {year}", fmt).strftime("%Y-%m-%d")
            except ValueError:
                pass

    # Look for month and year only "Aug, 2026"
    match = re.search(r"([A-Za-z]+),?\s+(\d{4})", raw_clean)
    if match:
        month, year = match.groups()
        for fmt in ("%b %Y", "%B %Y"):
            try:
                return datetime.strptime(f"01 {month} {year}", f"%d {fmt}").strftime("%Y-%m-%d")
            except ValueError:
                pass

    return raw_clean


def _extract_helpful_votes(text: str) -> int:
    """Extract integer count of helpful votes from string."""
    if not text:
        return 0
    text_lower = text.lower().strip()
    if "one person" in text_lower:
        return 1
    match = re.search(r"(\d[\d,]*)", text_lower)
    if match:
        return int(match.group(1).replace(",", ""))
    return 0


def parse_amazon_html(html: str, product_query: str = "realme buds t310") -> list[RawReview]:
    """Extract RawReview list from Amazon HTML string."""
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    review_elements = soup.find_all(attrs={"data-hook": "review"})
    reviews: list[RawReview] = []

    for idx, el in enumerate(review_elements, start=1):
        # Review ID
        raw_id = el.get("id") or ""
        if raw_id.startswith("customer_review-"):
            review_id = f"amz_{raw_id.replace('customer_review-', '')}"
        elif raw_id:
            review_id = f"amz_{raw_id}"
        else:
            review_id = f"amz_rev_{idx}"

        # Reviewer Name
        name_el = el.find(class_="a-profile-name")
        reviewer_name = name_el.get_text(strip=True) if name_el else "Amazon Customer"

        # Star Rating
        rating = 5
        rating_el = el.find(attrs={"data-hook": "review-star-rating"})
        if not rating_el:
            rating_el = el.find(class_=re.compile(r"a-star-\d"))
        if rating_el:
            rating_text = rating_el.get_text(strip=True)
            match = re.search(r"(\d(?:\.\d)?)", rating_text)
            if match:
                rating = max(1, min(5, int(float(match.group(1)))))
            else:
                for cls in rating_el.get("class", []):
                    star_match = re.search(r"a-star-(\d)", cls)
                    if star_match:
                        rating = int(star_match.group(1))
                        break

        # Review Title
        title_el = el.find(attrs={"data-hook": "review-title"})
        title = None
        if title_el:
            # Often contains a child span or direct text
            span_in_title = title_el.find("span")
            title = span_in_title.get_text(strip=True) if span_in_title else title_el.get_text(strip=True)

        # Review Body
        body_el = el.find(attrs={"data-hook": "review-body"})
        if not body_el:
            body_el = el.find(class_="review-text-content")
        text = ""
        if body_el:
            span_in_body = body_el.find("span")
            text = span_in_body.get_text(strip=True) if span_in_body else body_el.get_text(strip=True)

        # Review Date
        date_el = el.find(attrs={"data-hook": "review-date"})
        raw_date = date_el.get_text(strip=True) if date_el else ""
        review_date = _normalize_date(raw_date)

        # Verified Purchase Badge
        badge_el = el.find(attrs={"data-hook": "avp-badge"})
        verified = bool(badge_el and "verified purchase" in badge_el.get_text(strip=True).lower())

        # Helpful Votes
        helpful_el = el.find(attrs={"data-hook": "helpful-vote-statement"})
        helpful_votes = _extract_helpful_votes(helpful_el.get_text(strip=True)) if helpful_el else 0

        reviews.append(
            RawReview(
                review_id=review_id,
                platform="amazon",
                product_query=product_query,
                reviewer_name=reviewer_name,
                rating=rating,
                title=title,
                text=text,
                review_date=review_date,
                verified_purchase=verified,
                helpful_votes=helpful_votes,
            )
        )

    return reviews


def parse_flipkart_html(html: str, product_query: str = "realme buds t310") -> list[RawReview]:
    """Extract RawReview list from Flipkart HTML string."""
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    review_elements = soup.find_all(class_=re.compile(r"(_2wzgFH|EPCmJX|cPHDOP)"))
    # If cPHDOP container was matched, pick internal _2wzgFH blocks if present to avoid duplication
    filtered_elements = []
    for el in review_elements:
        if "_2wzgFH" in el.get("class", []):
            filtered_elements.append(el)
        elif "cPHDOP" in el.get("class", []) and not el.find(class_="_2wzgFH"):
            filtered_elements.append(el)

    if not filtered_elements:
        filtered_elements = review_elements

    reviews: list[RawReview] = []

    for idx, el in enumerate(filtered_elements, start=1):
        # Rating
        rating = 5
        rating_el = el.find(class_=re.compile(r"(_3LWZlK|XJA2_D)"))
        if rating_el:
            match = re.search(r"(\d)", rating_el.get_text(strip=True))
            if match:
                rating = max(1, min(5, int(match.group(1))))

        # Title
        title_el = el.find(class_=re.compile(r"(_2-N8zT|z9E0IG)"))
        title = title_el.get_text(strip=True) if title_el else None

        # Text Body
        body_el = el.find(class_=re.compile(r"(t-ZTKy|ZmyHeo)"))
        text = ""
        if body_el:
            text = body_el.get_text(" ", strip=True)
            # Remove "READ MORE" trailing button text from Flipkart cards
            text = re.sub(r"\s*READ MORE\s*$", "", text, flags=re.IGNORECASE).strip()

        # If empty text and no title, skip element (might not be an actual review block)
        if not text and not title:
            continue

        # Reviewer Name and Date
        author_els = el.find_all(class_=re.compile(r"(_2sc7ZR|_2NsDsF)"))
        reviewer_name = "Flipkart Customer"
        raw_date = ""
        if author_els:
            reviewer_name = author_els[0].get_text(strip=True)
            if len(author_els) > 1:
                raw_date = author_els[-1].get_text(strip=True)

        review_date = _normalize_date(raw_date)

        # Verified Purchase / Certified Buyer
        certified_el = el.find(string=re.compile(r"Certified Buyer", re.IGNORECASE))
        verified = bool(certified_el)

        # Helpful / Upvotes
        helpful_el = el.find(class_=re.compile(r"(_23vquh|tlQjTr)"))
        if not helpful_el:
            helpful_el = el.find(class_=re.compile(r"(_1LmwT9|pkR401)"))
        helpful_votes = _extract_helpful_votes(helpful_el.get_text(strip=True)) if helpful_el else 0

        # Review ID
        unique_hash = hashlib.md5(f"{reviewer_name}_{review_date}_{text[:30]}".encode()).hexdigest()[:8]
        review_id = f"fk_{unique_hash}_{idx}"

        reviews.append(
            RawReview(
                review_id=review_id,
                platform="flipkart",
                product_query=product_query,
                reviewer_name=reviewer_name,
                rating=rating,
                title=title,
                text=text,
                review_date=review_date,
                verified_purchase=verified,
                helpful_votes=helpful_votes,
            )
        )

    return reviews
