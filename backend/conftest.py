import sys
import os

os.environ["JWT_SECRET_KEY"] = "test_jwt_secret_key_super_secret_for_dev_123456789"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))