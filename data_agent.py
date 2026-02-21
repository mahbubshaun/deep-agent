from daytona import Daytona

from langchain_daytona import DaytonaSandbox

# sandbox = Daytona().create()
# backend = DaytonaSandbox(sandbox=sandbox)

# result = backend.execute("echo ready")
# print(result)

SAVED_SANDBOX_ID ="c15bf4ba-656d-41ad-8f6e-6ecf07d7b2b8"  # From first print

client = Daytona()
sandbox = client.get(SAVED_SANDBOX_ID)  # Reuses existing sandbox
backend = DaytonaSandbox(sandbox=sandbox)
backend.execute("""
pip install pandas matplotlib --quiet
""")
# ExecuteResponse(output='ready', exit_code=0, ...)

import csv
import io

# Create sample sales data
data = [
    ["Date", "Product", "Units Sold", "Revenue"],
    ["2025-08-01", "Widget A", 10, 250],
    ["2025-08-02", "Widget B", 5, 125],
    ["2025-08-03", "Widget A", 7, 175],
    ["2025-08-04", "Widget C", 3, 90],
    ["2025-08-05", "Widget B", 8, 200],
]

# Convert to CSV bytes
text_buf = io.StringIO()
writer = csv.writer(text_buf)
writer.writerows(data)
csv_bytes = text_buf.getvalue().encode("utf-8")
text_buf.close()

# Upload to backend
backend.upload_files([("/home/daytona/data/sales_data.csv", csv_bytes)])

from langchain.tools import tool
from slack_sdk import WebClient
import os


slack_token = os.environ["SLACK_USER_TOKEN"]
slack_client = WebClient(token=slack_token)

# Quick test outside agent
SLACK_CHANNEL = "C0AE325BQTC"  # Define once at top
# try:
#     slack_client.auth_test()
#     print("✅ Token valid")
#     slack_client.chat_postMessage(channel=SLACK_CHANNEL, text="🧪 Agent test")
#     print("✅ Can post to channel")
# except Exception as e:
#     print(f"❌ Slack error: {e}")




@tool(parse_docstring=True)
def slack_send_message(text: str, file_path: str | None = None) -> str:
    """Send analysis report to Slack, optionally with plot image.

    Args:
        text: Summary of sales analysis to send
        file_path: Path to plot image in sandbox (e.g., /tmp/sales_plot.png)
    """
    try:
        if file_path:
            files = backend.download_files([file_path])
            if not files or files[0].error:
                return f"❌ Failed to download {file_path}"
            slack_client.files_upload_v2(
                channel=SLACK_CHANNEL,
                content=files[0].content,
                initial_comment=text,
            )
        else:
            slack_client.chat_postMessage(channel=SLACK_CHANNEL, text=text)
        return f"✅ Sent to Slack: {text[:50]}..."
    except Exception as e:
        return f"❌ Slack error: {str(e)}"


import uuid

from langgraph.checkpoint.memory import InMemorySaver
from deepagents import create_deep_agent
from langchain.chat_models import init_chat_model
from os import getenv

checkpointer = InMemorySaver()
default_headers = {
    "HTTP-Referer": (getenv("YOUR_SITE_URL") or ""),
    "X-Title": (getenv("YOUR_SITE_NAME") or ""),
}

model = init_chat_model(
    model="gpt-4o",
    model_provider="openai",
    base_url="https://openrouter.ai/api/v1",
    api_key=getenv("OPENROUTER_API_KEY"),
    default_headers=default_headers,
)

agent = create_deep_agent(
    model=model,
    tools=[slack_send_message],
    backend=backend,
    checkpointer=checkpointer,
)

thread_id = str(uuid.uuid4())
config={"configurable": {"thread_id": thread_id}}        

input_message = {
    "role": "user",
    "content": (
        "Analyze /home/daytona/data/sales_data.csv. Create a bar chart of total revenue by product. "
        "Write a short summary of top products and trends. Send analysis + plot to Slack."
        "Data analyst. Create plots with matplotlib. "
        "ALWAYS end with slack_send_message(text=summary, file_path='/tmp/plot.png')"
    ),
}
for step in agent.stream(
    {"messages": [input_message]},
    config,
    stream_mode="updates",
):
    for _, update in step.items():
        if update and (messages := update.get("messages")) and isinstance(messages, list):
            for message in messages:
                message.pretty_print()