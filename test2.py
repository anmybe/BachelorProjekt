import google.generativeai as genai
genai.configure(api_key="AIzaSyCoTjmHS7ugwRiVG4j_fvuBG8HpdS6QG8Y")

for m in genai.list_models():
    print(m.name)
