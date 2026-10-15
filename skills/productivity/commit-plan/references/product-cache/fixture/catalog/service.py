class ProductService:
    def __init__(self, repository):
        self.repository = repository

    def get_product(self, product_id):
        return self.repository.get_product(product_id)
