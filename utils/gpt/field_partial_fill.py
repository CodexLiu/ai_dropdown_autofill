from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    raise ValueError(
        "No OpenAI API key found. Make sure OPENAI_API_KEY is set in your .env file")
client = OpenAI(api_key=api_key)


def generate_search_term(sample_elements, field_label):
    """
    Generate a partial search term based on sample dropdown options.

    Args:
        sample_elements: List of first few elements to model the response after
        field_label: The label/question of the field being filled

    Returns:
        str: A partial search term (max 5 chars) or None if can't generate
    """
    try:
        # Read resume text from info.txt for context
        try:
            with open('info.txt', 'r') as f:
                resume_text = f.read()
        except Exception as e:
            print(f"Error reading info.txt: {e}")
            resume_text = ""

        # Format sample elements for GPT prompt
        elements_text = "\n".join([
            f"[{i}] Text: {el.get('text', '')}, Class: {el.get('class', '')}"
            for i, el in enumerate(sample_elements)
        ])

        message = f"""Given these sample dropdown options and the field label, generate a PARTIAL search term that would help filter and find the best option.
        The search term should be at most 5 characters long and be the most identifying part of the desired option from the resume.
        
        Return ONLY the search term, no explanation. The term should be lowercase and not include any spaces.
        
        Examples of good partial search terms:
        - For "Software Engineer" -> "soft"
        - For "University of California, Berkeley" -> "berk"
        - For "Bachelor's Degree" -> "bach"
        - For "United States" -> "unit"
        - For "Yes" -> "y"
        
        Field Label: {field_label}
        
        Sample Options:
        {elements_text}
        
        Resume Context:
        {resume_text}
        """

        # Make API call
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": message}],
            temperature=0.1
        )

        answer = response.choices[0].message.content.strip().lower()

        answer = answer.strip('"\'')
        return answer

    except Exception as e:
        print(f"Error generating search term: {e}")
        return None
