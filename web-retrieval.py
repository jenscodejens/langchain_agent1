import os

from dotenv import load_dotenv
load_dotenv()

from langchain_xai import ChatXAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
from langchain_community.document_loaders import WebBaseLoader

def get_documents_From_Web(url):
    loader = WebBaseLoader(url)
    docs = loader.load()
    return docs

docs = get_documents_From_Web('https://planetix.gitbook.io/whitepaper/master/1.-executive-summary')

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

# "Answer the users's question" is the program telling the LLM its task (the 'answer' in the Answer-class is just to prep the LLM for the expected content(JSON))
prompt = ChatPromptTemplate.from_template("""
Answer the user's question with 3 sentences:
Context: {context}
Question: {human_input}
{format_instructions}
""")


def generate_answer(question: str) -> str:
    chain = prompt | llm_model | parser
    try:
        result = chain.invoke({
            "human_input": question,
            "context": docs,
            "format_instructions": parser.get_format_instructions()
        })
        return result["answer"]
    except Exception as e:
        return f"Error generating answer: {str(e)}"


# Example usage (you can call this function elsewhere)
if __name__ == "__main__":
    answer = generate_answer("What are the basics of the game?")
    print(answer)  