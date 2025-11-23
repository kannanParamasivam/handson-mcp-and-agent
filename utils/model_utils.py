async def test_model_connection(model):
    try:
        # Test the model with a simple prompt
        response = await model.ainvoke("Say hello in a creative way!")
        print("\nModel connection test successful!")
        print("Response:", response)
        return True
    except Exception as e:
        print("\nError connecting to model:", str(e))
        print("\nPlease ensure the model is available and properly configured.")
        print("You can start Ollama with: ollama serve")
        print("And download a model with: ollama pull llama2")
        return False



    