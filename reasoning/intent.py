import re
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class ReasoningResult:
    intent: Optional[str]
    slots: Dict[str, Any]


def extract_intent_and_slots(text: str) -> ReasoningResult:
    original = text.strip()
    text = original.lower()

    # Book flight
    if "book" in text and "flight" in text:
        slots = {}

        flight = re.search(r"\b(FL\d+)\b", original, re.I)
        passenger = re.search(r"\bfor\s+([A-Za-z ]+)$", original, re.I)

        if flight:
            slots["flight_id"] = flight.group(1).upper()

        if passenger:
            slots["passenger_name"] = passenger.group(1).strip()

        return ReasoningResult("book_flight", slots)

    # Update identity document
    if "update" in text and any(
        word in text for word in ["passport", "identity", "document"]
    ):
        slots = {}

        doc_type = re.search(
            r"\b(passport|license|licence|aadhaar|id)\b",
            original,
            re.I,
        )

        doc_number = re.search(
            r"\b(?=[A-Z0-9]*[A-Z])(?=[A-Z0-9]*\d)[A-Z0-9]{5,}\b",
            original,
            re.I,
        )

        if doc_type:
            slots["doc_type"] = doc_type.group(1).lower()

        if doc_number:
            slots["doc_number"] = doc_number.group(0)

        return ReasoningResult("update_identity_doc", slots)

    # Card benefits
    if "benefit" in text and "card" in text:
        slots = {}

        card = re.search(
            r"\b(visa|mastercard|amex|american express)\b",
            original,
            re.I,
        )

        if card:
            slots["card_type"] = card.group(1)

        return ReasoningResult("get_card_benefits", slots)

    # Exchange rate
    if "exchange rate" in text:
        slots = {}

        amount = re.search(
            r"\b(\d+(?:\.\d+)?)\s+([A-Za-z]{3})\s+to\s+([A-Za-z]{3})",
            original,
            re.I,
        )

        if amount:
            slots["amount"] = float(amount.group(1))
            slots["from_currency"] = amount.group(2).upper()
            slots["to_currency"] = amount.group(3).upper()

        return ReasoningResult("get_exchange_rate", slots)

    # Modify autopay
    if "autopay" in text or "auto pay" in text:
        slots = {}

        bill = re.search(
            r"\b(?:my|the)?\s*(electricity|water|internet|phone|rent|credit card)\b",
            original,
            re.I,
        )

        account = re.search(
            r"\b(?:account|source account)\s+([A-Za-z0-9_-]+)",
            original,
            re.I,
        )

        if bill:
            slots["bill_type"] = bill.group(1).lower()

        if account:
            slots["source_account"] = account.group(1)

        return ReasoningResult("modify_autopay", slots)

    # Calculate commute
    if "commute" in text:
        slots = {}

        route = re.search(
            r"from\s+(.+?)\s+to\s+(.+?)(?:\s+by\s+(\w+))?$",
            original,
            re.I,
        )

        if route:
            slots["origin_address"] = route.group(1).strip()
            slots["destination_address"] = route.group(2).strip()

            if route.group(3):
                slots["mode"] = route.group(3).lower()

        return ReasoningResult("calculate_commute", slots)

    # Update search filter
    if "filter" in text and ("update" in text or "change" in text):
        slots = {}

        filter_match = re.search(
            r"\b(price|location|city|bedrooms|budget)\s+filter\b",
            original,
            re.I,
        )

        value = re.search(
            r"\b(?:to|as)\s+([₹$]?\d+(?:\.\d+)?)",
            original,
            re.I,
        )

        if filter_match:
            slots["filter_name"] = filter_match.group(1).lower()

        if value:
            raw_value = value.group(1).replace(",", "").replace("₹", "").replace("$", "")
            slots["value"] = float(raw_value)

        return ReasoningResult("update_search_filter", slots)

    # Search apartments
    if "apartment" in text:
        slots = {}

        city = re.search(
            r"\bin\s+([a-zA-Z ]+?)(?:\s+under|\s+below|\s*$)",
            original,
            re.I,
        )

        bedrooms = re.search(
            r"\b(\d+)\s*(?:bedroom|bedrooms|bhk)\b",
            original,
            re.I,
        )

        price = re.search(
            r"(?:under|below)\s*[₹$]?\s*([\d,]+)",
            original,
            re.I,
        )

        if city:
            slots["city"] = city.group(1).strip()

        if bedrooms:
            slots["bedrooms"] = int(bedrooms.group(1))

        if price:
            slots["max_price"] = float(
                price.group(1).replace(",", "")
            )

        return ReasoningResult("search_apartments", slots)

    # Track order
    if "track" in text and "order" in text:
        slots = {}

        order = re.search(
            r"\b(?:order|order id)\s*[:#-]?\s*([A-Za-z0-9_-]+)",
            original,
            re.I,
        )

        if order:
            slots["order_id"] = order.group(1)

        return ReasoningResult("track_order", slots)

    # Search products
    if "search" in text and "product" in text:
        slots = {}

        price = re.search(
            r"(?:under|below)\s*[₹$]?\s*([\d,]+)",
            original,
            re.I,
        )

        query = re.search(
            r"products?\s+(?:for|called|like)\s+(.+?)(?:\s+under|\s+below|$)",
            original,
            re.I,
        )

        if query:
            slots["query"] = query.group(1).strip()

        if price:
            slots["max_price"] = float(
                price.group(1).replace(",", "")
            )

        return ReasoningResult("search_products", slots)

    # Add to cart
    if "add" in text and "cart" in text:
        slots = {}

        product = re.search(
            r"\b(?:product|item)\s+([A-Za-z0-9_-]+)",
            original,
            re.I,
        )

        quantity = re.search(
            r"\b(\d+)\s*(?:items?|units?|quantity)?\b",
            original,
            re.I,
        )

        if product:
            slots["product_id"] = product.group(1)

        if quantity:
            slots["quantity"] = int(quantity.group(1))

        return ReasoningResult("add_to_cart", slots)

    # Search flights
    if "flight" in text:
        slots = {}

        destination = re.search(
            r"(?:to|for)\s+([a-zA-Z ]+?)(?:\s+on|\s*$)",
            original,
            re.I,
        )

        date = re.search(
            r"\bon\s+(.+)$",
            original,
            re.I,
        )

        if destination:
            slots["destination"] = destination.group(1).strip()

        if date:
            slots["date"] = date.group(1).strip()

        return ReasoningResult("search_flights", slots)

    return ReasoningResult(None, {})