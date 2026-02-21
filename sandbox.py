from daytona import Daytona
from langchain_daytona import DaytonaSandbox
import os

# First run: Create and note the ID
client = Daytona()
sandbox = client.create()
print(f"Created sandbox ID: {sandbox.id}")  # Save this ID!

backend = DaytonaSandbox(sandbox=sandbox)