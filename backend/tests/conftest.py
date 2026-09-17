import sys
import os

os.environ["JWT_SECRET_KEY"] = "test_jwt_secret_key_super_secret_for_dev_123456789"
os.environ["DEV_SEED_EMAIL"] = "dev@businesshub.dev"
os.environ["DEV_SEED_PASSWORD"] = "DevSeedPass123!"
os.environ["DEV_SEED_NAME"] = "Development Owner"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))