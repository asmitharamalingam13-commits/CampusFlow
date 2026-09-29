from app import create_app

# Create Flask application
app = create_app()


# Start the server
if __name__ == "__main__":
    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )