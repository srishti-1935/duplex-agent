TOOLS = {
    "search_flights": {
        "required": ["destination", "date"],
        "optional": []
    },

    "book_flight": {
        "required": ["passenger_name"],
        "optional": ["flight_id"]
    },

    "update_identity_doc": {
        "required": ["doc_type", "doc_number"],
        "optional": []
    },

    "get_card_benefits": {
        "required": ["card_type"],
        "optional": []
    },

    "get_exchange_rate": {
        "required": ["amount", "from_currency", "to_currency"],
        "optional": []
    },

    "modify_autopay": {
        "required": ["bill_type", "source_account"],
        "optional": []
    },

    "search_apartments": {
        "required": ["city", "bedrooms", "max_price"],
        "optional": []
    },

    "calculate_commute": {
        "required": ["origin_address", "destination_address"],
        "optional": ["mode"]
    },

    "update_search_filter": {
        "required": ["filter_name", "value"],
        "optional": []
    },

    "track_order": {
        "required": ["order_id"],
        "optional": []
    },

    "search_products": {
        "required": ["query"],
        "optional": ["max_price"]
    },

    "add_to_cart": {
        "required": ["product_id", "quantity"],
        "optional": []
    }
}