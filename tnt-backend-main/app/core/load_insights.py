LOW_LOAD_MAX_UTILIZATION = 0.5
MEDIUM_LOAD_MAX_UTILIZATION = 0.8
MIN_EXPRESS_REMAINING_ORDERS = 2


def get_load_label(current_orders: int, max_orders: int) -> str:
    if max_orders <= 0:
        return "LOW"

    utilization = current_orders / max_orders
    if utilization < LOW_LOAD_MAX_UTILIZATION:
        return "LOW"
    if utilization < MEDIUM_LOAD_MAX_UTILIZATION:
        return "MEDIUM"
    return "HIGH"


def is_express_pickup_eligible(current_orders: int, max_orders: int) -> bool:
    if max_orders <= 0:
        return False

    remaining_orders = max_orders - current_orders
    if remaining_orders < MIN_EXPRESS_REMAINING_ORDERS:
        return False

    return get_load_label(current_orders, max_orders) in {"LOW", "MEDIUM"}