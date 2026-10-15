class ProductRepository:
    def __init__(self, database):
        self.database = database

    def get_product(self, product_id):
        if product_id not in self.database:
            raise LookupError(product_id)
        return self.database[product_id]
