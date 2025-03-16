from . import create_app, db

# Create application instance
app = create_app()

# Create database tables
with app.app_context():
    db.create_all()

# Run the application if this script is executed directly
if __name__ == '__main__':
    app.run(debug=True)