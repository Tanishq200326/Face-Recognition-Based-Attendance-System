from app import app  # Import Flask app
from utils import train_model

# Create an application context
with app.app_context():
    train_model()
    print("Model retrained successfully!")

