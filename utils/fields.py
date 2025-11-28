from django.db import models
from utils.encryption import AESCipher

class EncryptedCharField(models.CharField):
    # Encrypt data with the owning user's AES key

    def get_prep_value(self, value):
        # encryption happens before saving
        if value is None or not hasattr(self, 'user_key'):
            return value
        return AESCipher(self.user_key).encrypt(value)

    def from_db_value(self, value, expression, connection):
        if value is None or not hasattr(self, 'user_key'):
            return value
        return AESCipher(self.user_key).decrypt(value)
