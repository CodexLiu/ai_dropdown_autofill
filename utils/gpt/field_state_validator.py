from openai import OpenAI
from dotenv import load_dotenv
import os
import base64
from PIL import Image
from io import BytesIO

# Load environment variables
load_dotenv()

# Initialize OpenAI client
api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    raise ValueError(
        "No OpenAI API key found. Make sure OPENAI_API_KEY is set in your .env file")
client = OpenAI(api_key=api_key)


def encode_image_to_base64(image_path):
    """Convert an image file to base64 string"""
    try:
        with Image.open(image_path) as image:
            buffered = BytesIO()
            image.save(buffered, format="PNG")
            return base64.b64encode(buffered.getvalue()).decode('utf-8')
    except Exception as e:
        print(f"Error encoding image: {e}")
        return None


def validate_field_state(screenshot_path, field_info):
    """
    Validate if a field is empty or filled using GPT-4 Vision.

    Args:
        screenshot_path: Path to the screenshot of the current page state
        field_info: Dictionary containing field information (label, type, etc.)

    Returns:
        bool: True if field is filled, False if empty
    """
    try:
        # Encode the screenshot
        base64_image = encode_image_to_base64(screenshot_path)
        if not base64_image:
            print("Failed to encode screenshot")
            return False

        # Prepare the message for GPT-4 Vision
        message = f"""Analyze this screenshot of a form and determine if the specified field is empty or filled.
        
        Field Details:
        - Label: {field_info['label']}
        - Type: {field_info['type']}
        - ID: {field_info['attributes'].get('id', 'N/A')}
        - Class: {field_info['attributes'].get('class', 'N/A')}
        
        Return ONLY 'true' if the field is filled with a value, or 'false' if it appears empty.
        A field is considered filled if it shows a selected value, contains text, or displays a chosen option.
        A field is considered empty if it shows placeholder text, default text like 'Select...', or no value at all.
        """

        # Make API call to GPT-4 Vision
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": message},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=10,
            temperature=0.1
        )

        answer = response.choices[0].message.content.strip().lower()
        return answer == 'true'

    except Exception as e:
        print(f"Error validating field state: {e}")
        return False
