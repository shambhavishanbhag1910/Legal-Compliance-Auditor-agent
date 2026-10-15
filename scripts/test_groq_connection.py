from openai import OpenAI

from app.config import get_settings


settings = get_settings()


print("Model:", settings.groq_model)
print("Base URL:", settings.groq_base_url)
print("API key loaded:", bool(settings.groq_api_key))


client = OpenAI(
    api_key=settings.groq_api_key,
    base_url=settings.groq_base_url,
)


response = client.responses.create(
    model=settings.groq_model,
    input="Reply with exactly: GROQ CONNECTION OK",
)


print(response.output_text)