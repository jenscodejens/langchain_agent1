import os

from dotenv import load_dotenv
load_dotenv()

from langchain_xai import ChatXAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
from langchain_core.documents import Document

doc1 = Document(
    page_content="The AWESOME Sink is a special building that produces  FICSIT Coupons for use in the AWESOME Shop by destroying items inserted into it and converting them into points based on their value or complexity. These points are used to print the aforementioned Coupons, with each successive Coupon requiring more points according to a mathematical formula. In addition to normal items, Alien DNA Capsules can also be sunk and their AWESOME Points are counted separately. The Sink can consume as many parts as the connected conveyor can supply, therefore its maximum capacity is 1,200/min using a Conveyor Belt Mk.6 or Conveyor Lift Mk.6. Multiple Sinks can be constructed. Accumulated points will be shared between all Sinks, and Coupons can be printed from any of them. If all Sinks are deconstructed, the amount of points and accumulated Coupons is not lost. AWESOME is an acronym, which stands for \"Anti-Waste Effort for Stress-Testing of Materials on Exoplanets\"."
)

# Define a Pydantic model for the expected JSON output
class Answer(BaseModel):
    answer: str = Field(description="The answer to the user's question")

# Create the parser with the model
parser = JsonOutputParser(pydantic_object=Answer)

llm_model = ChatXAI(
    model="grok-4-1-fast-reasoning",
    temperature=0.3,
    verbose=False,
    timeout=25
    # max_tokens=None,
    # timeout=None,
    # max_retries=2,
    # other params...
)

# Answer the users's question is the program telling the LLM its task (the 'answer' in the class is just to prep the LLM for the expected content(JSON))
prompt = ChatPromptTemplate.from_template("""
Answer the user's question:
Context: {context}
Question: {human_input}
{format_instructions}
""")

# Function to generate the answer
def generate_answer(question: str) -> str:
    chain = prompt | llm_model | parser
    try:
        result = chain.invoke({
            "human_input": question,
            "context": doc1.page_content,
            "format_instructions": parser.get_format_instructions()
        })
        return result["answer"]
    except Exception as e:
        return f"Error generating answer: {str(e)}"

# Example usage (you can call this function elsewhere)
if __name__ == "__main__":
    answer = generate_answer("What is Awesome Sink?")
    print(answer)  