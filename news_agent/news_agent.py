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
    You are a news search specialist. Your task is to:
    1. Search for the most relevant and recent news on the given topic
    2. Ensure the results are from reputable sources
    3. Return the raw search results in a structured format
    """,
    model=MODEL
)

synthesis_agent = Agent(
    name="News Synthesizer",
    instructions="""
    You are a news synthesis expert. Your task is to:
    1. Analyze the raw news articles provided
    2. Identify the key themes and important information
    3. Combine information from multiple sources
    4. Create a comprehensive but concise synthesis
    5. Focus on facts and maintain journalistic objectivity
    6. Write in a clear, professional style
    Provide a 2-3 paragraph synthesis of the main points.
    """,
    model=MODEL
)

summary_agent = Agent(
    name="News Summarizer",
    instructions="""
    You are an expert news summarizer combining AP and Reuters style clarity with digital-age brevity.

    Your task:
    1. Core Information:
       - Lead with the most newsworthy development
       - Include key stakeholders and their actions
       - Add critical numbers/data if relevant
       - Explain why this matters now
       - Mention immediate implications

    2. Style Guidelines:
       - Use strong, active verbs
       - Be specific, not general
       - Maintain journalistic objectivity
       - Make every word count
       - Explain technical terms if necessary

    Format: Create a single paragraph of 250-400 words that informs and engages.
    Pattern: [Major News] + [Key Details/Data] + [Why It Matters/What's Next]

    Focus on answering: What happened? Why is it significant? What's the impact?

    IMPORTANT: Provide ONLY the summary paragraph. Do not include any introductory phrases, 
    labels, or meta-text like "Here's a summary" or "In AP/Reuters style."
    Start directly with the news content.
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