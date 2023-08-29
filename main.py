import os
import imaplib
import email
import re
import requests
from prefect import flow, task
from prefect.server.schemas.schedules import IntervalSchedule
from prefect.deployments import Deployment
from dotenv import load_dotenv
from datetime import datetime, timedelta


@flow(log_prints=True)
def create_reminder_icloud(due_date, amount_due):
    try:
        your_key = os.getenv("IFTTT_WEBHOOK_KEY")
        # Login credentials
        url = "https://maker.ifttt.com/trigger/create_reminder/with/key/{your_key}".format(
            your_key=your_key
        )

        # IFTTT Maker Webhooks payload
        payload = {"value1": amount_due, "value2": due_date}

        # Send POST request to IFTTT Maker Webhooks
        response = requests.post(url, data=payload)

        # Print response status code and content
        print("Response status code:", response.status_code)
        print("Response content:", response.content)
    except Exception as e:
        print("Couldn't create reminder:", e)


@flow(log_prints=True)
def fetch_bill_emails():
    try:
        # Load environment variables
        load_dotenv()
        # Login credentials
        username = os.getenv("GMAIL_USERNAME")
        password = os.getenv("GMAIL_APP_PASSWORD")

        # Connect to the Gmail server
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(username, password)
        print("Logged in as", username)

        # Select the mailbox you want to read emails from
        mail.select("inbox")

        # Search for emails from a specific sender
        sender_email = "customerservice@silverasset.com.au"
        _, data = mail.search(None, f'(FROM "{sender_email}")')

        # Loop through all the emails and print their subject lines
        last_email_id = data[0].split()[-1]
        _, data = mail.fetch(last_email_id, "(RFC822)")
        msg = email.message_from_bytes(data[0][1])
        if msg["Subject"].startswith("Important Notice: Your Silver Asset invoice"):
            payload = msg.get_payload()
            if isinstance(payload, list):
                payload = payload[0].get_payload()
            msg = email.message_from_string(payload)
            dates = re.findall(r"\d{2}\/\d{2}\/\d{4}", msg.get_payload())
            monetary_amounts = re.findall(
                r"\$\d{1,3}(?:,\d{3})*(?:\.\d{2})", msg.get_payload()
            )
            amount_due = monetary_amounts[0]
            due_date = dates[1]
            date_obj = datetime.strptime(due_date, "%d/%m/%Y")

            # Subtract one day from the date
            prev_date_obj = date_obj - timedelta(days=1)

            # Convert the previous date back to a string
            prev_due_date = prev_date_obj.strftime("%d/%m/%Y")

            print("Issue date:", dates[0])
            print("Total due:", monetary_amounts[0])
            print("Due date:", dates[1])

            create_reminder_icloud(prev_due_date, amount_due)

        # Close the mailbox and logout from the server
        mail.close()
        mail.logout()
    except Exception as e:
        print("Couldn't fetch emails:", e)


if __name__ == "__main__":
    # Run the flow
    fetch_bill_emails()
