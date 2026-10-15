import unittest
from catalog.api import get_product
from catalog.repository import ProductRepository
from catalog.service import ProductService

class LookupTests(unittest.TestCase):
    def setUp(self):
        self.product = {"id": "p1", "name": "Notebook", "price": 12}
        self.service = ProductService(ProductRepository({"p1": self.product}))

    def test_product_contract(self):
        self.assertEqual(get_product(self.service, "p1"), (200, self.product))

    def test_missing_product_contract(self):
        self.assertEqual(get_product(self.service, "missing"), (404, {"error": "Product not found"}))
