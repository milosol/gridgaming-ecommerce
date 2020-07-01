import braintree
from decouple import config

gateway = braintree.BraintreeGateway(
    braintree.Configuration(
        environment=config("BRAINTREE_ENVIRONMENT"),
        merchant_id=config("BRAINTREE_MERCHANT_ID"),
        public_key=config("BRAINTREE_PUBLIC_KEY"),
        private_key=config("BRAINTREE_PRIVATE_KEY")
    )
)

def generate_client_token():
    return gateway.client_token.generate()

def transact(options):
    return gateway.transaction.sale(options)

def find_transaction(id):
    return gateway.transaction.find(id)