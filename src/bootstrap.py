import os
from dotenv import load_dotenv
# Traverse up from src/ to the project root where .env lives
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(root_dir, '.env')
load_dotenv(env_path)