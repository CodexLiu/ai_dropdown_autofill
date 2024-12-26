from openai import OpenAI
from dotenv import load_dotenv
import os
import time

# Load environment variables
load_dotenv()

# Initialize OpenAI client
api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    raise ValueError(
        "No OpenAI API key found. Make sure OPENAI_API_KEY is set in your .env file")
client = OpenAI(api_key=api_key)


def get_text_field_value(field_info, resume_text):
    """Get appropriate value for a text field using GPT"""
    try:
        print(f"\nGetting value for field: {field_info['label']}")

        # Format the message to get appropriate text field value
        message = f"""Given a text field in a job application and the candidate's resume, provide an appropriate value to fill in the field.
        Return ONLY the value to fill in, no explanation.
        
        Field details:
        Label: {field_info['label']}
        Type: {field_info['type']}
        Required: {field_info['isRequired']}
        
        Resume:
        {resume_text}
        
        For any information not found in the resume, provide a reasonable professional response that would be appropriate for a job application.
        """

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": message}],
            temperature=0.1
        )

        answer = response.choices[0].message.content.strip()
        print(f"GPT suggests value: {answer}")
        return answer

    except Exception as e:
        print(f"Error getting GPT text field value: {e}")
        return None


def fill_text_field(page, element):
    """Fill a text field with GPT-suggested value"""
    try:
        # Load resume text
        with open('info.txt', 'r') as file:
            resume_text = file.read()

        # Get value from GPT
        value = get_text_field_value(element, resume_text)
        if not value:
            print("Failed to get value from GPT")
            return False

        # Click the field
        clicked = False
        if element['attributes']['id']:
            try:
                page.click(f"#{element['attributes']['id']}")
                clicked = True
            except:
                pass

        if not clicked and element['xpath']:
            try:
                page.click(f"xpath={element['xpath']}")
                clicked = True
            except:
                pass

        if clicked:
            # Clear existing value
            page.keyboard.press("Control+a")
            page.keyboard.press("Backspace")
            time.sleep(0.1)

            # Type new value
            page.keyboard.type(value)
            time.sleep(0.1)

            print(f"Filled field '{element['label']}' with: {value}")
            return True

        print("Failed to click text field")
        return False

    except Exception as e:
        print(f"Error filling text field: {e}")
        return False
