from openai import OpenAI
from dotenv import load_dotenv
import os


def truncate(text, length=30):
    """Truncate text to specified length"""
    return text[:length] + "..." if len(str(text)) > length else text


# Load environment variables
load_dotenv()

# Initialize OpenAI client
api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    raise ValueError(
        "No OpenAI API key found. Make sure OPENAI_API_KEY is set in your .env file")
client = OpenAI(api_key=api_key)

models = ["gpt-3.5-turbo", "gpt-4o-mini", "gpt-4o"]


def get_dropdown_suggestion(field_info, resume_text, attempt=1):
    """Get optimal partial search text for a dropdown field using GPT"""
    try:
        # Select model based on attempt number
        model = models[min(attempt - 1, len(models) - 1)]
        print(
            f"\nUsing model {model} for search term suggestion (attempt {attempt})")

        # Format the message to get a partial search term
        message = f"""Given a dropdown field in a job application and the candidate's resume, provide a PARTIAL search term that would efficiently find the best option.
        Return ONLY the shortest search term that would uniquely identify the best option, no explanation.
        
        For example:
        - If looking for "University of California, Davis" just return "davis"
        - If looking for "Yes" just return "y"
        - If looking for "Software Engineer" just return "soft"
        
        Field details:
        Label: {field_info.get('label', '')}
        
        Resume:
        {resume_text}
        """

        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": message}],
            temperature=0.1
        )

        answer = response.choices[0].message.content.strip()
        print(
            f"\nGPT suggests partial search term for {field_info['label']}: {answer}")
        return answer

    except Exception as e:
        print(f"Error getting GPT dropdown suggestion: {e}")
        return None


def get_best_option_number(new_elements, original_label, resume_text):
    """Get the best option number from the dropdown elements using GPT"""
    try:
        # Format the message to get the best option number with truncated text and class info
        elements_text = "\n".join([
            f"[{i}] Text: {truncate(el.get('text', ''), 30)}, Class: {truncate(el.get('class', ''), 30)}"
            for i, el in enumerate(new_elements)
        ])

        message = f"""Given these dropdown options and the candidate's resume, ONLY ONE of these elements is the actual dropdown option that should be clicked in order to answer the question/field.
        The others may be UI elements, labels, or other components. Find the single element that looks like a valid dropdown choice.
        Choose the most concise option if multiple options would be valid.

        Return ONLY the NUMBER of that one best option.
        If none of the options appear to directly answer or relate to the question/field, or if you're not highly confident that any option is a valid match, return exactly the word 'false' (no punctuation, no explanation). It's better to return false than to select an incorrect option.
        
        Question/Field: {truncate(original_label, 30)}
        
        Available elements:
        {elements_text}
        
        Resume:
        {resume_text}
        
        For any information not found in the resume, choose the best option that would best answer the question/field in a positive way.
        """

        print("\n=== GPT API Call ===")
        print(message)
        print("===================")

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": message}],
            temperature=0.1
        )

        answer = response.choices[0].message.content.strip().lower()
        print(f"\nGPT suggests option number or false: {answer}")

        # Check if the answer is 'false'
        if answer == 'false':
            return 'false'

        # Try to extract number
        try:
            # Remove all non-numeric characters and convert to int
            number = int(''.join(filter(str.isdigit, answer)))
            return number
        except ValueError:
            print("Could not extract valid number from GPT response")
            return 'false'

    except Exception as e:
        print(f"Error getting GPT option selection: {e}")
        return 'false'
