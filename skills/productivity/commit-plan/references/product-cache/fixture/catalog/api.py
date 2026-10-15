def get_product(service, product_id):
    try:
        return 200, service.get_product(product_id)
    except LookupError:
        return 404, {"error": "Product not found"}
