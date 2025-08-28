import os
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel, EmailStr
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

class EmailSchema(BaseModel):
    email_to: EmailStr
    subject: str
    body: str

def send_email(email_data: EmailSchema):
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    sender_email = os.getenv("SENDER_EMAIL")
    password = os.getenv("PASSWORD")
    
    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = email_data.email_to
    message["Subject"] = email_data.subject
    
    message.attach(MIMEText(email_data.body, "plain"))
    
    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, password)
        server.send_message(message)
        server.quit()
        print(f"Email send success: {email_data.email_to}")
        return True
    except Exception as e:
        print(f"Email send fail: {str(e)}")
        return False