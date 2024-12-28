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
        Other elements might be UI components, labels, or irrelevant options - find the one valid choice.
        If multiple options could work, choose the most concise one.

        Return ONLY the NUMBER of the best option.
        
        Question/Field: {field_label}
        
        Available elements:
        {elements_text}
        
        Resume:
        {resume_text}
        
        For fields where the information isn't in the resume but options are relevant, select the option that best answers the question in the most ideal fashion possible to obtain employment. However for easily verifyable information that cannot be fabricated such as asking if you have worked at a company, select the option that is most likely to be true given the user's resume.
        """

        # Make API call
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": message}],
            temperature=0.1
        )

        answer = response.choices[0].message.content.strip().lower()

        # Return 'false' if that's the explicit response
        if answer == 'false':
            return 'false'

        # Try to extract and validate the number
        try:
            number = int(''.join(filter(str.isdigit, answer)))
            if 0 <= number < len(elements):
                return number
            return 'false'
        except ValueError:
            return 'false'

    except Exception as e:
        print(f"Error in option selection: {e}")
        return 'false'
