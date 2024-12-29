from openai import OpenAI
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Initialize OpenAI client
api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    raise ValueError(
        "No OpenAI API key found. Make sure OPENAI_API_KEY is set in your .env file")
client = OpenAI(api_key=api_key)


def extract_number_from_response(gpt_response):
    """
    Uses GPT-3.5-turbo to extract the chosen number from a complex GPT response.
    Returns the number as an integer or 'false' if no valid number found.
    """
    try:
        message = f"""Extract ONLY the final chosen number from this GPT response. 
        Return ONLY the number, nothing else.
        If no clear number is chosen, return 'false'.

        GPT Response:
        {gpt_response}
        """

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": message}],
            temperature=0.1
        )

        extracted_answer = response.choices[0].message.content.strip().lower()
        print(f"Number extraction response: {extracted_answer}")

        # If the response is 'false', return 'false'
        if extracted_answer == 'false':
            return 'false'

        # Try to convert to integer
        try:
            number = int(extracted_answer)
            return number
        except ValueError:
            return 'false'

    except Exception as e:
        print(f"Error in number extraction: {e}")
        return 'false'
