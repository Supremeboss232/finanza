import uvicorn

if __name__ == "__main__":
    # Run the application from the 'main' module, ensuring it's accessible
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)