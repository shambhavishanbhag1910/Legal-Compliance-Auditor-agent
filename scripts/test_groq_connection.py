from openai import OpenAI

from app.config import get_settings


settings = get_settings()


print("Model:", settings.GROQ_MODEL)
print("Base URL:", settings.GROQ_BASE_URL)
print("API key loaded:", bool(settings.GROQ_API_KEY))


client = OpenAI(
    api_key=settings.GROQ_API_KEY,
    base_url=settings.GROQ_BASE_URL,
)


response = client.responses.create(
    model=settings.groq_model,
    input="Reply with exactly: GROQ CONNECTION OK",
)


print(response.output_text)