import reflex as rx
from duckduckgo_search import DDGS
from swarm import Swarm, Agent
from datetime import datetime
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Initialize Swarm and set model

MODEL = "llama3.1"
client = Swarm()

# Create specialized agents
search_agent = Agent(
    name="News Searcher",
    instructions="""
    You are an expert in news discovery. Your role involves:
    1. Identifying the latest and most pertinent news articles on the provided topic.
    2. Ensuring all sources are credible and trustworthy.
    3. Presenting the raw search results in a clear and organized manner.
    """,
    model=MODEL
)

synthesis_agent = Agent(
    name="News Synthesizer",
    instructions="""
    You are a specialist in news summarization. Your responsibilities include:
    1. Reviewing the provided news articles thoroughly.
    2. Extracting key insights and essential details.
    3. Merging information from various sources into a unified summary.
    4. Crafting a clear and concise overview that is both comprehensive and succinct in a 
    professional and accessible tone.
    5. Prioritizing factual accuracy and upholding journalistic neutrality.
    6. Provide a synthesis of the main points in 2-3 paragraphs.
    """,
    model=MODEL
)

summary_agent = Agent(
    name="News Summarizer",
    instructions="""
    You are a skilled news summarizer, blending the precision of AP and Reuters with concise, modern storytelling.

    Your Responsibilities:
    1. Core Details:
    - Start with the most critical news development.
    - Highlight key players and their actions.
    - Include significant data or figures where applicable.
    - Explain its immediate relevance and importance.
    - Outline potential short-term effects or implications.

    2. Writing Style:
    - Use clear, active language.
    - Focus on specifics over generalities.
    - Maintain a neutral, fact-based tone.
    - Ensure each word adds value.
    - Simplify complex terms for broader understanding.

    Deliverable:

    Compose a single, engaging paragraph (250-400 words) structured as follows:
    [Main Event] + [Key Details/Data] + [Significance/Next Steps].

    IMPORTANT NOTE: Deliver the paragraph as news content only, without labels, introductions, or meta-comments. Begin directly with the story.
    """,
    model=MODEL
)

def search_news(topic):
    """Search for news articles using DuckDuckGo"""
    with DDGS() as ddg:
        results = ddg.text(f"{topic} news {datetime.now().strftime('%Y-%m')}", max_results=3)
        if results:
            news_results = "\n\n".join([
                f"Title: {result['title']}\nURL: {result['href']}\nSummary: {result['body']}" 
                for result in results
            ])
            return news_results
        return f"No news found for {topic}."

class State(rx.State):
    """Manage the application state."""
    topic: str = "AI Agents"
    raw_news: str = ""
    synthesized_news: str = ""
    final_summary: str = ""
    is_loading: bool = False
    error_message: str = ""

    @rx.event(background=True)
    async def process_news(self):
        """Asynchronous news processing workflow using Swarm agents"""
        # Reset previous state
        async with self:

            self.is_loading = True
            self.error_message = ""
            self.raw_news = ""
            self.synthesized_news = ""
            self.final_summary = ""
            
            yield

        try:
            # Search news using search agent
            search_response = client.run(
                agent=search_agent,
                messages=[{"role": "user", "content": f"Find recent news about {self.topic}"}]
            )
            async with self:
                self.raw_news = search_response.messages[-1]["content"]
            
            # Synthesize using synthesis agent
            synthesis_response = client.run(
                agent=synthesis_agent,
                messages=[{"role": "user", "content": f"Synthesize these news articles:\n{self.raw_news}"}]
            )
            async with self:
                self.synthesized_news = synthesis_response.messages[-1]["content"]
            
            # Generate summary using summary agent
            summary_response = client.run(
                agent=summary_agent,
                messages=[{"role": "user", "content": f"Summarize this synthesis:\n{self.synthesized_news}"}]
            )

            async with self:
                self.final_summary = summary_response.messages[-1]["content"]
                self.is_loading = False

        except Exception as e:

            async with self:
                self.error_message = f"An error occurred: {str(e)}"
                self.is_loading = False

    def update_topic(self, topic: str):
        """Update the search topic"""
        self.topic = topic

def news_page() -> rx.Component:
    """Render the main news processing page"""
    return rx.box(
        rx.section(
            rx.heading("📰 News Agent", size="8"),
            rx.input(
                placeholder="Enter news topic",
                value=State.topic,
                on_change=State.update_topic,
                width="300px"
            ),
            rx.button(
                "Process News", 
                on_click=State.process_news,
                color_scheme="blue",
                loading=State.is_loading,
                width="fit-content",
            ),
            display="flex",
            flex_direction="column",
            gap="1rem",
        ),

        # Results Section
        rx.cond(
            State.final_summary != "",
            rx.vstack(
                rx.heading("📝 News Summary", size="4"),
                rx.text(State.final_summary),
                rx.button("Copy the Summary", on_click=[rx.set_clipboard(State.final_summary), rx.toast.info("Summary copied")]),
                spacing="4",
                width="100%"
            )
        ),

        spacing="4",
        max_width="800px",
        margin="auto",
        padding="20px"
    )

app = rx.App(
    theme=rx.theme(
        appearance="light",
        accent_color="blue"
    )
)
app.add_page(news_page, route="/")