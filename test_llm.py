import ollama
response = ollama.generate(model="llama3", prompt="Привет, это тест. Скажи 'OK'.")
print(response['response'])
