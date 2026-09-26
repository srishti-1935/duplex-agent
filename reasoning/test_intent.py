from reasoning.intent import extract_intent_and_slots


def test_search_flights():
    result = extract_intent_and_slots("Find flights to Delhi")
    assert result.intent == "search_flights"
    assert result.slots["destination"] == "Delhi"


def test_search_flights_with_date():
    result = extract_intent_and_slots(
        "Find flights to Delhi on 20 October"
    )
    assert result.intent == "search_flights"
    assert result.slots["destination"] == "Delhi"
    assert result.slots["date"] == "20 October"


def test_search_apartments():
    result = extract_intent_and_slots(
        "Find apartments in Chennai under 30000"
    )
    assert result.intent == "search_apartments"
    assert result.slots["city"] == "Chennai"
    assert result.slots["max_price"] == 30000.0


def test_apartment_bedrooms():
    result = extract_intent_and_slots(
        "Find 2 bedroom apartments in Chennai under 30000"
    )
    assert result.intent == "search_apartments"
    assert result.slots["city"] == "Chennai"
    assert result.slots["bedrooms"] == 2
    assert result.slots["max_price"] == 30000.0


def test_book_flight():
    result = extract_intent_and_slots(
        "Book flight FL456 for Palak"
    )
    assert result.intent == "book_flight"
    assert result.slots["flight_id"] == "FL456"
    assert result.slots["passenger_name"] == "Palak"


def test_update_identity_doc():
    result = extract_intent_and_slots(
        "Update my passport document ABC123"
    )
    assert result.intent == "update_identity_doc"
    assert result.slots["doc_type"] == "passport"
    assert result.slots["doc_number"] == "ABC123"


def test_card_benefits():
    result = extract_intent_and_slots(
        "What are the benefits of my Visa card?"
    )
    assert result.intent == "get_card_benefits"
    assert result.slots["card_type"] == "Visa"


def test_exchange_rate():
    result = extract_intent_and_slots(
        "What is the exchange rate for 100 USD to EUR?"
    )
    assert result.intent == "get_exchange_rate"
    assert result.slots["amount"] == 100.0
    assert result.slots["from_currency"] == "USD"
    assert result.slots["to_currency"] == "EUR"


def test_modify_autopay():
    result = extract_intent_and_slots(
        "Change my electricity autopay to account ACC123"
    )
    assert result.intent == "modify_autopay"
    assert result.slots["bill_type"] == "electricity"
    assert result.slots["source_account"] == "ACC123"


def test_calculate_commute():
    result = extract_intent_and_slots(
        "Calculate commute from SRM Chennai to Chennai Airport"
    )
    assert result.intent == "calculate_commute"
    assert result.slots["origin_address"] == "SRM Chennai"
    assert result.slots["destination_address"] == "Chennai Airport"


def test_update_search_filter():
    result = extract_intent_and_slots(
        "Update the price filter to 25000"
    )
    assert result.intent == "update_search_filter"
    assert result.slots["filter_name"] == "price"
    assert result.slots["value"] == 25000.0


def test_track_order():
    result = extract_intent_and_slots(
        "Track order ORD123"
    )
    assert result.intent == "track_order"
    assert result.slots["order_id"] == "ORD123"


def test_search_products():
    result = extract_intent_and_slots(
        "Search products for headphones under 5000"
    )
    assert result.intent == "search_products"
    assert result.slots["query"] == "headphones"
    assert result.slots["max_price"] == 5000.0


def test_add_to_cart():
    result = extract_intent_and_slots(
        "Add product PROD123 quantity 2 to cart"
    )
    assert result.intent == "add_to_cart"
    assert result.slots["product_id"] == "PROD123"
    assert result.slots["quantity"] == 2


def test_unknown_request():
    result = extract_intent_and_slots("Tell me a joke")
    assert result.intent is None