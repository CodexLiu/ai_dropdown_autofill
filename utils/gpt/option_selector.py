from openai import OpenAI
from dotenv import load_dotenv
import os
from utils.gpt.response_parser import extract_number_from_response


# Load environment variables
load_dotenv()

# Initialize OpenAI client
api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    raise ValueError(
        "No OpenAI API key found. Make sure OPENAI_API_KEY is set in your .env file")
client = OpenAI(api_key=api_key)


def select_best_option(elements, field_label, resume_text=None):
    try:
        # Read resume text from info.txt
        try:
            with open('info.txt', 'r') as f:
                resume_text = f.read()
        except Exception as e:
            print(f"Error reading info.txt: {e}")
            return 'false'

        # Format elements for GPT prompt
        elements_text = "\n".join([
            f"[{i}] Text: {el.get('text', '')}, Class: {el.get('class', '')}"
            for i, el in enumerate(elements)
        ])

        message = f"""Given these clickable elements and the candidate's resume, identify the SINGLE BEST element that should be clicked to answer the question/field.
        For education, work history, and certifications:
        - If an exact match exists, select that option
        - If no exact match exists but a closely related option is available, select the most relevant one
        - If no related options exist, select 'false'
        Other elements might be UI components, labels, or irrelevant options - find the one valid choice.
        If multiple options could work, choose the most specific and accurate one based on the resume.

        Return ONLY the NUMBER of the best option.
        
        Question/Field: {field_label}
        
        Available elements:
        {elements_text}
        
        Resume:
        {resume_text}
        
        IMPORTANT: 
        1. For education and credentials, select exact matches when available, otherwise choose the most relevant related option
        2. For fields where information isn't directly stated in the resume but options are available, select the most advantageous option
        3. Don't fabricate verifiable facts that are verifiable by a company's internal logs ie working at that company before or being a part of that company
        """

        # Make API call
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": message}],
            temperature=0.1
        )

        answer = response.choices[0].message.content.strip().lower()
        print(f"GPT elements: {elements_text}")
        print("="*100)
        print(f"Raw GPT output: {answer}")

        # Use the new parser to extract the number
        number = extract_number_from_response(answer)

        # If we got a number back, validate it
        if number != 'false':
            if 0 <= number < len(elements):
                print(f"Valid index found: {number}")
                return number
            else:
                print(
                    f"Number {number} outside valid range [0, {len(elements)-1}]")
                return 'false'

        return 'false'

    except Exception as e:
        print(f"Critical error in option selection: {e}")
        return 'false'
