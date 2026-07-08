# AlphaSphere Support Bot (Zendesk-to-Gemini)

This project automates the synchronization of Zendesk support articles into a Gemini Knowledge Base, powering an AI-driven support agent for OptiSigns.

## 1. Project Utilities
To run the utility scripts (`chatbot.py`, `cleanup.py`, `checkKb.py`), please set up a Python virtual environment:

```bash
# Create and activate virtual environment
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### File Descriptions:

- `main.py`: The core Lambda function that scrapes Zendesk, detects deltas, and syncs to Gemini.
- `local_run.py`: A local execution script for rapid testing and development.
- `chatbot.py`: A utility to test the Assistant via API (Bonus testing).
- `cleanup.py`: A utility to purge the Gemini Knowledge Base.
- `checkKb.py`: A utility to inspect current files in the Knowledge Base.
- `Dockerfile`: Container configuration for AWS Lambda deployment.

## 2. Cloud Architecture
The system employs a serverless, event-driven architecture designed for high availability, cost-efficiency, and minimal maintenance. An Amazon EventBridge rule triggers the scraper daily, and an Amazon SNS topic is integrated to notify administrators upon job execution.

[View AWS Architecture Diagram](https://drive.google.com/file/d/1n8O8h9MQhgQuXYGfDPAXJpMdmaxfB7kV/view?usp=sharing)
*(Note: If the link is inaccessible, please refer to the architecture image included in the repository).*

## 3. Deployment & Execution

### Local Testing
Build and run the project locally using:

```bash
# Build the image
docker build --provenance=false -t alpha-sphere-project:latest .                                               

# Run locally using the local_run.py script
docker run --rm -e GEMINI_API_KEY=<your_key> --entrypoint python alpha-sphere-project:latest local_run.py
```

**Why --provenance=false?**
Recent versions of Docker automatically attach provenance attestations (metadata about the build process), which creates a more complex multi-platform manifest list. This extra layer can sometimes cause compatibility issues or "manifest unknown" errors when pushing to Amazon ECR or executing within the AWS Lambda container runtime. Disabling it ensures a standard, flat OCI container image is generated, guaranteeing seamless integration with AWS.

**Why override the entrypoint?**
The `Dockerfile` is configured to execute `main.lambda_handler` by default, which is designed for the AWS Lambda environment. Overriding the entrypoint with `python` allows us to execute `local_run.py` directly, facilitating rapid local development and testing without needing a Lambda emulator.

### Why `chatbot.py` instead of Playground UI?
While the Playground UI is useful for manual testing, `chatbot.py` provides a programmatic, automated validation path. It ensures that the bot's behavior is consistent across the actual API used in production, allows for bulk testing against injected Knowledge Base chunks, and adheres to the project's "no UI drag-and-drop" requirement by utilizing the Gemini API exclusively.

## 4. Daily Job & Monitoring Proof
The scraper runs as a daily automated job via AWS EventBridge. Below are the execution proofs:

- **EventBridge Schedule:** Configured with a Cron expression to run daily.
*(See: `images/EventBridge rule to run daily scraper job and receive Email.png`)*
- **EventBridge Invocations:** Monitoring graph showing successful automated triggers.
*(See: `images/EventBridge log for daily job.png`)*
- **CloudWatch Lambda Log:** The Daily Job Summary demonstrating the detection of delta updates (Added, Updated, Skipped).
*(See: `images/Lambda Function Log for daily scaper job.png`)*
- **SNS Notification:** Email alert confirming the job execution.
*(See: `images/Email notification for daily scraper job.png`)*
- **Chat bot output:** Response from the chat bot.
*(See: `images/Chat bot output.png`)*
- **Crawled Articles Proof:** Terminal output displaying more than 30 scraped articles from the target domain.
*(See: `images/Crawled articles.png`)*
- **Cleaned Markdown Proof:** Execution log showing normalized Markdown format and content conversion.
*(See: `images/Content of crawled articles.png`)*
