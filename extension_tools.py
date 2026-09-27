"""
Extension use case: in-car destination change.
New tool outside FDB-v3's 12 domains, wired through the same
orchestrator, ledger, and cancellation logic already built tonight.
"""

def search_route(destination: str, origin: str = "current_location", **kwargs) -> dict:
    return {
        "status": "success",
        "route_id": f"ROUTE_{destination.upper()[:4]}",
        "destination": destination,
        "origin": origin,
        "eta_minutes": 24,
    }


def update_destination(route_id: str, new_destination: str, **kwargs) -> dict:
    return {
        "status": "success",
        "route_id": route_id,
        "updated_destination": new_destination,
        "eta_minutes": 31,
    }