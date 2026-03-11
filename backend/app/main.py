from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
import os
import io
import csv
from typing import List, Dict, Any

import google.generativeai as genai
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType


class ProcessResponse(BaseModel):
    status: str
    message: str


app = FastAPI(
    title="Sales Insight Automator API",
    description="Upload sales data and trigger AI-generated email summaries.",
    version="0.1.0",
)


origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def verify_api_key(x_api_key: str = Form(...)) -> None:
    expected = os.getenv("BACKEND_API_KEY")
    if not expected or x_api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid API key")


def parse_csv(content: bytes) -> List[Dict[str, Any]]:
    text_stream = io.StringIO(content.decode("utf-8"))
    reader = csv.DictReader(text_stream)
    return list(reader)


def aggregate_sales(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
  total_revenue = 0.0
  by_region: Dict[str, float] = {}
  by_category: Dict[str, float] = {}
  status_counts: Dict[str, int] = {}

  for row in rows:
      revenue_str = row.get("Revenue") or row.get("revenue") or "0"
      region = row.get("Region") or row.get("region") or "Unknown"
      category = row.get("Product_Category") or row.get("product_category") or "Unknown"
      status = row.get("Status") or row.get("status") or "Unknown"

      try:
          revenue = float(revenue_str)
      except (TypeError, ValueError):
          revenue = 0.0

      total_revenue += revenue
      by_region[region] = by_region.get(region, 0.0) + revenue
      by_category[category] = by_category.get(category, 0.0) + revenue
      status_counts[status] = status_counts.get(status, 0) + 1

  return {
      "total_revenue": total_revenue,
      "revenue_by_region": by_region,
      "revenue_by_category": by_category,
      "status_counts": status_counts,
      "row_count": len(rows),
  }


def generate_summary_with_gemini(stats: Dict[str, Any]) -> str:
  api_key = os.getenv("GEMINI_API_KEY")
  if not api_key:
      raise RuntimeError("GEMINI_API_KEY is not configured")

  genai.configure(api_key=api_key)
  model = genai.GenerativeModel("gemini-2.5-flash")

  prompt = (
      "You are an analytics assistant for a sales leadership team.\n"
      "Given the following Q1 sales metrics, write a concise executive summary.\n"
      "Highlight overall performance, key trends by region and product category, "
      "and any risks (e.g., cancellations). Close with 2–3 bullet recommendations.\n\n"
      f"Metrics JSON:\n{stats}"
  )

  response = model.generate_content(prompt)
  return response.text or "AI summary could not be generated."


mail_config = ConnectionConfig(
    MAIL_USERNAME=os.getenv("SMTP_USERNAME"),
    MAIL_PASSWORD=os.getenv("SMTP_PASSWORD"),
    MAIL_FROM=os.getenv("EMAIL_FROM"),
    MAIL_SERVER=os.getenv("SMTP_SERVER", "smtp.gmail.com"),
    MAIL_PORT=int(os.getenv("SMTP_PORT", "587")),
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
)


async def send_email(recipient: str, summary: str) -> None:
  if not mail_config.MAIL_USERNAME or not mail_config.MAIL_PASSWORD or not mail_config.MAIL_FROM:
      raise RuntimeError("Email configuration is missing.")

  message = MessageSchema(
      subject="Q1 Sales Insight Summary",
      recipients=[recipient],
      body=f"<pre style='font-family: system-ui, sans-serif; white-space: pre-wrap'>{summary}</pre>",
      subtype=MessageType.html,
  )

  fm = FastMail(mail_config)
  await fm.send_message(message)


@app.post(
    "/api/process-sales",
    response_model=ProcessResponse,
    summary="Process sales file and send AI summary email",
)
async def process_sales(
    file: UploadFile = File(...),
    email: EmailStr = Form(...),
    _: None = Depends(verify_api_key),
):
    if file.content_type not in ("text/csv", "application/vnd.ms-excel", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"):
        raise HTTPException(status_code=400, detail="Unsupported file type. Please upload a CSV or Excel file.")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        rows = parse_csv(content)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail="Failed to parse CSV file.") from exc

    if not rows:
        raise HTTPException(status_code=400, detail="No data rows found in file.")

    stats = aggregate_sales(rows)

    try:
        summary = generate_summary_with_gemini(stats)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail="AI generation failed.") from exc

    try:
        await send_email(email, summary)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=502,
            detail=f"Failed to send summary email: {exc}",
        ) from exc

    return JSONResponse(
        status_code=200,
        content={
            "status": "ok",
            "message": f"Summary generated and emailed to {email}",
        },
    )


@app.get("/health", summary="Health check")
async def health() -> Dict[str, str]:
    return {"status": "ok"}

