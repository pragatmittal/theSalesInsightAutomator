/* eslint-disable react/jsx-no-bind */
"use client";

import { FormEvent, useState } from "react";
import styles from "./page.module.css";

type Status = "idle" | "loading" | "success" | "error";

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [message, setMessage] = useState("");

  // Build the API URL defensively so a base host in NEXT_PUBLIC_API_URL still works.
  const backendBase = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  const apiUrl = backendBase.endsWith("/api/process-sales")
    ? backendBase
    : `${backendBase.replace(/\/$/, "")}/api/process-sales`;
  const apiKey =
    process.env.NEXT_PUBLIC_BACKEND_API_KEY ??
    "your-strong-random-string";

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!file) {
      setStatus("error");
      setMessage("Please select a CSV or Excel file.");
      return;
    }
    if (!email) {
      setStatus("error");
      setMessage("Please enter a recipient email.");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);
    formData.append("email", email);
    formData.append("x_api_key", apiKey);

    setStatus("loading");
    setMessage("Processing your file and generating summary...");

    try {
      const response = await fetch(apiUrl, {
        method: "POST",
        body: formData,
      });

      const json = await response.json();

      if (!response.ok) {
        throw new Error(json.detail ?? "Failed to process file.");
      }

      setStatus("success");
      setMessage(json.message ?? "Summary emailed successfully.");
    } catch (error: unknown) {
      setStatus("error");
      setMessage(
        error instanceof Error
          ? error.message
          : "Unexpected error while processing your request.",
      );
    }
  }

  return (
    <div className={styles.page}>
      <main className={styles.main}>
        <section className={styles.intro}>
          <h1>Sales Insight Automator</h1>
          <p>
            Upload your quarterly sales CSV/Excel file and send an
            AI-generated executive summary directly to your inbox.
          </p>
        </section>

        <form className={styles.form} onSubmit={handleSubmit}>
          <label className={styles.field}>
            <span>Sales file (.csv or .xlsx)</span>
            <input
              type="file"
              accept=".csv, application/vnd.openxmlformats-officedocument.spreadsheetml.sheet, application/vnd.ms-excel"
              onChange={(event) => {
                const selected = event.target.files?.[0] ?? null;
                setFile(selected);
              }}
            />
          </label>

          <label className={styles.field}>
            <span>Recipient email</span>
            <input
              type="email"
              placeholder="sales.leadership@company.com"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />
          </label>

          <button
            type="submit"
            className={styles.submit}
            disabled={status === "loading"}
          >
            {status === "loading" ? "Sending..." : "Generate & Email Summary"}
          </button>
        </form>

        {status !== "idle" && (
          <div
            className={`${styles.feedback} ${
              status === "success"
                ? styles.success
                : status === "error"
                  ? styles.error
                  : ""
            }`}
          >
            {message}
          </div>
        )}
      </main>
    </div>
  );
}
